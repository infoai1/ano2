"""Tests for footnote linking service."""
import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.footnote_linker import (
    detect_footnote_markers,
    detect_footnotes,
    link_footnotes,
    extract_footnote_content
)


class TestDetectFootnoteMarkers:
    """Test footnote marker detection in text."""

    @pytest.mark.parametrize("text,expected_markers", [
        # Superscript numbers
        ("The Prophet said¹ that peace", ["1"]),
        ("The text² mentions this³", ["2", "3"]),
        ("Quote here¹²³", ["123"]),  # Adjacent superscripts treated as one marker

        # Bracketed numbers
        ("The verse [1] states", ["1"]),
        ("See reference [2] and [3]", ["2", "3"]),
        ("Note [12] is important", ["12"]),

        # Parenthetical numbers
        ("As mentioned (1)", ["1"]),
        ("Reference (2) and (3)", ["2", "3"]),

        # Asterisk markers
        ("Important point*", ["*"]),
        ("First* and second**", ["*", "**"]),

        # Dagger and double dagger
        ("Note here†", ["†"]),
        ("See also‡", ["‡"]),
    ])
    def test_marker_detection(self, text, expected_markers):
        """Various footnote marker formats should be detected."""
        markers = detect_footnote_markers(text)
        assert len(markers) == len(expected_markers)
        for expected in expected_markers:
            assert any(m['marker'] == expected for m in markers)

    def test_marker_has_position(self):
        """Detected markers should include position information."""
        markers = detect_footnote_markers("Text here¹ continues")
        assert len(markers) == 1
        assert 'position' in markers[0]
        assert markers[0]['position'] > 0

    def test_no_markers(self):
        """Text without markers should return empty list."""
        markers = detect_footnote_markers("Plain text without markers")
        assert len(markers) == 0

    def test_empty_text(self):
        """Empty text should return empty list."""
        markers = detect_footnote_markers("")
        assert len(markers) == 0


class TestDetectFootnotes:
    """Test footnote content detection."""

    @pytest.mark.parametrize("text,expected_count", [
        # Numbered footnotes
        ("1. Sahih Bukhari 1234", 1),
        ("1. First note\n2. Second note", 2),
        ("1. Note one\n2. Note two\n3. Note three", 3),

        # Superscript style in footnote area
        ("¹ Quran 2:255", 1),
        ("¹ First\n² Second", 2),

        # Bracketed style
        ("[1] Reference here", 1),
        ("[1] First ref\n[2] Second ref", 2),
    ])
    def test_footnote_detection(self, text, expected_count):
        """Various footnote formats should be detected."""
        footnotes = detect_footnotes(text)
        assert len(footnotes) == expected_count

    def test_footnote_has_number(self):
        """Detected footnotes should have a number."""
        footnotes = detect_footnotes("1. Bukhari 1234")
        assert len(footnotes) == 1
        assert footnotes[0]['number'] == "1"

    def test_footnote_has_content(self):
        """Detected footnotes should have content."""
        footnotes = detect_footnotes("1. Sahih Bukhari 1234")
        assert len(footnotes) == 1
        assert 'content' in footnotes[0]
        assert 'Bukhari' in footnotes[0]['content']

    def test_no_footnotes(self):
        """Text without footnotes should return empty list."""
        footnotes = detect_footnotes("Regular paragraph text")
        assert len(footnotes) == 0


