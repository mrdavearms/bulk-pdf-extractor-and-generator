#!/usr/bin/env python3
"""
Simple Markdown-to-tkinter renderer for VCAA PDF Generator v2.0

Parses a subset of markdown and renders it into a tkinter Text widget
using the tag system.  Supports headings, bold, bullet lists, and
clickable hyperlinks.

Supported syntax
----------------
  # Heading 1
  ## Heading 2
  ### Heading 3
  **bold text**
  * bullet item   (or - bullet item)
  [link text](url)
  blank line = paragraph break
"""

import re
import tkinter as tk
import webbrowser

from vcaa_theme import COLORS, SYSTEM_FONTS, font

# Regex that matches **bold** spans and [text](url) links within a line.
_INLINE_RE = re.compile(
    r'(\*\*(.+?)\*\*)'                   # bold
    r'|'
    r'(\[([^\]]+)\]\(([^)]+)\))'          # [text](url)
)


class MarkdownRenderer:
    """Renders a subset of markdown into a tkinter Text widget."""

    def __init__(self, text_widget: tk.Text):
        self.text = text_widget
        self._link_count = 0
        self._setup_tags()

    # ── tag configuration ──────────────────────────────────────

    def _setup_tags(self):
        ff = SYSTEM_FONTS['family']
        C = COLORS

        self.text.tag_configure('h1',
            font=(ff, 22, 'bold'),
            foreground=C['accent'],
            spacing1=20,
            spacing3=8,
        )
        self.text.tag_configure('h2',
            font=(ff, 16, 'bold'),
            foreground=C['text_primary'],
            spacing1=18,
            spacing3=6,
        )
        self.text.tag_configure('h3',
            font=(ff, 13, 'bold'),
            foreground=C['text_primary'],
            spacing1=14,
            spacing3=4,
        )
        self.text.tag_configure('body',
            font=(ff, 11),
            foreground=C['text_primary'],
            spacing1=2,
            spacing3=2,
            lmargin1=12,
            lmargin2=12,
        )
        self.text.tag_configure('bold',
            font=(ff, 11, 'bold'),
        )
        self.text.tag_configure('bullet',
            font=(ff, 11),
            foreground=C['text_primary'],
            lmargin1=28,
            lmargin2=44,
            spacing1=2,
            spacing3=2,
        )
        self.text.tag_configure('link_base',
            font=(ff, 11),
            foreground=C['info'],
            underline=True,
        )
        self.text.tag_configure('spacer',
            font=(ff, 4),
            spacing1=0,
            spacing3=0,
        )
        self.text.tag_configure('hr',
            font=(ff, 1),
            foreground=C['border_subtle'],
            spacing1=12,
            spacing3=12,
        )

    # ── public API ─────────────────────────────────────────────

    def render(self, markdown_content: str):
        """Parse *markdown_content* and insert formatted text."""
        self.text.config(state=tk.NORMAL)
        self.text.delete('1.0', tk.END)

        lines = markdown_content.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]

            if line.strip() == '':
                # Blank line -> small vertical spacer
                self.text.insert(tk.END, '\n', 'spacer')
            elif line.strip() in ('---', '***', '___'):
                # Horizontal rule
                self.text.insert(tk.END, '\u2500' * 60 + '\n', 'hr')
            elif line.startswith('### '):
                self._insert_inline(line[4:], 'h3')
                self.text.insert(tk.END, '\n')
            elif line.startswith('## '):
                self._insert_inline(line[3:], 'h2')
                self.text.insert(tk.END, '\n')
            elif line.startswith('# '):
                self._insert_inline(line[2:], 'h1')
                self.text.insert(tk.END, '\n')
            elif line.lstrip().startswith(('* ', '- ')):
                indent = line[:len(line) - len(line.lstrip())]
                stripped = line.lstrip()[2:]
                bullet_char = '  \u2022  '
                self.text.insert(tk.END, bullet_char, 'bullet')
                self._insert_inline(stripped, 'bullet')
                self.text.insert(tk.END, '\n')
            else:
                self._insert_inline(line, 'body')
                self.text.insert(tk.END, '\n')

            i += 1

        self.text.config(state=tk.DISABLED)

    # ── inline parsing ─────────────────────────────────────────

    def _insert_inline(self, text: str, base_tag: str):
        """Parse **bold** and [link](url) within *text*."""
        last_end = 0

        for m in _INLINE_RE.finditer(text):
            # Insert any plain text before this match
            if m.start() > last_end:
                self.text.insert(tk.END, text[last_end:m.start()], base_tag)

            if m.group(2) is not None:
                # Bold match
                self.text.insert(tk.END, m.group(2), (base_tag, 'bold'))
            elif m.group(4) is not None:
                # Link match
                link_text = m.group(4)
                url = m.group(5)
                link_tag = self._create_link_tag(url)
                self.text.insert(tk.END, link_text, (base_tag, 'link_base', link_tag))

            last_end = m.end()

        # Insert remaining plain text
        if last_end < len(text):
            self.text.insert(tk.END, text[last_end:], base_tag)

    # ── hyperlink handling ─────────────────────────────────────

    def _create_link_tag(self, url: str) -> str:
        """Create a unique tag for *url* and bind click + cursor events."""
        self._link_count += 1
        tag = f'link_{self._link_count}'

        # Capture url in closure
        self.text.tag_bind(tag, '<Button-1>', lambda e, u=url: webbrowser.open(u))
        self.text.tag_bind(tag, '<Enter>', self._on_link_enter)
        self.text.tag_bind(tag, '<Leave>', self._on_link_leave)
        return tag

    def _on_link_enter(self, event):
        self.text.config(cursor='hand2')

    def _on_link_leave(self, event):
        self.text.config(cursor='arrow')


# ── convenience function ───────────────────────────────────────

def load_and_render(text_widget: tk.Text, md_file_path: str):
    """Load a markdown file and render it into *text_widget*."""
    renderer = MarkdownRenderer(text_widget)
    with open(md_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    renderer.render(content)
