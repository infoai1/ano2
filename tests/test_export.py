"""Tests for export service."""
import pytest
import json
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.exporter import (
    export_book_json,
    export_lightrag_json,
    build_paragraph_export,
    build_group_export,
    validate_export_data,
)


class TestBuildParagraphExport:
    """Test paragraph export building."""

    @pytest.mark.parametrize("para,expected_keys", [
        # Minimal paragraph
        (
            {'id': 1, 'text': 'Hello world', 'order_index': 0},
            ['id', 'text', 'order_index']
        ),
        # Paragraph with chapter
        (
            {'id': 2, 'text': 'Content', 'order_index': 1, 'chapter_title': 'Introduction'},
            ['id', 'text', 'order_index', 'chapter_title']
        ),
        # Paragraph with page number
        (
            {'id': 3, 'text': 'Content', 'order_index': 2, 'page_number': 42},
            ['id', 'text', 'order_index', 'page_number']
        ),
        # Full paragraph
        (
            {
                'id': 4, 'text': 'Full content', 'order_index': 3,
                'chapter_title': 'Chapter 1', 'page_number': 10,
                'is_heading': True, 'heading_level': 1,
                'quran_refs': [{'surah': 2, 'ayah': 255}],
                'hadith_refs': [{'collection': 'bukhari', 'number': '1234'}],
            },
            ['id', 'text', 'order_index', 'chapter_title', 'page_number', 'is_heading', 'heading_level', 'quran_refs', 'hadith_refs']
        ),
    ])
    def test_paragraph_export_has_keys(self, para, expected_keys):
        """Exported paragraph should have expected keys."""
        result = build_paragraph_export(para)
        for key in expected_keys:
            assert key in result

    def test_paragraph_export_preserves_text(self):
        """Exported paragraph should preserve text content."""
        para = {'id': 1, 'text': 'The Prophet (peace be upon him) said...', 'order_index': 0}
        result = build_paragraph_export(para)
        assert result['text'] == para['text']

    def test_paragraph_export_excludes_internal_fields(self):
        """Export should not include internal database fields."""
        para = {
            'id': 1, 'text': 'Content', 'order_index': 0,
            '_sa_instance_state': 'internal',
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
        }
        result = build_paragraph_export(para)
        assert '_sa_instance_state' not in result

    def test_paragraph_export_includes_group_id(self):
        """Paragraph with group_id should include it in export."""
        para = {'id': 1, 'text': 'Content', 'order_index': 0, 'group_id': 5}
        result = build_paragraph_export(para)
        assert result.get('group_id') == 5


class TestBuildGroupExport:
    """Test group export building."""

    @pytest.mark.parametrize("group,expected_keys", [
        # Minimal group
        (
            {'order_index': 0, 'token_count': 512, 'paragraphs': []},
            ['order_index', 'token_count', 'paragraph_ids']
        ),
        # Group with paragraphs
        (
            {
                'order_index': 1, 'token_count': 600,
                'paragraphs': [{'id': 1}, {'id': 2}, {'id': 3}]
            },
            ['order_index', 'token_count', 'paragraph_ids']
        ),
    ])
    def test_group_export_has_keys(self, group, expected_keys):
        """Exported group should have expected keys."""
        result = build_group_export(group)
        for key in expected_keys:
            assert key in result

    def test_group_export_extracts_paragraph_ids(self):
        """Group export should extract paragraph IDs."""
        group = {
            'order_index': 0, 'token_count': 500,
            'paragraphs': [{'id': 10}, {'id': 20}, {'id': 30}]
        }
        result = build_group_export(group)
        assert result['paragraph_ids'] == [10, 20, 30]

    def test_group_export_preserves_token_count(self):
        """Group export should preserve token count."""
        group = {'order_index': 0, 'token_count': 789, 'paragraphs': []}
        result = build_group_export(group)
        assert result['token_count'] == 789


