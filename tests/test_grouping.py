"""Tests for paragraph grouping service."""
import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.grouping import (
    count_tokens,
    create_groups,
    assign_paragraphs_to_groups,
    calculate_group_token_count
)


class TestCountTokens:
    """Test token counting."""

    @pytest.mark.parametrize("text,expected_range", [
        # Simple cases
        ("hello world", (2, 3)),
        ("one two three four five", (5, 7)),
        ("", (0, 1)),
        ("   ", (0, 1)),

        # Longer texts
        ("The quick brown fox jumps over the lazy dog", (9, 12)),
        ("This is a test sentence with multiple words.", (8, 12)),
    ])
    def test_token_count_range(self, text, expected_range):
        """Token counts should be within expected range."""
        count = count_tokens(text)
        assert expected_range[0] <= count <= expected_range[1]

    def test_punctuation_handling(self):
        """Punctuation should be handled reasonably."""
        count1 = count_tokens("Hello, world!")
        count2 = count_tokens("Hello world")
        # Punctuation may add tokens but shouldn't double count
        assert count1 >= count2

    def test_unicode_handling(self):
        """Unicode text should be handled."""
        count = count_tokens("Qur'ān reference: البقرة")
        assert count > 0


class TestCreateGroups:
    """Test group creation logic."""

    @pytest.mark.parametrize("token_counts,min_tokens,max_tokens,expected_groups", [
        # All fit in one group
        ([100, 100, 100], 512, 800, 1),
        ([200, 200], 512, 800, 1),

        # Need to split
        ([400, 400, 400], 512, 800, 2),
        ([300, 300, 300, 300], 512, 800, 2),

        # Edge: exactly at boundary
        ([512], 512, 800, 1),
        ([800], 512, 800, 1),

        # Single large paragraph over max
        ([900], 512, 800, 1),  # Single para stays alone

        # Empty list
        ([], 512, 800, 0),

        # Many small paragraphs
        ([50] * 20, 512, 800, 2),  # 1000 tokens total, ~2 groups

        # Mix of sizes
        ([100, 500, 100, 600, 100], 512, 800, 3),
    ])
    def test_group_count(self, token_counts, min_tokens, max_tokens, expected_groups):
        """Group count should match expected."""
        paragraphs = [
            {'id': i, 'text': 'x' * tc, 'token_count': tc}
            for i, tc in enumerate(token_counts)
        ]
        groups = create_groups(paragraphs, min_tokens, max_tokens)
        assert len(groups) == expected_groups

    def test_groups_respect_max_tokens(self):
        """No group should exceed max tokens (unless single large para)."""
        paragraphs = [
            {'id': i, 'text': 'word ' * 100, 'token_count': 100}
            for i in range(10)
        ]
        groups = create_groups(paragraphs, min_tokens=512, max_tokens=800)

        for group in groups:
            total = sum(p['token_count'] for p in group['paragraphs'])
            # Either under max or single paragraph
            assert total <= 800 or len(group['paragraphs']) == 1

    def test_groups_aim_for_min_tokens(self):
        """Groups should generally reach min token threshold."""
        paragraphs = [
            {'id': i, 'text': 'word ' * 200, 'token_count': 200}
            for i in range(10)
        ]
        groups = create_groups(paragraphs, min_tokens=512, max_tokens=800)

        # Most groups should reach min (except possibly last one)
        for group in groups[:-1]:
            total = sum(p['token_count'] for p in group['paragraphs'])
            assert total >= 512

    def test_paragraph_order_preserved(self):
        """Paragraph order should be preserved within groups."""
        paragraphs = [
            {'id': i, 'text': f'para {i}', 'token_count': 100}
            for i in range(10)
        ]
        groups = create_groups(paragraphs, min_tokens=300, max_tokens=500)

        # Check order within each group
        for group in groups:
            ids = [p['id'] for p in group['paragraphs']]
            assert ids == sorted(ids)

    def test_all_paragraphs_assigned(self):
        """All paragraphs should be assigned to a group."""
        paragraphs = [
            {'id': i, 'text': f'para {i}', 'token_count': 100}
            for i in range(15)
        ]
        groups = create_groups(paragraphs, min_tokens=512, max_tokens=800)

        assigned_ids = set()
        for group in groups:
            for para in group['paragraphs']:
                assigned_ids.add(para['id'])

        expected_ids = set(range(15))
        assert assigned_ids == expected_ids


