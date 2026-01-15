"""Quran reference detection service."""
import re
from typing import Dict, List, Any, Optional

from app.config import get_logger

logger = get_logger()

# Surah name to number mapping (canonical names and common variants)
SURAH_NAMES = {
    # 1. Al-Fatihah
    'fatihah': 1, 'fatiha': 1, 'fateha': 1, 'opening': 1,
    # 2. Al-Baqarah
    'baqarah': 2, 'baqara': 2, 'cow': 2,
    # 3. Aal-E-Imran
    'imran': 3, 'imraan': 3,
    # 4. An-Nisa
    'nisa': 4, 'nisaa': 4, 'women': 4,
    # 5. Al-Maidah
    'maidah': 5, 'maida': 5, 'table': 5,
    # 6. Al-Anam
    'anam': 6, 'anaam': 6, 'cattle': 6,
    # 7. Al-Araf
    'araf': 7, 'araaf': 7, 'heights': 7,
    # 8. Al-Anfal
    'anfal': 8, 'anfaal': 8, 'spoils': 8,
    # 9. At-Tawbah
    'tawbah': 9, 'tawba': 9, 'tauba': 9, 'repentance': 9,
    # 10. Yunus
    'yunus': 10, 'younus': 10, 'jonah': 10,
    # 11. Hud
    'hud': 11, 'hood': 11,
    # 12. Yusuf
    'yusuf': 12, 'yousuf': 12, 'joseph': 12,
    # 13. Ar-Rad
    'rad': 13, 'raad': 13, 'thunder': 13,
    # 14. Ibrahim
    'ibrahim': 14, 'ibraheem': 14, 'abraham': 14,
    # 15. Al-Hijr
    'hijr': 15,
    # 16. An-Nahl
    'nahl': 16, 'bee': 16,
    # 17. Al-Isra
    'isra': 17, 'israa': 17, 'bani israil': 17,
    # 18. Al-Kahf
    'kahf': 18, 'cave': 18,
    # 19. Maryam
    'maryam': 19, 'mary': 19,
    # 20. Ta-Ha
    'taha': 20,
    # 21. Al-Anbiya
    'anbiya': 21, 'anbiyaa': 21, 'prophets': 21,
    # 22. Al-Hajj
    'hajj': 22, 'pilgrimage': 22,
    # 23. Al-Muminun
    'muminun': 23, 'muminoon': 23, 'believers': 23,
    # 24. An-Nur
    'nur': 24, 'noor': 24, 'light': 24,
    # 25. Al-Furqan
    'furqan': 25, 'furqaan': 25, 'criterion': 25,
    # 26. Ash-Shuara
    'shuara': 26, 'shuaraa': 26, 'poets': 26,
    # 27. An-Naml
    'naml': 27, 'ant': 27, 'ants': 27,
    # 28. Al-Qasas
    'qasas': 28, 'stories': 28,
    # 29. Al-Ankabut
    'ankabut': 29, 'ankaboot': 29, 'spider': 29,
    # 30. Ar-Rum
    'rum': 30, 'room': 30, 'romans': 30,
    # 31. Luqman
    'luqman': 31, 'luqmaan': 31,
    # 32. As-Sajdah
    'sajdah': 32, 'sajda': 32, 'prostration': 32,
    # 33. Al-Ahzab
    'ahzab': 33, 'ahzaab': 33, 'confederates': 33,
    # 34. Saba
    'saba': 34, 'sabaa': 34, 'sheba': 34,
    # 35. Fatir
    'fatir': 35, 'faatir': 35, 'originator': 35,
    # 36. Ya-Sin
    'yasin': 36, 'yaseen': 36, 'ya sin': 36,
    # 37. As-Saffat
    'saffat': 37, 'saaffaat': 37,
    # 38. Sad
    'sad': 38, 'saad': 38,
    # 39. Az-Zumar
    'zumar': 39, 'groups': 39,
    # 40. Ghafir
    'ghafir': 40, 'mumin': 40, 'forgiver': 40,
    # 41. Fussilat
    'fussilat': 41, 'hamim sajdah': 41,
    # 42. Ash-Shura
    'shura': 42, 'shuraa': 42, 'consultation': 42,
    # 43. Az-Zukhruf
    'zukhruf': 43, 'ornaments': 43,
    # 44. Ad-Dukhan
    'dukhan': 44, 'dukhaan': 44, 'smoke': 44,
    # 45. Al-Jathiyah
    'jathiyah': 45, 'jathiya': 45, 'kneeling': 45,
    # 46. Al-Ahqaf
    'ahqaf': 46, 'ahqaaf': 46,
    # 47. Muhammad
    'muhammad': 47,
    # 48. Al-Fath
    'fath': 48, 'victory': 48,
    # 49. Al-Hujurat
    'hujurat': 49, 'hujuraat': 49, 'rooms': 49,
    # 50. Qaf
    'qaf': 50, 'qaaf': 50,
    # 51. Adh-Dhariyat
    'dhariyat': 51, 'dhaariyaat': 51,
    # 52. At-Tur
    'tur': 52, 'toor': 52, 'mount': 52,
    # 53. An-Najm
    'najm': 53, 'star': 53,
    # 54. Al-Qamar
    'qamar': 54, 'moon': 54,
    # 55. Ar-Rahman
    'rahman': 55, 'rahmaan': 55,
    # 56. Al-Waqiah
    'waqiah': 56, 'waqia': 56, 'event': 56,
    # 57. Al-Hadid
    'hadid': 57, 'hadeed': 57, 'iron': 57,
    # 58. Al-Mujadila
    'mujadila': 58, 'mujadilah': 58,
    # 59. Al-Hashr
    'hashr': 59, 'exile': 59,
    # 60. Al-Mumtahanah
    'mumtahanah': 60, 'mumtahana': 60,
    # 61. As-Saff
    'saff': 61, 'ranks': 61,
    # 62. Al-Jumuah
    'jumuah': 62, 'jumua': 62, 'friday': 62,
    # 63. Al-Munafiqun
    'munafiqun': 63, 'munafiqoon': 63, 'hypocrites': 63,
    # 64. At-Taghabun
    'taghabun': 64, 'taghaabun': 64,
    # 65. At-Talaq
    'talaq': 65, 'talaaq': 65, 'divorce': 65,
    # 66. At-Tahrim
    'tahrim': 66, 'tahreem': 66, 'prohibition': 66,
    # 67. Al-Mulk
    'mulk': 67, 'sovereignty': 67, 'dominion': 67,
    # 68. Al-Qalam
    'qalam': 68, 'pen': 68,
    # 69. Al-Haqqah
    'haqqah': 69, 'haaqqah': 69, 'reality': 69,
    # 70. Al-Maarij
    'maarij': 70, 'maaarij': 70,
    # 71. Nuh
    'nuh': 71, 'nooh': 71, 'noah': 71,
    # 72. Al-Jinn
    'jinn': 72,
    # 73. Al-Muzzammil
    'muzzammil': 73,
    # 74. Al-Muddathir
    'muddathir': 74, 'muddaththir': 74,
    # 75. Al-Qiyamah
    'qiyamah': 75, 'qiyama': 75, 'resurrection': 75,
    # 76. Al-Insan
    'insan': 76, 'insaan': 76, 'dahr': 76, 'man': 76,
    # 77. Al-Mursalat
    'mursalat': 77, 'mursalaat': 77,
    # 78. An-Naba
    'naba': 78, 'nabaa': 78, 'tidings': 78,
    # 79. An-Naziat
    'naziat': 79, 'naziaat': 79,
    # 80. Abasa
    'abasa': 80,
    # 81. At-Takwir
    'takwir': 81, 'takweer': 81,
    # 82. Al-Infitar
    'infitar': 82, 'infitaar': 82,
    # 83. Al-Mutaffifin
    'mutaffifin': 83, 'mutaffifeen': 83,
    # 84. Al-Inshiqaq
    'inshiqaq': 84, 'inshiqaaq': 84,
    # 85. Al-Buruj
    'buruj': 85, 'burooj': 85,
    # 86. At-Tariq
    'tariq': 86, 'taariq': 86,
    # 87. Al-Ala
    'ala': 87, 'alaa': 87, 'most high': 87,
    # 88. Al-Ghashiyah
    'ghashiyah': 88, 'ghashiya': 88,
    # 89. Al-Fajr
    'fajr': 89, 'dawn': 89,
    # 90. Al-Balad
    'balad': 90, 'city': 90,
    # 91. Ash-Shams
    'shams': 91, 'sun': 91,
    # 92. Al-Layl
    'layl': 92, 'lail': 92, 'night': 92,
    # 93. Ad-Duha
    'duha': 93, 'duhaa': 93,
    # 94. Al-Inshirah
    'inshirah': 94, 'sharh': 94, 'alam nashrah': 94,
    # 95. At-Tin
    'tin': 95, 'teen': 95, 'fig': 95,
    # 96. Al-Alaq
    'alaq': 96, 'iqra': 96, 'clot': 96,
    # 97. Al-Qadr
    'qadr': 97, 'power': 97, 'decree': 97,
    # 98. Al-Bayyinah
    'bayyinah': 98, 'bayyina': 98, 'evidence': 98,
    # 99. Az-Zalzalah
    'zalzalah': 99, 'zalzala': 99, 'earthquake': 99,
    # 100. Al-Adiyat
    'adiyat': 100, 'aadiyaat': 100,
    # 101. Al-Qariah
    'qariah': 101, 'qaria': 101,
    # 102. At-Takathur
    'takathur': 102, 'takaathur': 102,
    # 103. Al-Asr
    'asr': 103, 'time': 103,
    # 104. Al-Humazah
    'humazah': 104, 'humaza': 104,
    # 105. Al-Fil
    'fil': 105, 'feel': 105, 'elephant': 105,
    # 106. Quraysh
    'quraysh': 106, 'quraish': 106,
    # 107. Al-Maun
    'maun': 107, 'maaun': 107, 'small kindness': 107,
    # 108. Al-Kawthar
    'kawthar': 108, 'kauthar': 108, 'abundance': 108,
    # 109. Al-Kafirun
    'kafirun': 109, 'kafiroon': 109, 'disbelievers': 109,
    # 110. An-Nasr
    'nasr': 110, 'help': 110,
    # 111. Al-Masad
    'masad': 111, 'lahab': 111, 'flame': 111,
    # 112. Al-Ikhlas
    'ikhlas': 112, 'ikhlaas': 112, 'sincerity': 112, 'purity': 112,
    # 113. Al-Falaq
    'falaq': 113, 'daybreak': 113,
    # 114. An-Nas
    'nas': 114, 'naas': 114, 'mankind': 114,
}

