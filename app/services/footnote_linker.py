"""Footnote detection and linking service."""
import re
from typing import Dict, List, Any

from app.config import get_logger

logger = get_logger()

# Unicode superscript digits mapping
SUPERSCRIPT_MAP = {
    '¹': '1', '²': '2', '³': '3', '⁴': '4', '⁵': '5',
    '⁶': '6', '⁷': '7', '⁸': '8', '⁹': '9', '⁰': '0',
}


def detect_footnote_markers(text: str) -> List[Dict[str, Any]]:
    """Detect footnote markers in paragraph text.

    Supports:
    - Superscript numbers: ¹²³
    - Bracketed numbers: [1] [2]
    - Parenthetical numbers: (1) (2)
    - Asterisk markers: * **
    - Dagger markers: † ‡

    Args:
        text: Paragraph text to search

    Returns:
        List of marker dicts with 'marker' and 'position' keys
    """
    if not text:
        return []

    markers = []

    # Pattern 1: Unicode superscript digits
    for match in re.finditer(r'[¹²³⁴⁵⁶⁷⁸⁹⁰]+', text):
        # Convert to regular digits
        marker = ''.join(SUPERSCRIPT_MAP.get(c, c) for c in match.group())
        markers.append({
            'marker': marker,
            'position': match.start(),
            'raw': match.group(),
        })

    # Pattern 2: Bracketed numbers [1], [12]
    for match in re.finditer(r'\[(\d+)\]', text):
        markers.append({
            'marker': match.group(1),
            'position': match.start(),
            'raw': match.group(),
        })

    # Pattern 3: Parenthetical numbers at word boundary (1), (2)
    for match in re.finditer(r'(?<=[^\d])\((\d+)\)(?=[^\d]|$)', text):
        markers.append({
            'marker': match.group(1),
            'position': match.start(),
            'raw': match.group(),
        })

    # Pattern 4: Asterisk markers
    for match in re.finditer(r'\*+', text):
        # Only match if not part of emphasis (*word*)
        if match.start() == 0 or text[match.start()-1] not in ' \t\n':
            markers.append({
                'marker': match.group(),
                'position': match.start(),
                'raw': match.group(),
            })

    # Pattern 5: Dagger markers
    for match in re.finditer(r'[†‡]+', text):
        markers.append({
            'marker': match.group(),
            'position': match.start(),
            'raw': match.group(),
        })

    # Sort by position and remove duplicates
    markers.sort(key=lambda x: x['position'])

    logger.debug("footnote_markers_detected", count=len(markers), text_length=len(text))
    return markers


def detect_footnotes(text: str) -> List[Dict[str, Any]]:
    """Detect footnote definitions in footnote section.

    Supports:
    - "1. content" format
    - "1) content" format
    - "[1] content" format
    - "¹ content" format
    - "* content" format

    Args:
        text: Footnote section text

    Returns:
        List of footnote dicts with 'number' and 'content' keys
    """
    if not text:
        return []

    footnotes = []
    seen_numbers = set()

    # Pattern 1: "1. content" or "1) content"
    for match in re.finditer(r'^[\s]*(\d+)[.)\s]+(.+?)(?=\n\s*\d+[.)]|\n\s*\[|\n\s*[¹²³⁴⁵⁶⁷⁸⁹]|$)', text, re.MULTILINE | re.DOTALL):
        number = match.group(1)
        content = match.group(2).strip()
        if number not in seen_numbers and content:
            seen_numbers.add(number)
            footnotes.append({
                'number': number,
                'content': content,
            })

    # Pattern 2: "[1] content"
    for match in re.finditer(r'^\s*\[(\d+)\]\s*(.+?)(?=\n\s*\[|\n\s*\d+[.)]|$)', text, re.MULTILINE | re.DOTALL):
        number = match.group(1)
        content = match.group(2).strip()
        if number not in seen_numbers and content:
            seen_numbers.add(number)
            footnotes.append({
                'number': number,
                'content': content,
            })

    # Pattern 3: "¹ content" (superscript)
    for match in re.finditer(r'^[\s]*([¹²³⁴⁵⁶⁷⁸⁹⁰]+)\s*(.+?)(?=\n\s*[¹²³⁴⁵⁶⁷⁸⁹]|$)', text, re.MULTILINE | re.DOTALL):
        raw_number = match.group(1)
        number = ''.join(SUPERSCRIPT_MAP.get(c, c) for c in raw_number)
        content = match.group(2).strip()
        if number not in seen_numbers and content:
            seen_numbers.add(number)
            footnotes.append({
                'number': number,
                'content': content,
            })

    logger.debug("footnotes_detected", count=len(footnotes), text_length=len(text))
    return footnotes


def extract_footnote_content(raw_footnote: str) -> str:
    """Extract the content from a raw footnote string.

    Removes the number/marker prefix and trims whitespace.

    Args:
        raw_footnote: Raw footnote string like "1. Bukhari 123"

    Returns:
        Cleaned content string
    """
    if not raw_footnote:
        return ""

    # Remove common prefixes
    content = raw_footnote.strip()

    # Pattern: "N. " or "N) " or "[N] " or "¹ " or "* "
    content = re.sub(r'^[\s]*(\d+|[¹²³⁴⁵⁶⁷⁸⁹⁰]+|\*+|[†‡]+)[.)\]\s]+', '', content)
    content = re.sub(r'^\[(\d+)\]\s*', '', content)

    return content.strip()


def link_footnotes(
    para_text: str,
    footnotes: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Link footnote markers in paragraph to footnote definitions.

    Args:
        para_text: Paragraph text containing markers
        footnotes: List of footnote dicts with 'number' and 'content'

    Returns:
        List of link dicts with 'marker', 'content', and 'position'
    """
    if not para_text or not footnotes:
        return []

    # Detect markers in paragraph
    markers = detect_footnote_markers(para_text)

    # Create footnote lookup by number
    footnote_lookup = {fn['number']: fn['content'] for fn in footnotes}

    # Link markers to footnotes
    links = []
    for marker in markers:
        marker_num = marker['marker']
        if marker_num in footnote_lookup:
            links.append({
                'marker': marker_num,
                'content': footnote_lookup[marker_num],
                'position': marker['position'],
            })

    logger.debug("footnotes_linked",
                 markers_found=len(markers),
                 links_created=len(links))
    return links
