"""Export service for Book JSON and LightRAG JSON formats."""
import json
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from app.config import get_logger

logger = get_logger()

# Fields to exclude from paragraph export
INTERNAL_FIELDS = {'_sa_instance_state', 'created_at', 'updated_at', 'book_id', 'book'}


def build_paragraph_export(para: Dict[str, Any]) -> Dict[str, Any]:
    """Build export dict for a single paragraph.

    Args:
        para: Paragraph dict from database

    Returns:
        Clean paragraph dict for export
    """
    result = {}

    # Always include core fields
    for key in ['id', 'text', 'order_index']:
        if key in para:
            result[key] = para[key]

    # Include optional fields if present
    optional_fields = [
        'chapter_title', 'page_number', 'is_heading', 'heading_level',
        'quran_refs', 'hadith_refs', 'footnotes', 'group_id', 'token_count',
    ]
    for key in optional_fields:
        if key in para and para[key] is not None:
            result[key] = para[key]

    return result


def build_group_export(group: Dict[str, Any]) -> Dict[str, Any]:
    """Build export dict for a single group.

    Args:
        group: Group dict with paragraphs

    Returns:
        Clean group dict for export
    """
    paragraph_ids = [p['id'] for p in group.get('paragraphs', [])]

    return {
        'order_index': group['order_index'],
        'token_count': group['token_count'],
        'paragraph_ids': paragraph_ids,
    }


def validate_export_data(data: Optional[Dict[str, Any]]) -> bool:
    """Validate data before export.

    Args:
        data: Export data dict

    Returns:
        True if valid, False otherwise
    """
    if not data or not isinstance(data, dict):
        return False

    # Required top-level keys
    required_keys = ['title', 'paragraphs', 'groups']
    for key in required_keys:
        if key not in data:
            return False

    # Validate paragraphs have required fields
    for para in data.get('paragraphs', []):
        if 'id' not in para or 'text' not in para:
            return False

    return True


def export_book_json(data: Dict[str, Any]) -> str:
    """Export book data to Book JSON format.

    Book JSON format includes:
    - Book metadata (title, author, slug)
    - Full paragraph list with all annotations
    - Group information for chunking

    Args:
        data: Book data dict with paragraphs and groups

    Returns:
        JSON string
    """
    export = {
        'exported_at': datetime.now(timezone.utc).isoformat(),
        'format': 'book_json',
        'version': '1.0',
    }

    # Copy metadata
    for key in ['title', 'author', 'slug', 'description', 'source_file']:
        if key in data:
            export[key] = data[key]

    # Build paragraphs
    export['paragraphs'] = [
        build_paragraph_export(para)
        for para in data.get('paragraphs', [])
    ]

    # Build groups
    export['groups'] = [
        build_group_export(group)
        for group in data.get('groups', [])
    ]

    # Statistics
    export['stats'] = {
        'paragraph_count': len(export['paragraphs']),
        'group_count': len(export['groups']),
        'total_tokens': sum(g['token_count'] for g in export['groups']),
    }

    logger.debug("book_json_exported",
                 title=data.get('title'),
                 paragraphs=len(export['paragraphs']),
                 groups=len(export['groups']))

    return json.dumps(export, ensure_ascii=False, indent=2)


def export_lightrag_json(data: Dict[str, Any]) -> str:
    """Export book data to LightRAG JSON format.

    LightRAG format creates one chunk per group:
    - content: Combined text from all paragraphs in group
    - metadata: Source info, chunk position, paragraph IDs

    Args:
        data: Book data dict with paragraphs and groups

    Returns:
        JSON string (list of chunks)
    """
    chunks = []

    for group in data.get('groups', []):
        # Combine paragraph texts
        para_texts = [p.get('text', '') for p in group.get('paragraphs', [])]
        content = '\n\n'.join(para_texts)

        # Extract paragraph IDs
        para_ids = [p['id'] for p in group.get('paragraphs', [])]

        # Build metadata
        metadata = {
            'source': data.get('slug', ''),
            'title': data.get('title', ''),
            'author': data.get('author', ''),
            'chunk_index': group['order_index'],
            'token_count': group['token_count'],
            'paragraph_ids': para_ids,
        }

        # Include chapter if all paragraphs in same chapter
        chapters = set()
        for para in group.get('paragraphs', []):
            if 'chapter_title' in para:
                chapters.add(para['chapter_title'])
        if len(chapters) == 1:
            metadata['chapter'] = list(chapters)[0]

        # Include page range if available
        pages = []
        for para in group.get('paragraphs', []):
            if 'page_number' in para and para['page_number']:
                pages.append(para['page_number'])
        if pages:
            metadata['page_start'] = min(pages)
            metadata['page_end'] = max(pages)

        chunks.append({
            'content': content,
            'metadata': metadata,
        })

    logger.debug("lightrag_json_exported",
                 title=data.get('title'),
                 chunks=len(chunks))

    return json.dumps(chunks, ensure_ascii=False, indent=2)


def export_for_custom_kg(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Export data in format suitable for LightRAG ainsert_custom_kg().

    This creates entities and relationships for the knowledge graph.

    Args:
        data: Book data with paragraphs, groups, and references

    Returns:
        List of custom_kg entries
    """
    entries = []

    # Create book entity
    book_entity = {
        'type': 'entity',
        'entity_name': data.get('title', 'Unknown'),
        'entity_type': 'BOOK',
        'description': data.get('description', f"Book by {data.get('author', 'Unknown')}"),
        'source_chunk_id': f"book_{data.get('slug', 'unknown')}",
    }
    entries.append(book_entity)

    # Process each group/chunk
    for group in data.get('groups', []):
        chunk_id = f"{data.get('slug', 'book')}_{group['order_index']}"

        # Add Quran references
        for para in group.get('paragraphs', []):
            for ref in para.get('quran_refs', []):
                entity = {
                    'type': 'entity',
                    'entity_name': f"Quran {ref.get('surah')}:{ref.get('ayah')}",
                    'entity_type': 'QURAN_REF',
                    'description': f"Quran reference to Surah {ref.get('surah_name', ref.get('surah'))} verse {ref.get('ayah')}",
                    'source_chunk_id': chunk_id,
                }
                entries.append(entity)

        # Add Hadith references
        for para in group.get('paragraphs', []):
            for ref in para.get('hadith_refs', []):
                entity = {
                    'type': 'entity',
                    'entity_name': f"{ref.get('collection_name', ref.get('collection'))} {ref.get('hadith_number')}",
                    'entity_type': 'HADITH_REF',
                    'description': f"Hadith from {ref.get('collection_name', ref.get('collection'))}",
                    'source_chunk_id': chunk_id,
                }
                entries.append(entity)

    logger.debug("custom_kg_exported",
                 title=data.get('title'),
                 entries=len(entries))

    return entries
