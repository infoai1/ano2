"""Tests for DOCX parser service."""
import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.docx_parser import parse_docx, detect_paragraph_type

FIXTURES_DIR = Path(__file__).parent / 'fixtures'


class TestParseDocx:
    """Test DOCX parsing functionality."""

    def test_parse_simple_docx(self):
        """Parse simple DOCX with plain paragraphs."""
        result = parse_docx(FIXTURES_DIR / 'simple.docx')
        assert 'paragraphs' in result
        assert len(result['paragraphs']) == 10
        assert result['paragraphs'][0]['text'] != ''

    def test_parse_returns_list(self):
        """Result should contain a list of paragraphs."""
        result = parse_docx(FIXTURES_DIR / 'simple.docx')
        assert isinstance(result['paragraphs'], list)

    def test_paragraph_has_required_fields(self):
        """Each paragraph should have text, type, and order_index."""
        result = parse_docx(FIXTURES_DIR / 'simple.docx')
        para = result['paragraphs'][0]
        assert 'text' in para
        assert 'type' in para
        assert 'order_index' in para

    def test_detect_headings(self):
        """Headings should be detected automatically."""
        result = parse_docx(FIXTURES_DIR / 'with_headings.docx')
        headings = [p for p in result['paragraphs'] if p['type'] == 'heading']
        assert len(headings) >= 1

    def test_heading_levels_detected(self):
        """Different heading levels should be detected."""
        result = parse_docx(FIXTURES_DIR / 'with_headings.docx')
        # Should have level 1, 2, and 3 headings
        levels = set(p.get('level', 0) for p in result['paragraphs'] if p['type'] == 'heading')
        assert 1 in levels
        assert 2 in levels or 3 in levels  # At least some hierarchy

    def test_parse_empty_docx(self):
        """Empty DOCX should return empty list."""
        result = parse_docx(FIXTURES_DIR / 'empty.docx')
        assert len(result['paragraphs']) == 0

    def test_parse_complex_docx(self):
        """Complex DOCX with many paragraphs should parse correctly."""
        result = parse_docx(FIXTURES_DIR / 'complex.docx')
        # Should have significant content
        assert len(result['paragraphs']) > 30

    def test_order_index_sequential(self):
        """Order index should be sequential starting from 0."""
        result = parse_docx(FIXTURES_DIR / 'simple.docx')
        indices = [p['order_index'] for p in result['paragraphs']]
        assert indices == list(range(len(indices)))

    def test_text_content_preserved(self):
        """Text content should be preserved accurately."""
        result = parse_docx(FIXTURES_DIR / 'simple.docx')
        assert 'paragraph' in result['paragraphs'][0]['text'].lower()

    def test_quote_detection(self):
        """Quote style paragraphs should be detected."""
        result = parse_docx(FIXTURES_DIR / 'with_quotes.docx')
        quotes = [p for p in result['paragraphs'] if p['type'] == 'quote']
        assert len(quotes) >= 1


class TestDetectParagraphType:
    """Test paragraph type detection."""

    @pytest.mark.parametrize("style_name,expected_type", [
        ('Heading 1', 'heading'),
        ('Heading 2', 'heading'),
        ('Heading 3', 'heading'),
        ('Title', 'heading'),
        ('Normal', 'paragraph'),
        ('Body Text', 'paragraph'),
        ('Quote', 'quote'),
        ('Intense Quote', 'quote'),
        ('Block Text', 'quote'),
        (None, 'paragraph'),
        ('', 'paragraph'),
    ])
    def test_style_to_type_mapping(self, style_name, expected_type):
        """Various styles should map to correct types."""
        result = detect_paragraph_type(style_name)
        assert result['type'] == expected_type

    @pytest.mark.parametrize("style_name,expected_level", [
        ('Heading 1', 1),
        ('Heading 2', 2),
        ('Heading 3', 3),
        ('Title', 1),
        ('Normal', 1),
    ])
    def test_heading_level_extraction(self, style_name, expected_level):
        """Heading levels should be extracted correctly."""
        result = detect_paragraph_type(style_name)
        assert result.get('level', 1) == expected_level


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_nonexistent_file_raises(self):
        """Nonexistent file should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            parse_docx(FIXTURES_DIR / 'nonexistent.docx')

    def test_invalid_file_raises(self):
        """Invalid DOCX should raise appropriate error."""
        # Create a fake file
        fake_file = FIXTURES_DIR / 'fake.docx'
        fake_file.write_text('not a docx file')
        try:
            with pytest.raises(Exception):  # Could be various exceptions
                parse_docx(fake_file)
        finally:
            fake_file.unlink()

    def test_whitespace_only_paragraphs_filtered(self):
        """Paragraphs with only whitespace should be filtered out."""
        result = parse_docx(FIXTURES_DIR / 'simple.docx')
        for para in result['paragraphs']:
            assert para['text'].strip() != ''


class TestChapterDetection:
    """Test chapter structure detection."""

    def test_chapters_detected(self):
        """Chapter structure should be detected from headings."""
        result = parse_docx(FIXTURES_DIR / 'with_headings.docx')
        assert 'chapters' in result
        assert len(result['chapters']) >= 1

    def test_chapter_has_title(self):
        """Each chapter should have a title."""
        result = parse_docx(FIXTURES_DIR / 'with_headings.docx')
        for chapter in result['chapters']:
            assert 'title' in chapter
            assert chapter['title'] != ''

    def test_chapter_has_paragraphs(self):
        """Each chapter should list its paragraph indices."""
        result = parse_docx(FIXTURES_DIR / 'with_headings.docx')
        for chapter in result['chapters']:
            assert 'paragraph_indices' in chapter
            assert isinstance(chapter['paragraph_indices'], list)