class TestExportBookJson:
    """Test Book JSON export format."""

    @pytest.fixture
    def sample_book_data(self):
        """Sample book data for testing."""
        return {
            'title': 'The Way of Peace',
            'author': 'Maulana Wahiduddin Khan',
            'slug': 'the-way-of-peace',
            'paragraphs': [
                {'id': 1, 'text': 'First paragraph.', 'order_index': 0, 'token_count': 100},
                {'id': 2, 'text': 'Second paragraph.', 'order_index': 1, 'token_count': 150},
                {'id': 3, 'text': 'Third paragraph.', 'order_index': 2, 'token_count': 200},
            ],
            'groups': [
                {'order_index': 0, 'token_count': 450, 'paragraphs': [
                    {'id': 1}, {'id': 2}, {'id': 3}
                ]}
            ]
        }

    def test_book_json_has_metadata(self, sample_book_data):
        """Book JSON should include metadata."""
        result = export_book_json(sample_book_data)
        data = json.loads(result)
        assert data['title'] == 'The Way of Peace'
        assert data['author'] == 'Maulana Wahiduddin Khan'
        assert data['slug'] == 'the-way-of-peace'

    def test_book_json_has_paragraphs(self, sample_book_data):
        """Book JSON should include paragraphs."""
        result = export_book_json(sample_book_data)
        data = json.loads(result)
        assert 'paragraphs' in data
        assert len(data['paragraphs']) == 3

    def test_book_json_has_groups(self, sample_book_data):
        """Book JSON should include groups."""
        result = export_book_json(sample_book_data)
        data = json.loads(result)
        assert 'groups' in data
        assert len(data['groups']) == 1

    def test_book_json_has_export_timestamp(self, sample_book_data):
        """Book JSON should include export timestamp."""
        result = export_book_json(sample_book_data)
        data = json.loads(result)
        assert 'exported_at' in data

    def test_book_json_valid_format(self, sample_book_data):
        """Book JSON should be valid JSON."""
        result = export_book_json(sample_book_data)
        # Should not raise
        data = json.loads(result)
        assert isinstance(data, dict)

    def test_book_json_with_chapters(self):
        """Book JSON should include chapter information."""
        data = {
            'title': 'Test Book',
            'paragraphs': [
                {'id': 1, 'text': 'Intro', 'order_index': 0, 'chapter_title': 'Introduction'},
                {'id': 2, 'text': 'Ch1 content', 'order_index': 1, 'chapter_title': 'Chapter 1'},
            ],
            'groups': []
        }
        result = export_book_json(data)
        parsed = json.loads(result)
        assert parsed['paragraphs'][0]['chapter_title'] == 'Introduction'

    def test_book_json_with_references(self):
        """Book JSON should include Quran/Hadith references."""
        data = {
            'title': 'Test Book',
            'paragraphs': [
                {
                    'id': 1, 'text': 'See Quran 2:255', 'order_index': 0,
                    'quran_refs': [{'surah': 2, 'ayah': 255, 'surah_name': 'Al-Baqarah'}]
                },
            ],
            'groups': []
        }
        result = export_book_json(data)
        parsed = json.loads(result)
        assert len(parsed['paragraphs'][0]['quran_refs']) == 1