class TestLinkFootnotes:
    """Test linking markers to footnotes."""

    @pytest.mark.parametrize("para_text,footnotes,expected_links", [
        # Single marker and footnote
        (
            "The Prophet said¹ that peace is best",
            [{"number": "1", "content": "Sahih Bukhari 1234"}],
            [{"marker": "1", "content": "Sahih Bukhari 1234"}]
        ),
        # Multiple markers
        (
            "The verse¹ mentions peace² in context",
            [
                {"number": "1", "content": "Quran 2:255"},
                {"number": "2", "content": "Quran 3:18"}
            ],
            [
                {"marker": "1", "content": "Quran 2:255"},
                {"marker": "2", "content": "Quran 3:18"}
            ]
        ),
        # Bracketed markers
        (
            "See reference [1] for details",
            [{"number": "1", "content": "Muslim 567"}],
            [{"marker": "1", "content": "Muslim 567"}]
        ),
    ])
    def test_linking(self, para_text, footnotes, expected_links):
        """Markers should be linked to matching footnotes."""
        result = link_footnotes(para_text, footnotes)
        assert len(result) == len(expected_links)
        for expected in expected_links:
            matching = [r for r in result if r['marker'] == expected['marker']]
            assert len(matching) == 1
            assert expected['content'] in matching[0]['content']

    def test_no_markers_no_links(self):
        """Text without markers should return no links."""
        result = link_footnotes(
            "No footnotes here",
            [{"number": "1", "content": "Unused footnote"}]
        )
        assert len(result) == 0

    def test_no_footnotes_no_links(self):
        """No footnotes should return no links."""
        result = link_footnotes("Text with marker¹", [])
        assert len(result) == 0

    def test_unmatched_marker(self):
        """Unmatched markers should not create links."""
        result = link_footnotes(
            "Text with marker¹ and marker²",
            [{"number": "1", "content": "Only footnote 1"}]
        )
        # Only one link should be created
        assert len(result) == 1
        assert result[0]['marker'] == "1"

    def test_link_includes_position(self):
        """Links should include marker position."""
        result = link_footnotes(
            "Beginning¹ middle² end",
            [
                {"number": "1", "content": "First"},
                {"number": "2", "content": "Second"}
            ]
        )
        assert len(result) == 2
        # First marker should have lower position
        positions = {r['marker']: r.get('position', 0) for r in result}
        assert positions.get("1", 0) < positions.get("2", 999)


class TestExtractFootnoteContent:
    """Test footnote content extraction."""

    @pytest.mark.parametrize("raw_footnote,expected_content", [
        ("1. Sahih Bukhari 1234", "Sahih Bukhari 1234"),
        ("1) Quran 2:255", "Quran 2:255"),
        ("[1] Muslim 567", "Muslim 567"),
        ("¹ Reference text", "Reference text"),
        ("* Important note", "Important note"),
    ])
    def test_content_extraction(self, raw_footnote, expected_content):
        """Content should be extracted from various formats."""
        content = extract_footnote_content(raw_footnote)
        assert expected_content in content

    def test_strips_whitespace(self):
        """Extracted content should have trimmed whitespace."""
        content = extract_footnote_content("1.   Bukhari 123   ")
        assert not content.startswith(" ")
        assert not content.endswith(" ")


class TestEdgeCases:
    """Test edge cases."""

    def test_unicode_superscripts(self):
        """Unicode superscript numbers should be detected."""
        markers = detect_footnote_markers("Text with ¹ and ² and ³")
        assert len(markers) == 3

    def test_mixed_marker_styles(self):
        """Mixed marker styles should all be detected."""
        text = "First¹ second[2] third(3)"
        markers = detect_footnote_markers(text)
        assert len(markers) == 3

    def test_footnote_with_reference(self):
        """Footnotes containing Quran/Hadith refs should be detected."""
        footnotes = detect_footnotes("1. See Quran 2:255 for details")
        assert len(footnotes) == 1
        assert "Quran 2:255" in footnotes[0]['content']

    def test_multiline_footnote(self):
        """Multi-line footnotes should be handled."""
        text = """1. This is the first footnote
           that spans multiple lines
        2. This is the second footnote"""
        footnotes = detect_footnotes(text)
        assert len(footnotes) == 2

    def test_special_characters_in_footnote(self):
        """Special characters in footnotes should be preserved."""
        footnotes = detect_footnotes("1. Reference: Ibn Maja (d. 273/887)")
        assert len(footnotes) == 1
        assert "273/887" in footnotes[0]['content']


class TestComplexScenarios:
    """Test complex real-world scenarios."""

    def test_scholarly_paragraph_with_footnotes(self):
        """Full paragraph with multiple footnote types."""
        para = "The Prophet¹ emphasized peace² as mentioned in the Quran[3]."
        footnotes = [
            {"number": "1", "content": "Muhammad ibn Abdullah (570-632 CE)"},
            {"number": "2", "content": "Sahih Bukhari 1234"},
            {"number": "3", "content": "Quran 2:255"},
        ]
        links = link_footnotes(para, footnotes)
        assert len(links) == 3

    def test_book_style_footnotes(self):
        """Book-style footnote section."""
        footnote_section = """
        1. Sahih Bukhari, Book of Faith, Hadith 1
        2. See also Quran 2:255, known as Ayat al-Kursi
        3. Muslim ibn al-Hajjaj (815-875 CE)
        """
        footnotes = detect_footnotes(footnote_section)
        assert len(footnotes) == 3

    def test_empty_inputs(self):
        """Empty inputs should be handled gracefully."""
        assert link_footnotes("", []) == []
        assert link_footnotes("text", []) == []
        assert detect_footnote_markers("") == []
        assert detect_footnotes("") == []