# Reverse mapping for surah number to canonical name
SURAH_NUMBER_TO_NAME = {
    1: 'Al-Fatihah', 2: 'Al-Baqarah', 3: 'Aal-E-Imran', 4: 'An-Nisa', 5: 'Al-Maidah',
    6: 'Al-Anam', 7: 'Al-Araf', 8: 'Al-Anfal', 9: 'At-Tawbah', 10: 'Yunus',
    11: 'Hud', 12: 'Yusuf', 13: 'Ar-Rad', 14: 'Ibrahim', 15: 'Al-Hijr',
    16: 'An-Nahl', 17: 'Al-Isra', 18: 'Al-Kahf', 19: 'Maryam', 20: 'Ta-Ha',
    21: 'Al-Anbiya', 22: 'Al-Hajj', 23: 'Al-Muminun', 24: 'An-Nur', 25: 'Al-Furqan',
    26: 'Ash-Shuara', 27: 'An-Naml', 28: 'Al-Qasas', 29: 'Al-Ankabut', 30: 'Ar-Rum',
    31: 'Luqman', 32: 'As-Sajdah', 33: 'Al-Ahzab', 34: 'Saba', 35: 'Fatir',
    36: 'Ya-Sin', 37: 'As-Saffat', 38: 'Sad', 39: 'Az-Zumar', 40: 'Ghafir',
    41: 'Fussilat', 42: 'Ash-Shura', 43: 'Az-Zukhruf', 44: 'Ad-Dukhan', 45: 'Al-Jathiyah',
    46: 'Al-Ahqaf', 47: 'Muhammad', 48: 'Al-Fath', 49: 'Al-Hujurat', 50: 'Qaf',
    51: 'Adh-Dhariyat', 52: 'At-Tur', 53: 'An-Najm', 54: 'Al-Qamar', 55: 'Ar-Rahman',
    56: 'Al-Waqiah', 57: 'Al-Hadid', 58: 'Al-Mujadila', 59: 'Al-Hashr', 60: 'Al-Mumtahanah',
    61: 'As-Saff', 62: 'Al-Jumuah', 63: 'Al-Munafiqun', 64: 'At-Taghabun', 65: 'At-Talaq',
    66: 'At-Tahrim', 67: 'Al-Mulk', 68: 'Al-Qalam', 69: 'Al-Haqqah', 70: 'Al-Maarij',
    71: 'Nuh', 72: 'Al-Jinn', 73: 'Al-Muzzammil', 74: 'Al-Muddathir', 75: 'Al-Qiyamah',
    76: 'Al-Insan', 77: 'Al-Mursalat', 78: 'An-Naba', 79: 'An-Naziat', 80: 'Abasa',
    81: 'At-Takwir', 82: 'Al-Infitar', 83: 'Al-Mutaffifin', 84: 'Al-Inshiqaq', 85: 'Al-Buruj',
    86: 'At-Tariq', 87: 'Al-Ala', 88: 'Al-Ghashiyah', 89: 'Al-Fajr', 90: 'Al-Balad',
    91: 'Ash-Shams', 92: 'Al-Layl', 93: 'Ad-Duha', 94: 'Al-Inshirah', 95: 'At-Tin',
    96: 'Al-Alaq', 97: 'Al-Qadr', 98: 'Al-Bayyinah', 99: 'Az-Zalzalah', 100: 'Al-Adiyat',
    101: 'Al-Qariah', 102: 'At-Takathur', 103: 'Al-Asr', 104: 'Al-Humazah', 105: 'Al-Fil',
    106: 'Quraysh', 107: 'Al-Maun', 108: 'Al-Kawthar', 109: 'Al-Kafirun', 110: 'An-Nasr',
    111: 'Al-Masad', 112: 'Al-Ikhlas', 113: 'Al-Falaq', 114: 'An-Nas',
}

