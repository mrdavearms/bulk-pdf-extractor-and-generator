"""Tests for theme.font() — regression guard for font() call patterns."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import theme
from theme import font, SYSTEM_FONTS


class TestFont(unittest.TestCase):

    def setUp(self):
        self.family = SYSTEM_FONTS['family']
        self.size10 = round(10 * theme.FONT_SCALE)   # 13 on macOS with Tk 8.x

    def test_font_no_weight(self):
        """font(10) returns a 2-tuple (family, size)."""
        result = font(10)
        self.assertEqual(result, (self.family, self.size10))

    def test_font_bold(self):
        """font(10, 'bold') returns a 3-tuple (family, size, 'bold')."""
        result = font(10, 'bold')
        self.assertEqual(result, (self.family, self.size10, 'bold'))

    def test_font_italic(self):
        """font(10, 'italic') returns a 3-tuple (family, size, 'italic')."""
        result = font(10, 'italic')
        self.assertEqual(result, (self.family, self.size10, 'italic'))

    def test_font_bold_italic(self):
        """font(10, 'bold italic') returns a 3-tuple (family, size, 'bold italic')."""
        result = font(10, 'bold italic')
        self.assertEqual(result, (self.family, self.size10, 'bold italic'))

    def test_mac_tk8_scales_points_to_tk9_size(self):
        """Tk 8.x on macOS draws 1pt as 1px; scale so text matches Tk 9 and Windows."""
        import platform
        import tkinter as tk
        expected = 4 / 3 if platform.system() == 'Darwin' and tk.TkVersion < 9 else 1.0
        self.assertEqual(theme.FONT_SCALE, expected)
        from unittest.mock import patch
        with patch.object(theme, 'FONT_SCALE', 4 / 3):
            self.assertEqual(font(10), (self.family, 13))
            self.assertEqual(font(9, 'bold'), (self.family, 12, 'bold'))
            self.assertEqual(theme.mono_font(10), (SYSTEM_FONTS['mono'], 13))

    def test_no_font_sizes_bypass_font(self):
        """A literal (family, size) tuple would skip the macOS scale."""
        import ast
        repo = Path(__file__).parent.parent
        offenders = []
        for name in ('pdf_generator.py', 'theme.py', 'markdown_renderer.py'):
            for node in ast.walk(ast.parse((repo / name).read_text(encoding='utf-8'))):
                if (isinstance(node, ast.keyword) and node.arg == 'font'
                        and isinstance(node.value, ast.Tuple)):
                    offenders.append(f'{name}:{node.value.lineno}')
        self.assertEqual(offenders, [], 'use theme.font() for font sizes')

    def test_font_underline(self):
        self.assertEqual(font(10, 'underline'), (self.family, self.size10, 'underline'))

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
