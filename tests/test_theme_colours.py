"""Colour regression guards — no Tk instance needed (CI is headless).

1. Plain tk widgets must keep the colours the code gives them. ttkbootstrap 1.x
   repainted every one created without autostyle=False; 2.x leaves stock
   tkinter alone unless enable_global_api() is called or one of its own themed
   tk classes (ttk.Canvas, ttk.TkLabel, ...) is used, and stock tkinter
   rejects autostyle= outright (the v2.15-v2.17 start-up crash).
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
# ttkbootstrap 2's themed versions of the tk widgets. Each repaints itself
# with the theme, discarding the colours the code passes.
THEMED_TK_CLASSES = {'Tk', 'Toplevel', 'Menu', 'Text', 'Canvas', 'Listbox', 'TkFrame', 'TkLabel'}
GUI_FILES = ('pdf_generator.py', 'markdown_renderer.py', 'theme.py')


def _contrast(a: str, b: str) -> float:
    def lum(h):
        chans = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in chans]
        return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


class TestTkWidgetsKeepTheirColours(unittest.TestCase):

    def _calls(self):
        for filename in GUI_FILES:
            tree = ast.parse((REPO / filename).read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    yield filename, node

    def test_no_autostyle_keyword(self):
        """Stock tkinter widgets reject autostyle=; it crashed v2.15-v2.17 at start-up."""
        offenders = [f'{f}:{n.lineno}' for f, n in self._calls()
                     if any(k.arg == 'autostyle' for k in n.keywords)]
        self.assertEqual(offenders, [])

    def test_global_api_stays_off(self):
        """enable_global_api() would make ttkbootstrap repaint every plain tk widget."""
        offenders = [f'{f}:{n.lineno}' for f, n in self._calls()
                     if getattr(n.func, 'attr', getattr(n.func, 'id', None)) == 'enable_global_api']
        self.assertEqual(offenders, [])

    def test_tk_widgets_come_from_stock_tkinter(self):
        """ttk.<Canvas|Text|TkLabel|...> are ttkbootstrap's themed tk classes; use tk.<...>."""
        offenders = [f'{f}:{n.lineno} {n.func.value.id}.{n.func.attr}' for f, n in self._calls()
                     if isinstance(n.func, ast.Attribute)
                     and isinstance(n.func.value, ast.Name)
                     and n.func.value.id in ('ttk', 'tbs')
                     and n.func.attr in THEMED_TK_CLASSES]
        self.assertEqual(offenders, [])


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

    def test_solid_buttons_readable_in_every_state(self):
        """White button text must pass at rest, hover and press (litera fails all three)."""
        src = inspect.getsource(theme.apply_dark_theme)
        for style_name in ("'TButton'", "'primary.TButton'", "'success.TButton'"):
            self.assertIn(style_name, src)
        self.assertIn("tbs.Bootstyle.update_ttk_widget_style(None, name)", src)
        for key in ('accent', 'accent_hover', 'accent_pressed',
                    'success', 'success_hover', 'success_pressed'):
            with self.subTest(key=key):
                self.assertReadable('text_inverse', key)

    def test_outline_buttons_readable_in_every_state(self):
        """Accent text at rest, white on a darkened fill when hovered/pressed."""
        src = inspect.getsource(theme.apply_dark_theme)
        self.assertIn("name = 'primary.Outline.TButton'", src)
        self.assertIn("tbs.Bootstyle.update_ttk_widget_style(None, name)", src)
        self.assertIn("('pressed !disabled', C['text_inverse'])", src)
        self.assertIn("('hover !disabled', C['text_inverse'])", src)
        self.assertIn("('pressed !disabled', C['accent_pressed'])", src)
        self.assertIn("('hover !disabled', C['accent_hover'])", src)
        self.assertReadable('accent', 'bg_surface')
        for key in ('accent_hover', 'accent_pressed'):
            with self.subTest(key=key):
                self.assertReadable('text_inverse', key)

    def test_buttons_are_solid_primary_or_one_outline_style(self):
        """Two button kinds only: solid primary/success, or outline-primary."""
        tree = ast.parse((REPO / 'pdf_generator.py').read_text(encoding='utf-8'))
        styles = set()
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == 'Button'
                    and isinstance(node.func.value, ast.Name) and node.func.value.id == 'ttk'):
                kw = {k.arg: k.value for k in node.keywords}
                styles.add(kw['bootstyle'].value if 'bootstyle' in kw else None)
        self.assertLessEqual(styles, {'primary', 'success', 'outline-primary'},
                             'every ttk.Button needs an explicit, approved bootstyle')

    def test_disabled_notebook_tab_is_greyed(self):
        src = inspect.getsource(theme.apply_dark_theme)
        self.assertIn("foreground=[('disabled', C['text_disabled'])]", src)

    def test_page_frames_use_page_colour(self):
        """litera paints ttk.Frame white; the page must be bg_base so cards stand out."""
        src = inspect.getsource(theme.apply_dark_theme)
        self.assertIn("style.configure('TFrame', background=C['bg_base'])", src)


if __name__ == '__main__':
    unittest.main()
