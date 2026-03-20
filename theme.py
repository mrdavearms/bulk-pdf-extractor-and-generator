#!/usr/bin/env python3
"""
Bulk PDF Generator v2.0 -- Theme System (ttkbootstrap edition)

Provides colour constants, font helpers, and custom style definitions
on top of the ttkbootstrap 'litera' base theme.  Base widget styles
(TButton, TEntry, TCombobox, TNotebook, TScrollbar, TProgressbar) are
owned by ttkbootstrap — only app-specific overrides are defined here.
"""

import platform
import tkinter as tk
from tkinter import ttk  # ttk.Treeview type hints in helper functions
import ttkbootstrap as tbs


# ============================================================
# COLOR PALETTE
# These remain as explicit constants so the rest of the codebase
# can reference them for tk.* legacy widgets (Canvas bg, dialog bg, etc.)
# ============================================================

COLORS = {
    # --- Backgrounds ---
    'bg_base':        '#f2f2f4',
    'bg_surface':     '#ffffff',
    'bg_elevated':    '#ffffff',
    'bg_input':       '#f7f7f9',
    'bg_hover':       '#e9e9ec',

    # --- Text ---
    'text_primary':   '#1d1d1f',
    'text_secondary': '#6e6e73',
    'text_tertiary':  '#aeaeb2',
    'text_inverse':   '#ffffff',

    # --- Accent / Brand ---
    'accent':         '#4c8bf5',
    'accent_hover':   '#3a7ae0',
    'accent_pressed': '#2d6ad4',
    'accent_subtle':  '#e8f0fe',

    # --- Borders ---
    'border_subtle':  '#e0e0e3',
    'border_default': '#c7c7cc',
    'border_focus':   '#4c8bf5',

    # --- Semantic ---
    'success':        '#34a853',
    'success_bg':     '#e6f4ea',
    'warning':        '#ea8600',
    'warning_bg':     '#fef7e0',
    'error':          '#d93025',
    'error_bg':       '#fce8e6',
    'info':           '#4c8bf5',

    # --- Tab bar (used for custom tab rendering if needed) ---
    'tab_inactive_bg':   '#e8e8eb',
    'tab_inactive_text': '#6e6e73',
    'tab_active_bg':     '#ffffff',
    'tab_active_text':   '#1d1d1f',
    'tab_hover_bg':      '#dddde0',

    # --- Treeview ---
    'tree_row_even':  '#ffffff',
    'tree_row_odd':   '#f7f7f9',
    'tree_selected':  '#e8f0fe',
    'tree_header_bg': '#f2f2f4',
    'tree_header_fg': '#6e6e73',

    # --- Scrollbar ---
    'scroll_track':   '#f2f2f4',
    'scroll_thumb':   '#c7c7cc',
    'scroll_hover':   '#a8a8ad',

    # --- Progress bar ---
    'progress_track': '#e0e0e3',
    'progress_fill':  '#4c8bf5',

    # --- Canvas / Preview ---
    'canvas_bg':      '#f7f7f9',
    'canvas_border':  '#e0e0e3',
}


# ============================================================
# TYPOGRAPHY
# ============================================================

def get_system_fonts() -> dict:
    system = platform.system()
    if system == 'Windows':
        return {'family': 'Segoe UI', 'mono': 'Consolas'}
    elif system == 'Darwin':
        return {'family': 'Helvetica Neue', 'mono': 'Menlo'}
    else:
        return {'family': 'DejaVu Sans', 'mono': 'DejaVu Sans Mono'}


SYSTEM_FONTS = get_system_fonts()


_VALID_WEIGHTS = {'', 'bold', 'italic', 'bold italic'}


def font(size: int, weight: str = '') -> tuple:
    if weight not in _VALID_WEIGHTS:
        raise ValueError(
            f"font() weight must be one of {sorted(_VALID_WEIGHTS)!r}, got {weight!r}"
        )
    if weight:
        return (SYSTEM_FONTS['family'], size, weight)
    return (SYSTEM_FONTS['family'], size)


def mono_font(size: int) -> tuple:
    return (SYSTEM_FONTS['mono'], size)


# ============================================================
# SPACING
# ============================================================

SPACING = {
    'page_padding':  20,
    'section_gap':   16,
    'element_gap':   10,
    'inner_padding': 16,
    'button_gap':    10,
    'input_gap':      8,
}


# ============================================================
# THEME APPLICATION
# ============================================================

