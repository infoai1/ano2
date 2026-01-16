"""Configurable highlight keywords for the annotation tool.

This file contains editable lists of keywords that will be highlighted
in the paragraph text to help users identify and add references.
"""

# Islamic terms - highlighted in blue (same as Quran)
ISLAMIC_KEYWORDS = [
    'Quran',
    "Qur'an",
    'Quranic',
    'Hadith',
    'Prophet',
    'Surah',
    'Ayah',
    'Verse',
    'Allah',
    'Muhammad',
    'Sunnah',
    'Sahih',
    'Bukhari',
    'Muslim',
    'Tirmidhi',
    'Dawud',
    'Majah',
    'Muwatta',
    'Nasai',
    'Messenger',
    'Rasul',
    'Nabi',
    'Companions',
    'Sahaba',
    'Revelation',
    'Tafsir',
    'Fiqh',
    'Shariah',
    'Ummah',
    'Jihad',
    'Dawah',
    'Tawbah',
    'Taqwa',
    'Iman',
    'Islam',
    'Deen',
    'Salah',
    'Zakat',
    'Hajj',
    'Sawm',
    'Ramadan',
]

# People names - highlighted in purple
PEOPLE_KEYWORDS = [
    'Maulana',
    'Wahiduddin Khan',
    'Moses',
    'Jesus',
    'Abraham',
    'Ibrahim',
    'Musa',
    'Isa',
    'Adam',
    'Noah',
    'Nuh',
    'David',
    'Dawud',
    'Solomon',
    'Sulayman',
    'Joseph',
    'Yusuf',
    'Jacob',
    'Yaqub',
    'Isaac',
    'Ismail',
    'Ishmael',
]

# Places - highlighted in green
PLACE_KEYWORDS = [
    'Makkah',
    'Mecca',
    'Madinah',
    'Medina',
    'Jerusalem',
    'Kaaba',
    'Masjid',
    'Mosque',
    'Paradise',
    'Jannah',
    'Hell',
    'Jahannam',
]


def get_all_keywords():
    """Get all highlight keywords organized by category.

    Returns:
        Dict with keyword categories
    """
    return {
        'islamic': ISLAMIC_KEYWORDS,
        'people': PEOPLE_KEYWORDS,
        'places': PLACE_KEYWORDS,
    }


def get_flat_keywords():
    """Get all keywords as a flat list with their categories.

    Returns:
        List of (keyword, category) tuples
    """
    result = []
    for kw in ISLAMIC_KEYWORDS:
        result.append((kw, 'islamic'))
    for kw in PEOPLE_KEYWORDS:
        result.append((kw, 'people'))
    for kw in PLACE_KEYWORDS:
        result.append((kw, 'place'))
    return result
