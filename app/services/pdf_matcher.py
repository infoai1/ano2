"""PDF matcher service for extracting pages and matching paragraphs."""
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
import fitz  # PyMuPDF

from app.config import get_logger

logger = get_logger()

# Minimum confidence threshold for a valid match
MIN_CONFIDENCE_THRESHOLD = 0.3


def normalize_text(text: str) -> str:
    """Normalize text for comparison.

    Args:
        text: Raw text string

    Returns:
        Normalized text (lowercase, normalized whitespace)
    """
    if not text:
        return ""
    # Convert to lowercase
    text = text.lower()
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    # Strip leading/trailing whitespace
    return text.strip()


def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate similarity between two texts.

    Uses a combination of:
    1. Exact substring match (highest confidence)
    2. Word overlap ratio with position-aware matching

    Args:
        text1: Search text (typically paragraph)
        text2: Target text (typically page content)

    Returns:
        Similarity score between 0.0 and 1.0
    """
    # Normalize texts
    norm1 = normalize_text(text1)
    norm2 = normalize_text(text2)

    if not norm1 or not norm2:
        return 0.0

    # Exact substring containment - highest confidence signal
    if norm1 in norm2:
        return 1.0

    # Split into words
    words1 = norm1.split()
    words2_set = set(norm2.split())

    if not words1:
        return 0.0

    # Count how many of the search words appear in target
    matches = sum(1 for w in words1 if w in words2_set)
    overlap_ratio = matches / len(words1)

    # Check for consecutive word matches (phrase detection)
    # This helps distinguish "page 1" from "page 2" even when both contain common words
    words1_str = ' '.join(words1)
    consecutive_match_score = 0.0

    # Try to find the longest consecutive match
    for i in range(len(words1)):
        for j in range(len(words1), i, -1):
            phrase = ' '.join(words1[i:j])
            if phrase in norm2:
                phrase_len = j - i
                consecutive_match_score = max(consecutive_match_score, phrase_len / len(words1))
                break

    # Combine overlap and consecutive match
    # Consecutive matches are weighted higher for differentiation
    final_score = overlap_ratio * 0.4 + consecutive_match_score * 0.6

    return min(1.0, final_score)


def extract_pdf_pages(file_path: Path) -> List[Dict[str, Any]]:
    """Extract text from each page of a PDF.

    Args:
        file_path: Path to the PDF file

    Returns:
        List of dicts with 'page_number' and 'text' for each page

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    pages = []

    try:
        doc = fitz.open(file_path)

        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text")
            pages.append({
                'page_number': page_num,
                'text': text,
                'text_normalized': normalize_text(text),
            })

        doc.close()

        logger.info("pdf_extracted",
                    file=str(file_path),
                    page_count=len(pages))

    except Exception as e:
        logger.error("pdf_extraction_failed",
                     file=str(file_path),
                     error=str(e))
        raise

    return pages


def match_paragraph_to_page(
    para_text: str,
    pages: List[Dict[str, Any]],
    min_confidence: float = MIN_CONFIDENCE_THRESHOLD
) -> Dict[str, Any]:
    """Match a paragraph to the most likely PDF page.

    Args:
        para_text: The paragraph text to match
        pages: List of page dicts from extract_pdf_pages
        min_confidence: Minimum confidence threshold for a valid match

    Returns:
        Dict with 'page_number' (int or None) and 'confidence' (float)
    """
    if not para_text or not pages:
        return {'page_number': None, 'confidence': 0.0}

    best_page = None
    best_score = 0.0

    norm_para = normalize_text(para_text)

    for page in pages:
        page_text = page.get('text_normalized') or normalize_text(page.get('text', ''))

        if not page_text:
            continue

        score = calculate_similarity(norm_para, page_text)

        if score > best_score:
            best_score = score
            best_page = page['page_number']

    # Only return a page if confidence is above threshold
    if best_score < min_confidence:
        return {'page_number': None, 'confidence': best_score}

    return {'page_number': best_page, 'confidence': best_score}


def match_paragraphs_to_pdf(
    paragraphs: List[Dict[str, Any]],
    pdf_path: Path
) -> List[Dict[str, Any]]:
    """Match multiple paragraphs to PDF pages.

    Args:
        paragraphs: List of paragraph dicts with 'id' and 'text' keys
        pdf_path: Path to the PDF file

    Returns:
        List of result dicts with 'paragraph_id', 'page_number', 'confidence'
    """
    if not paragraphs:
        return []

    pages = extract_pdf_pages(pdf_path)
    results = []

    for para in paragraphs:
        para_id = para.get('id')
        para_text = para.get('text', '')

        match_result = match_paragraph_to_page(para_text, pages)

        results.append({
            'paragraph_id': para_id,
            'page_number': match_result['page_number'],
            'confidence': match_result['confidence'],
        })

    logger.info("paragraphs_matched",
                pdf=str(pdf_path),
                paragraph_count=len(paragraphs),
                matched_count=sum(1 for r in results if r['page_number'] is not None))

    return results