class TestAssignParagraphsToGroups:
    """Test paragraph assignment to existing groups."""

    def test_assignment_updates_group_id(self):
        """Paragraphs should be assigned correct group IDs."""
        paragraphs = [
            {'id': 1, 'text': 'first', 'token_count': 300},
            {'id': 2, 'text': 'second', 'token_count': 300},
            {'id': 3, 'text': 'third', 'token_count': 300},
        ]
        groups = create_groups(paragraphs, min_tokens=512, max_tokens=800)
        result = assign_paragraphs_to_groups(paragraphs, groups)

        for para in result:
            assert 'group_id' in para
            assert para['group_id'] is not None

    def test_same_group_for_adjacent_small_paragraphs(self):
        """Adjacent small paragraphs should be in same group."""
        paragraphs = [
            {'id': 1, 'text': 'first', 'token_count': 100},
            {'id': 2, 'text': 'second', 'token_count': 100},
        ]
        groups = create_groups(paragraphs, min_tokens=512, max_tokens=800)
        result = assign_paragraphs_to_groups(paragraphs, groups)

        # Both should be in same group since total < min
        assert result[0]['group_id'] == result[1]['group_id']


class TestCalculateGroupTokenCount:
    """Test group token count calculation."""

    def test_sum_of_paragraph_tokens(self):
        """Group token count should sum paragraph tokens."""
        paragraphs = [
            {'id': 1, 'token_count': 100},
            {'id': 2, 'token_count': 200},
            {'id': 3, 'token_count': 150},
        ]
        total = calculate_group_token_count(paragraphs)
        assert total == 450

    def test_empty_list(self):
        """Empty list should return 0."""
        total = calculate_group_token_count([])
        assert total == 0


class TestEdgeCases:
    """Test edge cases."""

    def test_single_paragraph(self):
        """Single paragraph should form one group."""
        paragraphs = [{'id': 1, 'text': 'only one', 'token_count': 100}]
        groups = create_groups(paragraphs, min_tokens=512, max_tokens=800)
        assert len(groups) == 1

    def test_very_large_paragraph(self):
        """Very large paragraph should be in its own group."""
        paragraphs = [
            {'id': 1, 'text': 'small', 'token_count': 100},
            {'id': 2, 'text': 'huge', 'token_count': 1500},
            {'id': 3, 'text': 'small', 'token_count': 100},
        ]
        groups = create_groups(paragraphs, min_tokens=512, max_tokens=800)

        # Large paragraph should be alone
        large_group = None
        for group in groups:
            for para in group['paragraphs']:
                if para['id'] == 2:
                    large_group = group
                    break

        assert large_group is not None
        assert len(large_group['paragraphs']) == 1

    def test_paragraphs_without_token_count(self):
        """Paragraphs without token_count should have it calculated."""
        paragraphs = [
            {'id': 1, 'text': 'hello world test'},
            {'id': 2, 'text': 'another paragraph here'},
        ]
        groups = create_groups(paragraphs, min_tokens=10, max_tokens=50)
        assert len(groups) >= 1

    def test_group_has_metadata(self):
        """Groups should have necessary metadata."""
        paragraphs = [
            {'id': i, 'text': f'para {i}', 'token_count': 200}
            for i in range(5)
        ]
        groups = create_groups(paragraphs, min_tokens=512, max_tokens=800)

        for i, group in enumerate(groups):
            assert 'order_index' in group
            assert 'token_count' in group
            assert 'paragraphs' in group
            assert group['order_index'] == i