class TestExportLightragJson:
    """Test LightRAG JSON export format."""

    @pytest.fixture
    def sample_lightrag_data(self):
        """Sample data for LightRAG export."""
        return {
            'title': 'The Way of Peace',
            'author': 'Maulana Wahiduddin Khan',
            'slug': 'the-way-of-peace',
            'paragraphs': [
                {'id': 1, 'text': 'First paragraph about peace.', 'order_index': 0, 'token_count': 100, 'group_id': 0},
                {'id': 2, 'text': 'Second paragraph about harmony.', 'order_index': 1, 'token_count': 150, 'group_id': 0},
                {'id': 3, 'text': 'Third paragraph about unity.', 'order_index': 2, 'token_count': 200, 'group_id': 0},
            ],
            'groups': [
                {
                    'order_index': 0, 'token_count': 450,
                    'paragraphs': [
                        {'id': 1, 'text': 'First paragraph about peace.'},
                        {'id': 2, 'text': 'Second paragraph about harmony.'},
                        {'id': 3, 'text': 'Third paragraph about unity.'},
                    ]
                }
            ]
        }

    def test_lightrag_returns_list(self, sample_lightrag_data):
        """LightRAG export should return a list of chunks."""
        result = export_lightrag_json(sample_lightrag_data)
        data = json.loads(result)
        assert isinstance(data, list)

    def test_lightrag_chunk_has_content(self, sample_lightrag_data):
        """Each LightRAG chunk should have content field."""
        result = export_lightrag_json(sample_lightrag_data)
        data = json.loads(result)
        for chunk in data:
            assert 'content' in chunk
            assert len(chunk['content']) > 0

    def test_lightrag_chunk_has_metadata(self, sample_lightrag_data):
        """Each LightRAG chunk should have metadata."""
        result = export_lightrag_json(sample_lightrag_data)
        data = json.loads(result)
        for chunk in data:
            assert 'metadata' in chunk
            assert 'source' in chunk['metadata']

    def test_lightrag_combines_group_paragraphs(self, sample_lightrag_data):
        """LightRAG should combine paragraphs in a group."""
        result = export_lightrag_json(sample_lightrag_data)
        data = json.loads(result)
        # One group = one chunk
        assert len(data) == 1
        # Content should include all paragraphs
        assert 'First paragraph' in data[0]['content']
        assert 'Second paragraph' in data[0]['content']
        assert 'Third paragraph' in data[0]['content']

    def test_lightrag_metadata_includes_book_info(self, sample_lightrag_data):
        """LightRAG metadata should include book info."""
        result = export_lightrag_json(sample_lightrag_data)
        data = json.loads(result)
        metadata = data[0]['metadata']
        assert metadata['source'] == 'the-way-of-peace'
        assert metadata['title'] == 'The Way of Peace'
        assert metadata['author'] == 'Maulana Wahiduddin Khan'

    def test_lightrag_metadata_includes_chunk_info(self, sample_lightrag_data):
        """LightRAG metadata should include chunk position info."""
        result = export_lightrag_json(sample_lightrag_data)
        data = json.loads(result)
        metadata = data[0]['metadata']
        assert 'chunk_index' in metadata
        assert 'token_count' in metadata

    def test_lightrag_multiple_groups(self):
        """LightRAG should create one chunk per group."""
        data = {
            'title': 'Test',
            'slug': 'test',
            'paragraphs': [
                {'id': i, 'text': f'Para {i}', 'order_index': i, 'token_count': 300, 'group_id': i // 2}
                for i in range(4)
            ],
            'groups': [
                {'order_index': 0, 'token_count': 600, 'paragraphs': [{'id': 0, 'text': 'Para 0'}, {'id': 1, 'text': 'Para 1'}]},
                {'order_index': 1, 'token_count': 600, 'paragraphs': [{'id': 2, 'text': 'Para 2'}, {'id': 3, 'text': 'Para 3'}]},
            ]
        }
        result = export_lightrag_json(data)
        parsed = json.loads(result)
        assert len(parsed) == 2

    def test_lightrag_includes_paragraph_ids(self, sample_lightrag_data):
        """LightRAG metadata should include paragraph IDs for traceability."""
        result = export_lightrag_json(sample_lightrag_data)
        data = json.loads(result)
        metadata = data[0]['metadata']
        assert 'paragraph_ids' in metadata
        assert metadata['paragraph_ids'] == [1, 2, 3]


class TestValidateExportData:
    """Test export data validation."""

    @pytest.mark.parametrize("data,is_valid", [
        # Valid minimal data
        ({'title': 'Test', 'paragraphs': [], 'groups': []}, True),
        # Missing title
        ({'paragraphs': [], 'groups': []}, False),
        # Missing paragraphs
        ({'title': 'Test', 'groups': []}, False),
        # Missing groups
        ({'title': 'Test', 'paragraphs': []}, False),
        # Empty dict
        ({}, False),
        # None
        (None, False),
    ])
    def test_validation(self, data, is_valid):
        """Data validation should correctly identify valid/invalid data."""
        result = validate_export_data(data)
        assert result == is_valid

    def test_validation_with_invalid_paragraph(self):
        """Paragraphs missing required fields should fail validation."""
        data = {
            'title': 'Test',
            'paragraphs': [{'text': 'No ID'}],  # Missing id
            'groups': []
        }
        result = validate_export_data(data)
        assert result is False

    def test_validation_with_valid_paragraph(self):
        """Paragraphs with required fields should pass."""
        data = {
            'title': 'Test',
            'paragraphs': [{'id': 1, 'text': 'Content', 'order_index': 0}],
            'groups': []
        }
        result = validate_export_data(data)
        assert result is True


class TestEdgeCases:
    """Test edge cases."""

    def test_empty_paragraphs_book_json(self):
        """Book with no paragraphs should export."""
        data = {'title': 'Empty Book', 'paragraphs': [], 'groups': []}
        result = export_book_json(data)
        parsed = json.loads(result)
        assert parsed['paragraphs'] == []

    def test_empty_paragraphs_lightrag(self):
        """Book with no paragraphs should export empty list."""
        data = {'title': 'Empty Book', 'slug': 'empty', 'paragraphs': [], 'groups': []}
        result = export_lightrag_json(data)
        parsed = json.loads(result)
        assert parsed == []

    def test_unicode_content(self):
        """Unicode content should be preserved."""
        data = {
            'title': 'القرآن',
            'author': 'مولانا',
            'slug': 'quran',
            'paragraphs': [
                {'id': 1, 'text': 'بسم الله الرحمن الرحيم', 'order_index': 0, 'token_count': 100, 'group_id': 0}
            ],
            'groups': [
                {'order_index': 0, 'token_count': 100, 'paragraphs': [
                    {'id': 1, 'text': 'بسم الله الرحمن الرحيم'}
                ]}
            ]
        }
        result = export_book_json(data)
        parsed = json.loads(result)
        assert 'بسم الله' in parsed['paragraphs'][0]['text']

    def test_special_characters_in_text(self):
        """Special characters should be properly escaped."""
        data = {
            'title': 'Test "Book"',
            'slug': 'test',
            'paragraphs': [
                {'id': 1, 'text': 'Quote: "Hello" and \'World\'', 'order_index': 0, 'token_count': 50, 'group_id': 0}
            ],
            'groups': [
                {'order_index': 0, 'token_count': 50, 'paragraphs': [
                    {'id': 1, 'text': 'Quote: "Hello"'}
                ]}
            ]
        }
        result = export_book_json(data)
        # Should be valid JSON
        parsed = json.loads(result)
        assert '"Hello"' in parsed['paragraphs'][0]['text']

    def test_large_paragraph_count(self):
        """Export should handle many paragraphs."""
        paragraphs = [
            {'id': i, 'text': f'Paragraph {i}', 'order_index': i, 'token_count': 50, 'group_id': i // 10}
            for i in range(100)
        ]
        groups = [
            {'order_index': g, 'token_count': 500, 'paragraphs': [
                {'id': i, 'text': f'Paragraph {i}'} for i in range(g*10, (g+1)*10)
            ]}
            for g in range(10)
        ]
        data = {'title': 'Large Book', 'slug': 'large', 'paragraphs': paragraphs, 'groups': groups}
        result = export_book_json(data)
        parsed = json.loads(result)
        assert len(parsed['paragraphs']) == 100

    def test_newlines_in_text(self):
        """Newlines in text should be preserved."""
        data = {
            'title': 'Test',
            'slug': 'test',
            'paragraphs': [
                {'id': 1, 'text': 'Line 1\nLine 2\nLine 3', 'order_index': 0, 'token_count': 50, 'group_id': 0}
            ],
            'groups': [
                {'order_index': 0, 'token_count': 50, 'paragraphs': [
                    {'id': 1, 'text': 'Line 1\nLine 2\nLine 3'}
                ]}
            ]
        }
        result = export_book_json(data)
        parsed = json.loads(result)
        assert '\n' in parsed['paragraphs'][0]['text']

