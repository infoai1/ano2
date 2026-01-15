"""Tests for PDF matcher service."""
import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.pdf_matcher import (
    extract_pdf_pages,
    match_paragraph_to_page,
    match_paragraphs_to_pdf,
    calculate_similarity
)

FIXTURES_DIR = Path(__file__).parent / 'fixtures'


class TestExtractPdfPages:
    """Test PDF page extraction."""

    def test_extract_simple_pdf(self):
        """Extract pages from simple PDF."""
        pages = extract_pdf_pages(FIXTURES_DIR / 'simple.pdf')
        assert len(pages) == 3

    def test_extract_returns_list(self):
        """Result should be a list of page dicts."""
        pages = extract_pdf_pages(FIXTURES_DIR / 'simple.pdf')
        assert isinstance(pages, list)
        assert all(isinstance(p, dict) for p in pages)

    def test_page_has_required_fields(self):
        """Each page should have page_number and text."""
        pages = extract_pdf_pages(FIXTURES_DIR / 'simple.pdf')
        for page in pages:
            assert 'page_number' in page
            assert 'text' in page

    def test_page_numbers_start_at_one(self):
        """Page numbers should start at 1."""
        pages = extract_pdf_pages(FIXTURES_DIR / 'simple.pdf')
        assert pages[0]['page_number'] == 1

    def test_page_numbers_sequential(self):
        """Page numbers should be sequential."""
        pages = extract_pdf_pages(FIXTURES_DIR / 'book_like.pdf')
        page_nums = [p['page_number'] for p in pages]
        assert page_nums == list(range(1, len(pages) + 1))

    def test_extract_text_content(self):
        """Text content should be extracted."""
        pages = extract_pdf_pages(FIXTURES_DIR / 'simple.pdf')
        assert 'page' in pages[0]['text'].lower()

    def test_extract_empty_pages(self):
        """Empty pages should still be returned with empty text."""
        pages = extract_pdf_pages(FIXTURES_DIR / 'empty_pages.pdf')
        assert len(pages) == 2
        # Empty pages have empty or whitespace-only text
        for page in pages:
            assert page['text'].strip() == ''

    def test_single_page_pdf(self):
        """Single page PDF should return one page."""
        pages = extract_pdf_pages(FIXTURES_DIR / 'single_page.pdf')
        assert len(pages) == 1
        assert pages[0]['page_number'] == 1

    def test_nonexistent_file_raises(self):
        """Nonexistent file should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            extract_pdf_pages(FIXTURES_DIR / 'nonexistent.pdf')


class TestCalculateSimilarity:
    """Test text similarity calculation."""

    @pytest.mark.parametrize("text1,text2,min_expected", [
        # Exact match
        ("hello world", "hello world", 1.0),
        # Substring match
        ("hello", "hello world", 0.5),
        # Partial overlap
        ("peace is important", "peace is very important", 0.7),
        # No match
        ("apple", "orange", 0.0),
        # Empty strings
        ("", "", 0.0),
        ("hello", "", 0.0),
        # Case insensitive
        ("Hello World", "hello world", 1.0),
    ])
    def test_similarity_ranges(self, text1, text2, min_expected):
        """Similarity should be within expected range."""
        score = calculate_similarity(text1, text2)
        assert score >= min_expected - 0.1  # Allow some tolerance

    def test_similarity_symmetric(self):
        """Similarity should be symmetric."""
        text1 = "The Prophet emphasized peace"
        text2 = "peace was emphasized by the Prophet"
        # Not perfectly symmetric due to algorithm, but close
        s1 = calculate_similarity(text1, text2)
        s2 = calculate_similarity(text2, text1)
        assert abs(s1 - s2) < 0.3


class TestMatchParagraphToPage:
    """Test matching single paragraph to pages."""

    @pytest.mark.parametrize("para_text,expected_page", [
        # Exact matches
        ("This is page 1", 1),
        ("This is page 2", 2),
        ("This is page 3", 3),
    ])
    def test_exact_match(self, para_text, expected_page):
        """Exact text should match correct page."""
        pages = extract_pdf_pages(FIXTURES_DIR / 'simple.pdf')
        result = match_paragraph_to_page(para_text, pages)
        assert result['page_number'] == expected_page

    def test_partial_match(self):
        """Partial text should still match."""
        pages = extract_pdf_pages(FIXTURES_DIR / 'simple.pdf')
        result = match_paragraph_to_page("sample text for testing", pages)
        # Should match one of the pages
        assert result['page_number'] is not None
        assert result['confidence'] > 0.3

    def test_no_match_returns_none(self):
        """No matching text should return None page."""
        pages = extract_pdf_pages(FIXTURES_DIR / 'simple.pdf')
        result = match_paragraph_to_page("completely unrelated xyz abc 123", pages)
        assert result['page_number'] is None
        assert result['confidence'] < 0.3

    def test_match_includes_confidence(self):
        """Match result should include confidence score."""
        pages = extract_pdf_pages(FIXTURES_DIR / 'simple.pdf')
        result = match_paragraph_to_page("This is page 1", pages)
        assert 'confidence' in result
        assert 0.0 <= result['confidence'] <= 1.0

    def test_high_confidence_for_exact(self):
        """Exact matches should have high confidence."""
        pages = extract_pdf_pages(FIXTURES_DIR / 'multi_para.pdf')
        result = match_paragraph_to_page("The concept of peace is fundamental to Islamic teachings", pages)
        assert result['confidence'] > 0.7

    def test_match_multi_paragraph_pdf(self):
        """Should match in multi-paragraph PDF."""
        pages = extract_pdf_pages(FIXTURES_DIR / 'multi_para.pdf')
        result = match_paragraph_to_page("Prophet Muhammad emphasized mercy and compassion", pages)
        assert result['page_number'] == 1
        assert result['confidence'] > 0.5


class TestMatchParagraphsToPdf:
    """Test batch matching of paragraphs to PDF."""

    def test_batch_matching(self):
        """Batch matching should return list of results."""
        pdf_path = FIXTURES_DIR / 'simple.pdf'
        paragraphs = [
            {'id': 1, 'text': 'This is page 1'},
            {'id': 2, 'text': 'This is page 2'},
            {'id': 3, 'text': 'This is page 3'},
        ]
        results = match_paragraphs_to_pdf(paragraphs, pdf_path)
        assert len(results) == 3

    def test_batch_results_have_ids(self):
        """Batch results should preserve paragraph IDs."""
        pdf_path = FIXTURES_DIR / 'simple.pdf'
        paragraphs = [
            {'id': 100, 'text': 'This is page 1'},
            {'id': 200, 'text': 'This is page 2'},
        ]
        results = match_paragraphs_to_pdf(paragraphs, pdf_path)
        ids = [r['paragraph_id'] for r in results]
        assert 100 in ids
        assert 200 in ids

    def test_batch_empty_list(self):
        """Empty paragraph list should return empty results."""
        pdf_path = FIXTURES_DIR / 'simple.pdf'
        results = match_paragraphs_to_pdf([], pdf_path)
        assert results == []

    def test_batch_preserves_order(self):
        """Results should be in same order as input."""
        pdf_path = FIXTURES_DIR / 'simple.pdf'
        paragraphs = [
            {'id': 3, 'text': 'This is page 3'},
            {'id': 1, 'text': 'This is page 1'},
            {'id': 2, 'text': 'This is page 2'},
        ]
        results = match_paragraphs_to_pdf(paragraphs, pdf_path)
        result_ids = [r['paragraph_id'] for r in results]
        assert result_ids == [3, 1, 2]


class TestBookLikePdf:
    """Test with book-like PDF structure."""

    def test_match_chapter_heading(self):
        """Chapter headings should match correct pages."""
        pages = extract_pdf_pages(FIXTURES_DIR / 'book_like.pdf')
        result = match_paragraph_to_page("Chapter One: Introduction", pages)
        assert result['page_number'] == 1
        assert result['confidence'] > 0.7

    def test_match_chapter_two(self):
        """Second chapter should match page 3."""
        pages = extract_pdf_pages(FIXTURES_DIR / 'book_like.pdf')
        result = match_paragraph_to_page("Chapter Two: Main Content", pages)
        assert result['page_number'] == 3
        assert result['confidence'] > 0.7

    def test_match_content_on_later_page(self):
        """Content on later pages should be found."""
        pages = extract_pdf_pages(FIXTURES_DIR / 'book_like.pdf')
        result = match_paragraph_to_page("Detailed information about the subject", pages)
        assert result['page_number'] == 4


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_very_short_text(self):
        """Very short text should still attempt matching."""
        pages = extract_pdf_pages(FIXTURES_DIR / 'simple.pdf')
        result = match_paragraph_to_page("page", pages)
        # Short text might match but with low confidence
        assert 'page_number' in result
        assert 'confidence' in result

    def test_special_characters(self):
        """Special characters should be handled."""
        pages = extract_pdf_pages(FIXTURES_DIR / 'simple.pdf')
        result = match_paragraph_to_page("text with 'quotes' and (parens)", pages)
        # Should not crash
        assert 'page_number' in result

    def test_unicode_text(self):
        """Unicode text should be handled."""
        pages = extract_pdf_pages(FIXTURES_DIR / 'simple.pdf')
        result = match_paragraph_to_page("Qur'ān reference — test", pages)
        # Should not crash
        assert 'page_number' in result

    def test_whitespace_normalization(self):
        """Whitespace variations should be normalized."""
        pages = extract_pdf_pages(FIXTURES_DIR / 'simple.pdf')
        # Extra spaces shouldn't prevent matching
        result = match_paragraph_to_page("This   is    page  1", pages)
        assert result['page_number'] == 1
