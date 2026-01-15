"""Tests for Quran reference detection."""
import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.quran_detector import detect_quran_refs, normalize_surah_name, SURAH_NAMES


class TestDetectQuranRefs:
    """Test Quran reference detection."""

    # Standard numeric formats
    @pytest.mark.parametrize("text,expected_count,expected_surah,expected_ayah", [
        # Basic formats
        ("Quran 2:255", 1, 2, 255),
        ("quran 2:255", 1, 2, 255),  # lowercase
        ("QURAN 2:255", 1, 2, 255),  # uppercase
        ("Qur'an 2:255", 1, 2, 255),  # apostrophe variant
        ("Qur'ān 2:255", 1, 2, 255),  # with macron
        ("Quran, 2:255", 1, 2, 255),  # with comma

        # Parenthetical format (requires context)
        ("see (2:255)", 1, 2, 255),
        ("verse ( 2:255 )", 1, 2, 255),  # with spaces
        ("cf. (2: 255)", 1, 2, 255),  # space after colon

        # Different surahs
        ("Quran 1:1", 1, 1, 1),
        ("Quran 114:6", 1, 114, 6),
        ("Quran 36:1", 1, 36, 1),

        # With verse text
        ("The verse (2:255) speaks of God's throne", 1, 2, 255),
        ("See Quran 3:19 for guidance", 1, 3, 19),
    ])
    def test_numeric_formats(self, text, expected_count, expected_surah, expected_ayah):
        """Numeric Quran references should be detected."""
        refs = detect_quran_refs(text)
        assert len(refs) == expected_count
        assert refs[0]['surah'] == expected_surah
        assert refs[0]['ayah_start'] == expected_ayah

    # Range formats
    @pytest.mark.parametrize("text,expected_surah,expected_start,expected_end", [
        ("Quran 2:255-257", 2, 255, 257),
        ("Quran 1:1-7", 1, 1, 7),
        ("see (2:1-5)", 2, 1, 5),
        ("Quran 36:1-10", 36, 1, 10),
        ("Quran 2:255–257", 2, 255, 257),  # en-dash
        ("Quran 2:255—257", 2, 255, 257),  # em-dash
    ])
    def test_range_formats(self, text, expected_surah, expected_start, expected_end):
        """Verse ranges should be detected."""
        refs = detect_quran_refs(text)
        assert len(refs) == 1
        assert refs[0]['surah'] == expected_surah
        assert refs[0]['ayah_start'] == expected_start
        assert refs[0]['ayah_end'] == expected_end

    # Surah name formats
    @pytest.mark.parametrize("text,expected_surah", [
        ("Surah Al-Baqarah", 2),
        ("Surah al-Baqarah", 2),  # lowercase al
        ("Sura Baqarah", 2),  # without Al-
        ("Surah Al-Fatiha", 1),
        ("Surah Fatiha", 1),
        ("Surah Al-Fatihah", 1),
        ("Surah Yasin", 36),
        ("Surah Ya-Sin", 36),
        ("Surah Yaseen", 36),
        ("Surah An-Nas", 114),
        ("Surah Al-Ikhlas", 112),
        ("Surah Al-Kahf", 18),
        ("Surah Maryam", 19),
        ("Surah Yusuf", 12),
    ])
    def test_surah_name_formats(self, text, expected_surah):
        """Surah names should be detected and mapped."""
        refs = detect_quran_refs(text)
        assert len(refs) == 1
        assert refs[0]['surah'] == expected_surah

    # Surah name with verse
    @pytest.mark.parametrize("text,expected_surah,expected_ayah", [
        ("Al-Baqarah: 255", 2, 255),
        ("Al-Baqarah:255", 2, 255),
        ("Al-Baqarah, verse 255", 2, 255),
        ("Al-Baqarah verse 255", 2, 255),
        ("Al-Baqarah, 255", 2, 255),
        ("Al-Fatiha: 1-7", 1, 1),
    ])
    def test_surah_name_with_verse(self, text, expected_surah, expected_ayah):
        """Surah names with verse numbers should be detected."""
        refs = detect_quran_refs(text)
        assert len(refs) >= 1
        assert refs[0]['surah'] == expected_surah
        assert refs[0]['ayah_start'] == expected_ayah

    # Multiple references
    @pytest.mark.parametrize("text,expected_count", [
        ("See Quran 2:255 and Quran 3:1", 2),
        ("Compare verse (2:255) with verse (3:18)", 2),
        ("Surah Al-Fatiha and Surah Al-Baqarah", 2),
        ("Quran 2:255, Quran 3:18, and Quran 4:1", 3),
        ("Quran 2:255 and Quran 2:256 and Quran 2:257", 3),  # explicit prefix each
    ])
    def test_multiple_references(self, text, expected_count):
        """Multiple references should all be detected."""
        refs = detect_quran_refs(text)
        assert len(refs) == expected_count

    # Edge cases - no matches
    @pytest.mark.parametrize("text", [
        "",
        "   ",
        "No references here",
        "Quran 999:999",  # Invalid surah (only 114)
        "Quran 2:300",  # Invalid ayah (Baqarah has 286)
        "Quran 0:1",  # Invalid surah (starts at 1)
    ])
    def test_no_match_cases(self, text):
        """Non-Quran text should return empty list."""
        refs = detect_quran_refs(text)
        assert len(refs) == 0

    # Reference metadata
    def test_reference_has_raw_text(self):
        """Each reference should include the raw matched text."""
        refs = detect_quran_refs("The verse Quran 2:255 is important")
        assert len(refs) == 1
        assert 'raw_text' in refs[0]
        assert '2:255' in refs[0]['raw_text']

    def test_reference_has_surah_name(self):
        """References should include surah name when available."""
        refs = detect_quran_refs("Quran 1:1")
        assert len(refs) == 1
        assert refs[0].get('surah_name') == 'Al-Fatihah'


