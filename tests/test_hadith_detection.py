"""Tests for Hadith reference detection."""
import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.hadith_detector import detect_hadith_refs, normalize_collection_name, COLLECTION_NAMES


class TestDetectHadithRefs:
    """Test Hadith reference detection."""

    # Sahih Bukhari formats
    @pytest.mark.parametrize("text,expected_count,expected_collection,expected_number", [
        ("Sahih Bukhari 1234", 1, "bukhari", "1234"),
        ("Sahih al-Bukhari 1234", 1, "bukhari", "1234"),
        ("Bukhari 1234", 1, "bukhari", "1234"),
        ("Bukhari, 1234", 1, "bukhari", "1234"),
        ("Bukhari no. 1234", 1, "bukhari", "1234"),
        ("Bukhari #1234", 1, "bukhari", "1234"),
        ("Bukhari: 1234", 1, "bukhari", "1234"),
        ("bukhari 1234", 1, "bukhari", "1234"),  # lowercase
        ("BUKHARI 1234", 1, "bukhari", "1234"),  # uppercase
    ])
    def test_bukhari_formats(self, text, expected_count, expected_collection, expected_number):
        """Bukhari references in various formats."""
        refs = detect_hadith_refs(text)
        assert len(refs) == expected_count
        assert refs[0]['collection'] == expected_collection
        assert refs[0]['hadith_number'] == expected_number

    # Sahih Muslim formats
    @pytest.mark.parametrize("text,expected_count,expected_collection,expected_number", [
        ("Sahih Muslim 567", 1, "muslim", "567"),
        ("Muslim 567", 1, "muslim", "567"),
        ("Muslim, 567", 1, "muslim", "567"),
        ("Muslim no. 567", 1, "muslim", "567"),
    ])
    def test_muslim_formats(self, text, expected_count, expected_collection, expected_number):
        """Muslim references in various formats."""
        refs = detect_hadith_refs(text)
        assert len(refs) == expected_count
        assert refs[0]['collection'] == expected_collection
        assert refs[0]['hadith_number'] == expected_number

    # Other major collections
    @pytest.mark.parametrize("text,expected_collection", [
        ("Sunan Abu Dawud 123", "abudawud"),
        ("Abu Dawud 123", "abudawud"),
        ("Abu Dawood 123", "abudawud"),
        ("Tirmidhi 456", "tirmidhi"),
        ("Jami at-Tirmidhi 456", "tirmidhi"),
        ("Sunan at-Tirmidhi 456", "tirmidhi"),
        ("Tirmizi 456", "tirmidhi"),
        ("Ibn Majah 789", "ibnmajah"),
        ("Sunan Ibn Majah 789", "ibnmajah"),
        ("Ibn Maja 789", "ibnmajah"),
        ("Nasai 321", "nasai"),
        ("Sunan an-Nasai 321", "nasai"),
        ("An-Nasai 321", "nasai"),
        ("Muwatta Malik 111", "muwatta"),
        ("Muwatta 111", "muwatta"),
        ("Malik's Muwatta 111", "muwatta"),
    ])
    def test_other_collections(self, text, expected_collection):
        """Other hadith collections should be detected."""
        refs = detect_hadith_refs(text)
        assert len(refs) == 1
        assert refs[0]['collection'] == expected_collection

    # Musnad and other collections
    @pytest.mark.parametrize("text,expected_collection", [
        ("Musnad Ahmad 12345", "ahmad"),
        ("Ahmad 12345", "ahmad"),
        ("Musnad Ahmed 12345", "ahmad"),
        ("Darimi 999", "darimi"),
        ("Sunan ad-Darimi 999", "darimi"),
        ("Bayhaqi 888", "bayhaqi"),
    ])
    def test_additional_collections(self, text, expected_collection):
        """Additional hadith collections."""
        refs = detect_hadith_refs(text)
        assert len(refs) == 1
        assert refs[0]['collection'] == expected_collection

    # Book and chapter format
    @pytest.mark.parametrize("text,expected_collection,expected_number", [
        ("Bukhari, Book 1, Hadith 1", "bukhari", "1:1"),
        ("Muslim Book 5 Hadith 23", "muslim", "5:23"),
        ("Tirmidhi Vol. 3, No. 456", "tirmidhi", "3:456"),
    ])
    def test_book_chapter_format(self, text, expected_collection, expected_number):
        """Book/chapter format references."""
        refs = detect_hadith_refs(text)
        assert len(refs) == 1
        assert refs[0]['collection'] == expected_collection
        assert refs[0]['hadith_number'] == expected_number

    # Multiple references
    @pytest.mark.parametrize("text,expected_count", [
        ("Bukhari 1234 and Muslim 567", 2),
        ("See Bukhari 123, Bukhari 456, Bukhari 789", 3),
        ("Tirmidhi 100, Abu Dawud 200, Ibn Majah 300", 3),
        ("As narrated in Bukhari 1 and also Muslim 2", 2),
    ])
    def test_multiple_references(self, text, expected_count):
        """Multiple hadith references should all be detected."""
        refs = detect_hadith_refs(text)
        assert len(refs) == expected_count

    # Edge cases - no matches
    @pytest.mark.parametrize("text", [
        "",
        "   ",
        "No references here",
        "John Smith 1234",  # Not a collection
        "The Muslim community",  # Muslim without number
        "Chapter 123",  # Not hadith
    ])
    def test_no_match_cases(self, text):
        """Non-hadith text should return empty list."""
        refs = detect_hadith_refs(text)
        assert len(refs) == 0

    # Reference metadata
    def test_reference_has_raw_text(self):
        """Each reference should include the raw matched text."""
        refs = detect_hadith_refs("The Prophet said (Bukhari 1234)")
        assert len(refs) == 1
        assert 'raw_text' in refs[0]
        assert 'Bukhari' in refs[0]['raw_text']
        assert '1234' in refs[0]['raw_text']

    def test_reference_has_collection_full_name(self):
        """References should include full collection name."""
        refs = detect_hadith_refs("Bukhari 1234")
        assert len(refs) == 1
        assert refs[0].get('collection_name') == 'Sahih al-Bukhari'


