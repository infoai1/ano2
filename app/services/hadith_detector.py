"""Hadith reference detection service."""
import re
from typing import Dict, List, Any, Optional

from app.config import get_logger

logger = get_logger()

# Collection name variants to canonical name mapping
COLLECTION_NAMES = {
    # Sahih Bukhari
    'bukhari': 'bukhari',
    'bukhaaree': 'bukhari',
    'bukhaari': 'bukhari',

    # Sahih Muslim
    'muslim': 'muslim',

    # Sunan Abu Dawud
    'abudawud': 'abudawud',
    'abudawood': 'abudawud',
    'abud': 'abudawud',
    'dawud': 'abudawud',
    'dawood': 'abudawud',
    'daud': 'abudawud',

    # Jami at-Tirmidhi
    'tirmidhi': 'tirmidhi',
    'tirmizi': 'tirmidhi',
    'tirmidhee': 'tirmidhi',

    # Sunan Ibn Majah
    'ibnmajah': 'ibnmajah',
    'ibnmaja': 'ibnmajah',
    'majah': 'ibnmajah',
    'maja': 'ibnmajah',

    # Sunan an-Nasai
    'nasai': 'nasai',
    'nasaai': 'nasai',

    # Muwatta Malik
    'muwatta': 'muwatta',
    'muwattamalik': 'muwatta',
    'maliksmuwatta': 'muwatta',

    # Musnad Ahmad
    'ahmad': 'ahmad',
    'ahmed': 'ahmad',

    # Sunan ad-Darimi
    'darimi': 'darimi',
    'daarimi': 'darimi',

    # Sunan al-Bayhaqi
    'bayhaqi': 'bayhaqi',
    'bayhaqee': 'bayhaqi',
}

# Full collection names
COLLECTION_FULL_NAMES = {
    'bukhari': 'Sahih al-Bukhari',
    'muslim': 'Sahih Muslim',
    'abudawud': 'Sunan Abu Dawud',
    'tirmidhi': 'Jami at-Tirmidhi',
    'ibnmajah': 'Sunan Ibn Majah',
    'nasai': 'Sunan an-Nasai',
    'muwatta': 'Muwatta Malik',
    'ahmad': 'Musnad Ahmad',
    'darimi': 'Sunan ad-Darimi',
    'bayhaqi': 'Sunan al-Bayhaqi',
}


def normalize_collection_name(name: str) -> Optional[str]:
    """Normalize a collection name to its canonical form.

    Args:
        name: Collection name in any format

    Returns:
        Canonical collection name or None if not recognized
    """
    if not name:
        return None

    # Normalize: lowercase, remove common prefixes and special chars
    normalized = name.lower().strip()
    normalized = re.sub(r'^(sahih|saheeh|sunan|jami|musnad)\s*', '', normalized)
    normalized = re.sub(r'^(al-|an-|at-|ad-)', '', normalized)
    normalized = normalized.replace(' ', '').replace('-', '').replace("'", '')

    return COLLECTION_NAMES.get(normalized)


def detect_hadith_refs(text: str) -> List[Dict[str, Any]]:
    """Detect Hadith references in text.

    Supports formats:
    - Bukhari 1234
    - Sahih al-Bukhari 1234
    - Bukhari, no. 1234
    - Muslim Book 5 Hadith 23
    - Tirmidhi Vol. 3, No. 456

    Args:
        text: Text to search for references

    Returns:
        List of reference dicts with collection, hadith_number, collection_name, raw_text
    """
    if not text:
        return []

    refs = []
    seen = set()

    # Collection keywords for pattern matching
    collection_keywords = (
        r'bukhari|bukhaaree|bukhaari|'
        r'muslim|'
        r'abu\s*dawu?d|abu\s*dawood|'
        r'tirmidhi|tirmizi|tirmidhee|'
        r'ibn\s*majah?|'
        r'nasai|nasa\'?i|'
        r'muwatta(?:\s+malik)?|malik\'?s?\s+muwatta|'
        r'ahmad|ahmed|'
        r'darimi|daarimi|'
        r'bayhaqi|bayhaqee'
    )

    # Pattern 1: Collection followed by number
    # e.g., "Bukhari 1234" or "Sahih al-Bukhari, no. 1234"
    pattern1 = rf'''
        (?:sahih|saheeh|sunan|jami|musnad)?\s*
        (?:al-|an-|at-|ad-)?
        ({collection_keywords})
        [\s,.:]*
        (?:no\.?|[#]|hadith)?\s*
        (\d+)
    '''

    for match in re.finditer(pattern1, text, re.IGNORECASE | re.VERBOSE):
        collection_raw = match.group(1)
        number = match.group(2)

        # Normalize the collection name
        collection = normalize_collection_name(collection_raw)
        if collection:
            key = (collection, number)
            if key not in seen:
                seen.add(key)
                refs.append({
                    'collection': collection,
                    'hadith_number': number,
                    'collection_name': COLLECTION_FULL_NAMES.get(collection),
                    'raw_text': match.group(0).strip(),
                })

    # Pattern 2: Book/Chapter format
    # e.g., "Bukhari, Book 1, Hadith 1" or "Muslim Book 5 Hadith 23"
    pattern2 = rf'''
        (?:sahih|saheeh|sunan|jami|musnad)?\s*
        (?:al-|an-|at-|ad-)?
        ({collection_keywords})
        [\s,]*
        (?:book|vol\.?|volume)\s*
        (\d+)
        [\s,]*
        (?:hadith|no\.?|[#])?\s*
        (\d+)
    '''

    for match in re.finditer(pattern2, text, re.IGNORECASE | re.VERBOSE):
        collection_raw = match.group(1)
        book_num = match.group(2)
        hadith_num = match.group(3)

        collection = normalize_collection_name(collection_raw)
        if collection:
            number = f"{book_num}:{hadith_num}"
            key = (collection, number)
            if key not in seen:
                seen.add(key)
                refs.append({
                    'collection': collection,
                    'hadith_number': number,
                    'collection_name': COLLECTION_FULL_NAMES.get(collection),
                    'raw_text': match.group(0).strip(),
                })

    logger.debug("hadith_refs_detected", count=len(refs), text_length=len(text))
    return refs
