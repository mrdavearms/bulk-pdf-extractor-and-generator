"""Tests for theme.font() — regression guard for font() call patterns."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from theme import font, SYSTEM_FONTS


class TestFont(unittest.TestCase):

    def setUp(self):
        self.family = SYSTEM_FONTS['family']

    def test_font_no_weight(self):
        """font(10) returns a 2-tuple (family, size)."""
        result = font(10)
        self.assertEqual(result, (self.family, 10))

    def test_font_bold(self):
        """font(10, 'bold') returns a 3-tuple (family, size, 'bold')."""
        result = font(10, 'bold')
        self.assertEqual(result, (self.family, 10, 'bold'))

    def test_font_italic(self):
        """font(10, 'italic') returns a 3-tuple (family, size, 'italic')."""
        result = font(10, 'italic')
        self.assertEqual(result, (self.family, 10, 'italic'))

    def test_font_bold_italic(self):
        """font(10, 'bold italic') returns a 3-tuple (family, size, 'bold italic')."""
        result = font(10, 'bold italic')
        self.assertEqual(result, (self.family, 10, 'bold italic'))

    def test_font_invalid_weight_raises(self):
        """font(10, 'Bold') raises ValueError — wrong case is rejected."""
        with self.assertRaises(ValueError):
            font(10, 'Bold')

    def test_font_invalid_kwarg_raises(self):
        """font(9, bold=True) raises TypeError — documents the v2.7 crash pattern."""
        with self.assertRaises(TypeError):
            font(9, bold=True)  # type: ignore


if __name__ == '__main__':
    unittest.main()
