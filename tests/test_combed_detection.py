"""Combed-field detection tests (item 2).

Real comb character-boxes share a horizontal baseline. Genuinely separate
sequential fields (Address_1 / Address_2 stacked on different lines) must NOT
be merged into one character-by-character comb — doing so truncates each value
to a single character (silent data loss).

These tests drive PDFAnalyzer._detect_combed_fields directly with synthetic
widgets, so no real PDF is required.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pdf_analyzer import PDFAnalyzer


class _FakeWidget:
    """Minimal stand-in for a fitz.Widget — only the attributes the
    analyzer reads. Deliberately has no `xref` / `text_maxlen`, so the
    single-field MaxLen probe degrades gracefully to None."""

    def __init__(self, name, rect, ftype='Text', value=''):
        self.field_name = name
        self.rect = rect  # (x0, y0, x1, y1) in PDF points
        self.field_type_string = ftype
        self.field_value = value


def _analyzer():
    a = PDFAnalyzer.__new__(PDFAnalyzer)  # bypass __enter__/fitz.open
    a.doc = None
    return a


def _widgets(specs):
    """specs: list of (name, rect) -> analyzer records on page 1.

    _detect_combed_fields consumes the merged-record shape produced by
    _merge_widgets_by_name; these tests build it directly. All specs are plain
    Text fields, so on_states/options are empty."""
    return [
        {'name': n, 'widget': _FakeWidget(n, r), 'page_num': 1,
         'field_type': 'Text', 'on_states': [], 'options': []}
        for n, r in specs
    ]


class TestCombedRowDetection(unittest.TestCase):

    def test_same_row_underscore_sequence_is_combed(self):
        """Code_0..Code_4 on one baseline → a single comb field of length 5."""
        specs = [(f'Code_{i}', (100 + i * 12, 200, 110 + i * 12, 214))
                 for i in range(5)]
        fields = _analyzer()._detect_combed_fields(_widgets(specs))
        self.assertEqual(len(fields), 1)
        self.assertTrue(fields[0].is_combed)
        self.assertEqual(fields[0].length, 5)
        self.assertEqual(len(fields[0].combed_fields), 5)

    def test_stacked_sequential_fields_are_not_combed(self):
        """Address_1 / Address_2 on different lines stay as separate fields."""
        specs = [
            ('Address_1', (100, 200, 400, 214)),
            ('Address_2', (100, 230, 400, 244)),  # next line down
        ]
        fields = _analyzer()._detect_combed_fields(_widgets(specs))
        self.assertEqual(len(fields), 2)
        self.assertFalse(any(f.is_combed for f in fields))
        self.assertEqual({f.field_name for f in fields},
                         {'Address_1', 'Address_2'})

    def test_bracketed_pattern_combs_even_when_stacked(self):
        """Field[N] is the canonical comb naming — always merged, no geometry
        check (some forms lay comb boxes across rows)."""
        specs = [
            ('Box[0]', (100, 200, 114, 214)),
            ('Box[1]', (100, 230, 114, 244)),
            ('Box[2]', (100, 260, 114, 274)),
        ]
        fields = _analyzer()._detect_combed_fields(_widgets(specs))
        self.assertEqual(len(fields), 1)
        self.assertTrue(fields[0].is_combed)
        self.assertEqual(fields[0].length, 3)

    def test_minor_baseline_jitter_still_combs(self):
        """A few points of y-jitter on one row must not break comb detection."""
        specs = [
            ('Num_0', (100, 200, 112, 214)),
            ('Num_1', (112, 202, 124, 216)),  # +2pt jitter
            ('Num_2', (124, 199, 136, 213)),  # -1pt jitter
        ]
        fields = _analyzer()._detect_combed_fields(_widgets(specs))
        self.assertEqual(len(fields), 1)
        self.assertTrue(fields[0].is_combed)


if __name__ == '__main__':
    unittest.main()