# Maximum ayahs per surah (for validation)
MAX_AYAHS = {
    1: 7, 2: 286, 3: 200, 4: 176, 5: 120, 6: 165, 7: 206, 8: 75, 9: 129, 10: 109,
    11: 123, 12: 111, 13: 43, 14: 52, 15: 99, 16: 128, 17: 111, 18: 110, 19: 98, 20: 135,
    21: 112, 22: 78, 23: 118, 24: 64, 25: 77, 26: 227, 27: 93, 28: 88, 29: 69, 30: 60,
    31: 34, 32: 30, 33: 73, 34: 54, 35: 45, 36: 83, 37: 182, 38: 88, 39: 75, 40: 85,
    41: 54, 42: 53, 43: 89, 44: 59, 45: 37, 46: 35, 47: 38, 48: 29, 49: 18, 50: 45,
    51: 60, 52: 49, 53: 62, 54: 55, 55: 78, 56: 96, 57: 29, 58: 22, 59: 24, 60: 13,
    61: 14, 62: 11, 63: 11, 64: 18, 65: 12, 66: 12, 67: 30, 68: 52, 69: 52, 70: 44,
    71: 28, 72: 28, 73: 20, 74: 56, 75: 40, 76: 31, 77: 50, 78: 40, 79: 46, 80: 42,
    81: 29, 82: 19, 83: 36, 84: 25, 85: 22, 86: 17, 87: 19, 88: 26, 89: 30, 90: 20,
    91: 15, 92: 21, 93: 11, 94: 8, 95: 8, 96: 19, 97: 5, 98: 8, 99: 8, 100: 11,
    101: 11, 102: 8, 103: 3, 104: 9, 105: 5, 106: 4, 107: 7, 108: 3, 109: 6, 110: 3,
    111: 5, 112: 4, 113: 5, 114: 6,
}