class TestNormalizeCollectionName:
    """Test collection name normalization."""

    @pytest.mark.parametrize("input_name,expected", [
        ("Bukhari", "bukhari"),
        ("bukhari", "bukhari"),
        ("BUKHARI", "bukhari"),
        ("al-Bukhari", "bukhari"),
        ("Sahih Bukhari", "bukhari"),
        ("Sahih al-Bukhari", "bukhari"),
        ("Muslim", "muslim"),
        ("Sahih Muslim", "muslim"),
        ("Abu Dawud", "abudawud"),
        ("Abu Dawood", "abudawud"),
        ("Tirmidhi", "tirmidhi"),
        ("Tirmizi", "tirmidhi"),
        ("at-Tirmidhi", "tirmidhi"),
        ("Ibn Majah", "ibnmajah"),
        ("Ibn Maja", "ibnmajah"),
        ("Nasai", "nasai"),
        ("an-Nasai", "nasai"),
        ("Muwatta", "muwatta"),
        ("Ahmad", "ahmad"),
        ("Ahmed", "ahmad"),
    ])
    def test_name_normalization(self, input_name, expected):
        """Various collection name formats should normalize correctly."""
        result = normalize_collection_name(input_name)
        assert result == expected

    def test_unknown_name_returns_none(self):
        """Unknown collection names should return None."""
        assert normalize_collection_name("NotACollection") is None
        assert normalize_collection_name("") is None


class TestCollectionNameMapping:
    """Test collection name mappings."""

    def test_six_major_books_mapped(self):
        """The six major hadith books should all be mapped."""
        major_books = ['bukhari', 'muslim', 'abudawud', 'tirmidhi', 'nasai', 'ibnmajah']
        for book in major_books:
            assert book in COLLECTION_NAMES.values(), f"{book} not mapped"

    def test_collection_full_names(self):
        """Collections should have full names available."""
        refs = detect_hadith_refs("Bukhari 1")
        assert refs[0]['collection_name'] is not None


class TestComplexTexts:
    """Test with complex, realistic text samples."""

    def test_paragraph_with_mixed_references(self):
        """Real paragraph with multiple reference styles."""
        text = """
        The Prophet (peace be upon him) said, "The best of you are those who
        learn the Quran and teach it" (Bukhari 5027). This is also narrated
        in Muslim 817 with similar wording. See also Tirmidhi 2907.
        """
        refs = detect_hadith_refs(text)
        assert len(refs) == 3

    def test_footnote_style_reference(self):
        """References in footnote format."""
        text = "¹ Sahih al-Bukhari 1; Muslim 2"
        refs = detect_hadith_refs(text)
        assert len(refs) == 2

    def test_scholarly_citation(self):
        """Scholarly citation format."""
        text = "This hadith is reported in Bukhari 6018 and Muslim 2586"
        refs = detect_hadith_refs(text)
        assert len(refs) == 2

    def test_arabic_transliteration_variants(self):
        """Various transliteration spellings."""
        text = "Reported in Saheeh al-Bukhaaree 123 and Saheeh Muslim 456"
        refs = detect_hadith_refs(text)
        assert len(refs) >= 1  # At least Bukhari variant

    def test_chain_of_narration_mention(self):
        """Text mentioning isnad should not false positive."""
        text = "The isnad includes Muslim ibn al-Hajjaj but this is not a hadith reference"
        refs = detect_hadith_refs(text)
        # Should not match "Muslim" without a number
        assert len(refs) == 0
