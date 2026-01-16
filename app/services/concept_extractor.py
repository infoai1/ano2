"""Concept extraction service using LLM (Gemini/DeepSeek).

Extracts concepts from paragraph text based on Maulana's taxonomy.
"""
import os
import yaml
from pathlib import Path
from typing import Optional

from app.config import get_logger

logger = get_logger()

# Load taxonomy
TAXONOMY_PATH = Path(__file__).parent.parent.parent / 'taxonomy' / 'maulana_taxonomy.yaml'
TAXONOMY = {}

if TAXONOMY_PATH.exists():
    with open(TAXONOMY_PATH) as f:
        TAXONOMY = yaml.safe_load(f)
    logger.info("taxonomy_loaded", categories=len(TAXONOMY.get('categories', {})))


def get_taxonomy_categories():
    """Get list of all taxonomy categories with subcategories.

    Returns:
        Dict mapping category names to their subcategories
    """
    if not TAXONOMY:
        return {}

    categories = TAXONOMY.get('categories', {})
    result = {}
    for cat_key, cat_data in categories.items():
        result[cat_key] = {
            'display_name': cat_data.get('display_name', cat_key),
            'subcategories': cat_data.get('subcategories', [])
        }
    return result


def extract_concepts_mock(text: str) -> dict:
    """Mock concept extraction for testing (no API call).

    Returns placeholder data until Gemini API is configured.

    Args:
        text: The paragraph text

    Returns:
        Dict with extracted concepts
    """
    # Simple keyword-based mock extraction
    concepts = []

    text_lower = text.lower()

    if any(word in text_lower for word in ['peace', 'peaceful', 'harmony']):
        concepts.append({'category': 'PEACE', 'subcategory': 'culture_of_peace'})

    if any(word in text_lower for word in ['god', 'allah', 'lord', 'creator']):
        concepts.append({'category': 'GOD_REALIZATION', 'subcategory': 'discovering_god_in_creation'})

    if any(word in text_lower for word in ['patience', 'sabr', 'perseverance']):
        concepts.append({'category': 'SPIRITUALITY', 'subcategory': 'patience'})

    if any(word in text_lower for word in ['quran', 'qur\'an', 'scripture']):
        concepts.append({'category': 'QURAN', 'subcategory': 'understanding_quran'})

    if any(word in text_lower for word in ['prophet', 'muhammad', 'messenger']):
        concepts.append({'category': 'PROPHETIC_WISDOM', 'subcategory': 'prophet_as_model'})

    return {
        'concepts': concepts,
        'method': 'mock',
        'confidence': 0.5
    }


def extract_concepts_gemini(text: str, api_key: Optional[str] = None) -> dict:
    """Extract concepts using Google Gemini API.

    Args:
        text: The paragraph text
        api_key: Gemini API key (uses env var if not provided)

    Returns:
        Dict with extracted concepts
    """
    import google.generativeai as genai

    api_key = api_key or os.getenv('GEMINI_API_KEY')
    if not api_key:
        logger.warning("gemini_api_key_missing")
        return extract_concepts_mock(text)

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')

        # Build prompt with taxonomy
        categories_list = []
        for cat_key, cat_data in get_taxonomy_categories().items():
            subs = ', '.join(cat_data['subcategories'][:5])
            categories_list.append(f"- {cat_key}: {subs}...")

        categories_text = '\n'.join(categories_list)

        prompt = f"""Analyze this text and identify the main concepts/themes.
Return a JSON array of objects with 'category' and 'subcategory' fields.
Only use categories from this taxonomy:

{categories_text}

Text to analyze:
"{text}"

Return ONLY valid JSON array, no explanation. Example:
[{{"category": "PEACE", "subcategory": "culture_of_peace"}}]
"""

        response = model.generate_content(prompt)
        result_text = response.text.strip()

        # Parse JSON response
        import json
        if result_text.startswith('```'):
            result_text = result_text.split('```')[1]
            if result_text.startswith('json'):
                result_text = result_text[4:]

        concepts = json.loads(result_text)

        return {
            'concepts': concepts,
            'method': 'gemini',
            'confidence': 0.8
        }

    except Exception as e:
        logger.error("gemini_extraction_failed", error=str(e))
        return extract_concepts_mock(text)


def extract_concepts(text: str, use_llm: bool = True) -> dict:
    """Extract concepts from text.

    Args:
        text: The paragraph text
        use_llm: Whether to use LLM (Gemini) or mock

    Returns:
        Dict with extracted concepts
    """
    if not text or len(text.strip()) < 10:
        return {'concepts': [], 'method': 'skip', 'confidence': 0}

    if use_llm and os.getenv('GEMINI_API_KEY'):
        return extract_concepts_gemini(text)
    else:
        return extract_concepts_mock(text)