def normalize_surah_name(name: str) -> Optional[int]:
    """Normalize a surah name to its number.

    Args:
        name: Surah name in any format

    Returns:
        Surah number (1-114) or None if not found
    """
    if not name:
        return None

    # Normalize: lowercase, remove al-/an-/as-/at-/ad-/az-/ar-/ash- prefix, remove hyphens
    normalized = name.lower().strip()
    normalized = re.sub(r'^(al|an|as|at|ad|az|ar|ash|aal)-?', '', normalized)
    normalized = normalized.replace('-', '').replace(' ', '')

    return SURAH_NAMES.get(normalized)


def is_valid_reference(surah: int, ayah_start: int, ayah_end: Optional[int] = None) -> bool:
    """Check if a Quran reference is valid.

    Args:
        surah: Surah number
        ayah_start: Starting ayah number
        ayah_end: Optional ending ayah number for ranges

    Returns:
        True if valid, False otherwise
    """
    if surah < 1 or surah > 114:
        return False

    max_ayah = MAX_AYAHS.get(surah, 0)
    if ayah_start < 1 or ayah_start > max_ayah:
        return False

    if ayah_end is not None and (ayah_end < ayah_start or ayah_end > max_ayah):
        return False

    return True


def detect_quran_refs(text: str) -> List[Dict[str, Any]]:
    """Detect Quran references in text.

    Supports formats:
    - Quran 2:255
    - Qur'an 2:255-257
    - (2:255)
    - Surah Al-Baqarah
    - Al-Baqarah: 255
    - Q. 2:255

    Args:
        text: Text to search for references

    Returns:
        List of reference dicts with surah, ayah_start, ayah_end, surah_name, raw_text
    """
    if not text:
        return []

    refs = []
    seen = set()  # Avoid duplicates

    # Pattern 1: Explicit Quran prefix - Quran/Qur'an/Q. 2:255 or 2:255-257
    quran_prefix_pattern = r'''
        (?:Qur[\'']?[aā]n|quran|Q\.)\s*,?\s*       # Quran prefix (required)
        (\d{1,3})                                  # Surah number
        \s*:\s*                                    # Colon separator
        (\d{1,3})                                  # Ayah start
        (?:\s*[-–—]\s*(\d{1,3}))?                  # Optional ayah end
    '''

    for match in re.finditer(quran_prefix_pattern, text, re.IGNORECASE | re.VERBOSE):
        surah = int(match.group(1))
        ayah_start = int(match.group(2))
        ayah_end = int(match.group(3)) if match.group(3) else None

        if is_valid_reference(surah, ayah_start, ayah_end):
            key = (surah, ayah_start, ayah_end)
            if key not in seen:
                seen.add(key)
                refs.append({
                    'surah': surah,
                    'ayah_start': ayah_start,
                    'ayah_end': ayah_end,
                    'surah_name': SURAH_NUMBER_TO_NAME.get(surah),
                    'raw_text': match.group(0).strip(),
                })

    # Pattern 1b: Parenthetical format only in Islamic context - (2:255)
    # Only match if preceded by Islamic context words
    paren_pattern = r'''
        (?:verse|ayah|ayat|see|cf\.|compare|mentioned\s+in|stated\s+in|reference)\s*
        \(\s*
        (\d{1,3})                                  # Surah number
        \s*:\s*                                    # Colon separator
        (\d{1,3})                                  # Ayah start
        (?:\s*[-–—]\s*(\d{1,3}))?                  # Optional ayah end
        \s*\)
    '''

    for match in re.finditer(paren_pattern, text, re.IGNORECASE | re.VERBOSE):
        surah = int(match.group(1))
        ayah_start = int(match.group(2))
        ayah_end = int(match.group(3)) if match.group(3) else None

        if is_valid_reference(surah, ayah_start, ayah_end):
            key = (surah, ayah_start, ayah_end)
            if key not in seen:
                seen.add(key)
                refs.append({
                    'surah': surah,
                    'ayah_start': ayah_start,
                    'ayah_end': ayah_end,
                    'surah_name': SURAH_NUMBER_TO_NAME.get(surah),
                    'raw_text': match.group(0).strip(),
                })

    # Pattern 2: Surah name only - Surah Al-Baqarah
    surah_only_pattern = r'(?:Surah?|Sura)\s+((?:Al-?|An-?|As-?|At-?|Ad-?|Az-?|Ar-?|Ash-?|Aal-?)?[A-Za-z\-]+)'

    for match in re.finditer(surah_only_pattern, text, re.IGNORECASE):
        name = match.group(1)
        surah = normalize_surah_name(name)
        if surah:
            key = (surah, None, None)
            if key not in seen:
                seen.add(key)
                refs.append({
                    'surah': surah,
                    'ayah_start': None,
                    'ayah_end': None,
                    'surah_name': SURAH_NUMBER_TO_NAME.get(surah),
                    'raw_text': match.group(0).strip(),
                })

    # Pattern 3: Surah name with verse - Al-Baqarah: 255 or Al-Baqarah verse 255
    name_verse_pattern = r'((?:Al-?|An-?|As-?|At-?|Ad-?|Az-?|Ar-?|Ash-?|Aal-?)?[A-Za-z\-]+)[\s:,]+(?:verse\s+)?(\d{1,3})(?:\s*[-–—]\s*(\d{1,3}))?'

    for match in re.finditer(name_verse_pattern, text, re.IGNORECASE):
        name = match.group(1)
        surah = normalize_surah_name(name)
        if surah:
            ayah_start = int(match.group(2))
            ayah_end = int(match.group(3)) if match.group(3) else None

            if is_valid_reference(surah, ayah_start, ayah_end):
                key = (surah, ayah_start, ayah_end)
                if key not in seen:
                    seen.add(key)
                    refs.append({
                        'surah': surah,
                        'ayah_start': ayah_start,
                        'ayah_end': ayah_end,
                        'surah_name': SURAH_NUMBER_TO_NAME.get(surah),
                        'raw_text': match.group(0).strip(),
                    })

    logger.debug("quran_refs_detected", count=len(refs), text_length=len(text))
    return refs