def apply_dark_theme(root: tk.Tk):
    """Apply the ttkbootstrap 'litera' theme plus app-specific custom styles.

    Name kept as apply_dark_theme for backward compatibility.
    """
    # DPI scaling is handled by main() before Tk() creation — not here.
    # (Must be called before Tk window creation for correct Windows scaling.)

    # Initialise ttkbootstrap style on the existing root window.
    # 'litera' is a clean, professional light theme whose primary blue
    # (#4582ec) closely matches our brand accent (#4c8bf5).
    style = tbs.Style(theme='litera')

    C = COLORS
    ff = SYSTEM_FONTS['family']

    # ── Custom surface/card frames ──────────────────────────────
    # ttkbootstrap owns TFrame; we add named variants for layered surfaces.
    style.configure('Card.TFrame', background=C['bg_surface'])
    style.configure('Elevated.TFrame', background=C['bg_elevated'])

    # ── Custom label typography variants ───────────────────────
    # ttkbootstrap owns TLabel base; we add semantic variants.
    style.configure('Title.TLabel',
        background=C['bg_base'],
        foreground=C['text_primary'],
        font=(ff, 22, 'bold'),
    )
    style.configure('Subtitle.TLabel',
        background=C['bg_base'],
        foreground=C['text_secondary'],
        font=(ff, 11),
    )
    style.configure('SectionHeader.TLabel',
        background=C['bg_surface'],
        foreground=C['text_primary'],
        font=(ff, 13, 'bold'),
    )
    style.configure('Secondary.TLabel',
        background=C['bg_base'],
        foreground=C['text_secondary'],
        font=(ff, 10),
    )
    style.configure('Success.TLabel',
        background=C['bg_base'],
        foreground=C['success'],
        font=(ff, 10),
    )
    style.configure('Warning.TLabel',
        background=C['bg_base'],
        foreground=C['warning'],
        font=(ff, 10),
    )
    style.configure('Muted.TLabel',
        background=C['bg_base'],
        foreground=C['text_tertiary'],
        font=(ff, 10),
    )
    style.configure('Surface.TLabel',
        background=C['bg_surface'],
        foreground=C['text_primary'],
        font=(ff, 11),
    )
    style.configure('Surface.Secondary.TLabel',
        background=C['bg_surface'],
        foreground=C['text_secondary'],
        font=(ff, 10),
    )
    style.configure('Surface.Success.TLabel',
        background=C['bg_surface'],
        foreground=C['success'],
        font=(ff, 10),
    )
    style.configure('SectionTitle.TLabel',
        background=C['bg_base'],
        foreground=C['text_primary'],
        font=(ff, 13, 'bold'),
    )
    style.configure('SectionSubtitle.TLabel',
        background=C['bg_base'],
        foreground=C['text_secondary'],
        font=(ff, 10),
    )

    # ── Treeview ────────────────────────────────────────────────
    # ttkbootstrap styles the base Treeview; we tune row height and header.
    style.configure('Treeview',
        font=(ff, 11),
        rowheight=30,
    )
    style.configure('Treeview.Heading',
        background=C['tree_header_bg'],
        foreground=C['tree_header_fg'],
        font=(ff, 10, 'bold'),
        padding=(8, 8),
    )
    style.map('Treeview.Heading',
        background=[('active', C['bg_hover'])],
    )

    # ── TLabelframe (kept for compatibility) ────────────────────
    style.configure('TLabelframe',
        background=C['bg_surface'],
        borderwidth=1,
        relief='flat',
    )
    style.configure('TLabelframe.Label',
        background=C['bg_surface'],
        foreground=C['text_primary'],
        font=(ff, 12, 'bold'),
    )

    # ── TRadiobutton / TCheckbutton surface variants ────────────
    style.configure('Surface.TRadiobutton',
        background=C['bg_surface'],
    )
    style.map('Surface.TRadiobutton',
        background=[('active', C['bg_hover'])],
    )
    style.configure('Elevated.TRadiobutton',
        background=C['bg_elevated'],
    )
    style.map('Elevated.TRadiobutton',
        background=[('active', C['bg_hover'])],
    )

    # Root window background
    root.configure(bg=C['bg_base'])


# ============================================================
# TREEVIEW HELPERS
# ============================================================

def setup_treeview_tags(tree: ttk.Treeview):
    """Configure alternating row colours and status tags on a Treeview."""
    tree.tag_configure('odd', background=COLORS['tree_row_odd'])
    tree.tag_configure('even', background=COLORS['tree_row_even'])
    tree.tag_configure('hover', background=COLORS['bg_hover'])
    tree.tag_configure('warning_row',
        background=COLORS['warning_bg'],
        foreground='#9a5c00',
    )
    tree.tag_configure('success_row',
        background=COLORS['success_bg'],
        foreground='#1e7e34',
    )
    tree.tag_configure('combed',
        foreground=COLORS['accent'],
    )


def bind_treeview_hover(tree: ttk.Treeview):
    """Add hover highlighting to a Treeview widget."""
    hovered = {'item': None}

    def on_motion(event):
        item = tree.identify_row(event.y)
        if item != hovered['item']:
            if hovered['item']:
                tags = list(tree.item(hovered['item'], 'tags'))
                if 'hover' in tags:
                    tags.remove('hover')
                    tree.item(hovered['item'], tags=tags)
            if item:
                tags = list(tree.item(item, 'tags'))
                tags.append('hover')
                tree.item(item, tags=tags)
            hovered['item'] = item

    def on_leave(event):
        if hovered['item']:
            tags = list(tree.item(hovered['item'], 'tags'))
            if 'hover' in tags:
                tags.remove('hover')
                tree.item(hovered['item'], tags=tags)
            hovered['item'] = None

    tree.bind('<Motion>', on_motion)
    tree.bind('<Leave>', on_leave)
