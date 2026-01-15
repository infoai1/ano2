"""Paragraph grouping service for token-based chunking."""
import re
from typing import Dict, List, Any

from app.config import get_logger

logger = get_logger()

# Default token count settings
DEFAULT_MIN_TOKENS = 512
DEFAULT_MAX_TOKENS = 800


def count_tokens(text: str) -> int:
    """Count approximate tokens in text.

    Uses a simple word-based approximation. For more accurate counts,
    consider using tiktoken or similar tokenizer.

    Args:
        text: Text to count tokens in

    Returns:
        Approximate token count
    """
    if not text or not text.strip():
        return 0

    # Split on whitespace and punctuation
    words = re.findall(r'\b\w+\b', text)

    # Add some for punctuation (rough approximation)
    punctuation = len(re.findall(r'[.,!?;:\'"()\[\]{}]', text))

    return len(words) + (punctuation // 2)


def calculate_group_token_count(paragraphs: List[Dict[str, Any]]) -> int:
    """Calculate total token count for a list of paragraphs.

    Args:
        paragraphs: List of paragraph dicts with 'token_count' key

    Returns:
        Total token count
    """
    return sum(p.get('token_count', 0) for p in paragraphs)


def create_groups(
    paragraphs: List[Dict[str, Any]],
    min_tokens: int = DEFAULT_MIN_TOKENS,
    max_tokens: int = DEFAULT_MAX_TOKENS
) -> List[Dict[str, Any]]:
    """Create groups of paragraphs based on token count.

    Groups paragraphs to achieve target token counts (512-800 by default).
    Preserves paragraph order and ensures all paragraphs are assigned.

    Args:
        paragraphs: List of paragraph dicts
        min_tokens: Minimum tokens per group (default 512)
        max_tokens: Maximum tokens per group (default 800)

    Returns:
        List of group dicts with 'order_index', 'token_count', 'paragraphs'
    """
    if not paragraphs:
        return []

    # Ensure all paragraphs have token counts
    for para in paragraphs:
        if 'token_count' not in para:
            para['token_count'] = count_tokens(para.get('text', ''))

    groups = []
    current_group_paras = []
    current_token_count = 0

    for para in paragraphs:
        para_tokens = para['token_count']

        # If single paragraph exceeds max, it goes in its own group
        if para_tokens > max_tokens:
            # First, finish current group if it has content
            if current_group_paras:
                groups.append({
                    'order_index': len(groups),
                    'token_count': current_token_count,
                    'paragraphs': current_group_paras,
                })
                current_group_paras = []
                current_token_count = 0

            # Add large paragraph as its own group
            groups.append({
                'order_index': len(groups),
                'token_count': para_tokens,
                'paragraphs': [para],
            })
            continue

        # Check if adding this paragraph would exceed max
        if current_token_count + para_tokens > max_tokens and current_group_paras:
            # Check if current group meets minimum
            if current_token_count >= min_tokens:
                # Finalize current group
                groups.append({
                    'order_index': len(groups),
                    'token_count': current_token_count,
                    'paragraphs': current_group_paras,
                })
                current_group_paras = []
                current_token_count = 0
            # If not at minimum, we'll exceed max to try to reach min

        # Add paragraph to current group
        current_group_paras.append(para)
        current_token_count += para_tokens

        # If we've reached minimum and are at a good stopping point
        if current_token_count >= min_tokens:
            groups.append({
                'order_index': len(groups),
                'token_count': current_token_count,
                'paragraphs': current_group_paras,
            })
            current_group_paras = []
            current_token_count = 0

    # Don't forget remaining paragraphs
    if current_group_paras:
        groups.append({
            'order_index': len(groups),
            'token_count': current_token_count,
            'paragraphs': current_group_paras,
        })

    logger.debug("groups_created",
                 paragraph_count=len(paragraphs),
                 group_count=len(groups))

    return groups


def assign_paragraphs_to_groups(
    paragraphs: List[Dict[str, Any]],
    groups: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Assign group IDs to paragraphs based on group membership.

    Args:
        paragraphs: List of paragraph dicts
        groups: List of group dicts from create_groups

    Returns:
        Updated paragraphs with 'group_id' field
    """
    # Build lookup from paragraph ID to group index
    para_to_group = {}
    for group_idx, group in enumerate(groups):
        for para in group['paragraphs']:
            para_to_group[para['id']] = group_idx

    # Assign group IDs
    for para in paragraphs:
        para['group_id'] = para_to_group.get(para['id'])

    return paragraphs
