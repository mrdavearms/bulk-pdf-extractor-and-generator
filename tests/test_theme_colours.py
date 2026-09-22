"""Colour regression guards — no Tk instance needed (CI is headless).

1. ttkbootstrap replaces the fg/bg of every plain tk widget created without
   autostyle=False, silently discarding the colours the code asked for.
2. Text colours in COLORS must meet WCAG AA (4.5:1) on the surfaces they
   are drawn on.
"""
import ast
import inspect
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import theme
from theme import COLORS

REPO = Path(__file__).parent.parent
PATCHED_TK_WIDGETS = {'Label', 'Frame', 'Text', 'Canvas'}
COLOUR_KWARGS = {'fg', 'bg', 'foreground', 'background'}


def _contrast(a: str, b: str) -> float:
    def lum(h):
        chans = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in chans]
        return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


class TestAutostyleOff(unittest.TestCase):

    def test_coloured_tk_widgets_opt_out_of_autostyle(self):
        """Every tk.Label/Frame/Text/Canvas passing fg= or bg= also passes autostyle=False."""
        for filename in ('pdf_generator.py', 'markdown_renderer.py'):
            tree = ast.parse((REPO / filename).read_text(encoding='utf-8'))
            offenders = []
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Attribute)
                        and isinstance(node.func.value, ast.Name)
                        and node.func.value.id == 'tk'
                        and node.func.attr in PATCHED_TK_WIDGETS):
                    continue
                kwargs = {k.arg for k in node.keywords}
                if kwargs & COLOUR_KWARGS and 'autostyle' not in kwargs:
                    offenders.append(f'{filename}:{node.lineno} tk.{node.func.attr}')
            self.assertEqual(offenders, [],
                             'ttkbootstrap will overwrite these colours; add autostyle=False')


class TestTextContrast(unittest.TestCase):

    def assertReadable(self, fg_key, bg_key):
        ratio = _contrast(COLORS[fg_key], COLORS[bg_key])
        self.assertGreaterEqual(
            ratio, 4.5, f'{fg_key} {COLORS[fg_key]} on {bg_key} {COLORS[bg_key]} is {ratio:.2f}:1')

    def test_text_colours_on_page_and_card(self):
        for fg in ('text_primary', 'text_secondary', 'text_tertiary', 'accent',
                   'success', 'warning', 'error', 'info'):
            for bg in ('bg_surface', 'bg_base'):
                with self.subTest(fg=fg, bg=bg):
                    self.assertReadable(fg, bg)

    def test_semantic_text_on_tinted_banners(self):
        self.assertReadable('success', 'success_bg')
        self.assertReadable('warning', 'warning_bg')
        self.assertReadable('error', 'error_bg')
        self.assertReadable('info', 'accent_subtle')

    def test_selected_treeview_row_is_readable(self):
        """litera's default selected row (white on #adb5bd) is 2.1:1 — theme must override it."""
        src = inspect.getsource(theme.apply_dark_theme)
        self.assertIn("style.map('Treeview'", src)
        self.assertIn("('selected', C['tree_selected'])", src)
        self.assertReadable('text_primary', 'tree_selected')

    def test_page_frames_use_page_colour(self):
        """litera paints ttk.Frame white; the page must be bg_base so cards stand out."""
        src = inspect.getsource(theme.apply_dark_theme)
        self.assertIn("style.configure('TFrame', background=C['bg_base'])", src)


if __name__ == '__main__':
    unittest.main()