class TestNormalizeSurahName:
    """Test surah name normalization."""

    @pytest.mark.parametrize("input_name,expected_surah", [
        ("Al-Baqarah", 2),
        ("al-baqarah", 2),
        ("AL-BAQARAH", 2),
        ("Baqarah", 2),
        ("Fatiha", 1),
        ("Al-Fatiha", 1),
        ("Fatihah", 1),
        ("Al-Fatihah", 1),
        ("Yasin", 36),
        ("Ya-Sin", 36),
        ("Yaseen", 36),
    ])
    def test_name_normalization(self, input_name, expected_surah):
        """Various surah name formats should normalize correctly."""
        result = normalize_surah_name(input_name)
        assert result == expected_surah

    def test_unknown_name_returns_none(self):
        """Unknown names should return None."""
        assert normalize_surah_name("NotASurah") is None
        assert normalize_surah_name("") is None


class TestSurahNameMapping:
    """Test surah name to number mapping."""

    def test_all_114_surahs_mapped(self):
        """All 114 surahs should have at least one name mapping."""
        mapped_surahs = set(SURAH_NAMES.values())
        for i in range(1, 115):
            assert i in mapped_surahs, f"Surah {i} not mapped"

    def test_common_surahs_have_variants(self):
        """Common surahs should have multiple name variants."""
        # Check Al-Fatihah variants
        assert normalize_surah_name("Fatiha") == 1
        assert normalize_surah_name("Fatihah") == 1
        assert normalize_surah_name("Al-Fatiha") == 1

        # Check Al-Baqarah variants
        assert normalize_surah_name("Baqarah") == 2
        assert normalize_surah_name("Baqara") == 2


class TestComplexTexts:
    """Test with complex, realistic text samples."""

    def test_paragraph_with_mixed_references(self):
        """Real paragraph with multiple reference styles."""
        text = """
        The Prophet mentioned that Ayat al-Kursi (2:255) is the greatest verse.
        This is supported by Surah Al-Baqarah verse 256 which states there is
        no compulsion in religion. See also Quran 3:18-19 for related guidance.
        """
        refs = detect_quran_refs(text)
        assert len(refs) >= 3

    def test_footnote_style_reference(self):
        """References in footnote format."""
        text = "¹ Quran 2:255; see also Quran 3:18"
        refs = detect_quran_refs(text)
        assert len(refs) == 2

    def test_scholarly_citation(self):
        """Scholarly citation format."""
        text = "As stated in Q. 2:255 (Ayat al-Kursi)"
        refs = detect_quran_refs(text)
        assert len(refs) >= 1
        assert refs[0]['surah'] == 2
        assert refs[0]['ayah_start'] == 255
