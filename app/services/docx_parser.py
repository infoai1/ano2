"""DOCX parser service for extracting paragraphs and structure."""
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from docx import Document
from docx.opc.exceptions import PackageNotFoundError

from app.config import get_logger

logger = get_logger()


def detect_paragraph_type(style_name: Optional[str]) -> Dict[str, Any]:
    """Detect paragraph type and level from style name.

    Args:
        style_name: The Word style name (e.g., 'Heading 1', 'Normal', 'Quote')

    Returns:
        Dict with 'type' and optionally 'level' keys
    """
    if not style_name:
        return {'type': 'paragraph', 'level': 1}

    style_lower = style_name.lower()

    # Heading detection
    if 'heading' in style_lower or style_lower == 'title':
        # Extract level from "Heading N" format
        level_match = re.search(r'heading\s*(\d+)', style_lower)
        if level_match:
            level = int(level_match.group(1))
        elif style_lower == 'title':
            level = 1
        else:
            level = 1
        return {'type': 'heading', 'level': level}

    # Quote detection
    if any(q in style_lower for q in ['quote', 'block text', 'intense']):
        return {'type': 'quote', 'level': 1}

    # Default to paragraph
    return {'type': 'paragraph', 'level': 1}


def parse_docx(file_path: Path) -> Dict[str, Any]:
    """Parse a DOCX file and extract paragraphs with structure.

    Args:
        file_path: Path to the DOCX file

    Returns:
        Dict containing 'paragraphs' list and 'chapters' list

    Raises:
        FileNotFoundError: If file doesn't exist
        Exception: If file is not a valid DOCX
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        doc = Document(file_path)
    except PackageNotFoundError as e:
        logger.error("docx_parse_failed", file=str(file_path), error="Invalid DOCX format")
        raise ValueError(f"Invalid DOCX file: {file_path}") from e
    except Exception as e:
        logger.error("docx_parse_failed", file=str(file_path), error=str(e))
        raise

    paragraphs = []
    chapters = []
    current_chapter = None
    order_index = 0

    for para in doc.paragraphs:
        text = para.text.strip()

        # Skip whitespace-only paragraphs
        if not text:
            continue

        # Get style info
        style_name = para.style.name if para.style else None
        type_info = detect_paragraph_type(style_name)

        para_data = {
            'text': text,
            'type': type_info['type'],
            'level': type_info.get('level', 1),
            'order_index': order_index,
            'style_name': style_name,
        }

        # Track chapter structure (level 1 headings start new chapters)
        if type_info['type'] == 'heading' and type_info.get('level', 1) == 1:
            if current_chapter is not None:
                chapters.append(current_chapter)
            current_chapter = {
                'title': text,
                'order_index': len(chapters),
                'paragraph_indices': [order_index],
            }
        elif current_chapter is not None:
            current_chapter['paragraph_indices'].append(order_index)

        paragraphs.append(para_data)
        order_index += 1

    # Don't forget the last chapter
    if current_chapter is not None:
        chapters.append(current_chapter)

    # If no chapters detected (no level-1 headings), create a default one
    if not chapters and paragraphs:
        chapters = [{
            'title': 'Main Content',
            'order_index': 0,
            'paragraph_indices': list(range(len(paragraphs))),
        }]

    logger.info("docx_parsed",
                file=str(file_path),
                paragraph_count=len(paragraphs),
                chapter_count=len(chapters))

    return {
        'paragraphs': paragraphs,
        'chapters': chapters,
    }
