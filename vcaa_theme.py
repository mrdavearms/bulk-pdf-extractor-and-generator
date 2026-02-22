#!/usr/bin/env python3
"""
Bulk PDF Generator v2.0 -- Modern Light Theme System
Centralized theme module for colors, fonts, spacing, and ttk style configuration.
"""

import platform
import tkinter as tk
from tkinter import ttk


# ============================================================
# COLOR PALETTE -- Modern Light Theme (inspired by Logitech Options+)
# ============================================================

COLORS = {
    # --- Backgrounds (layered surface hierarchy) ---
    'bg_base':        '#f2f2f4',   # Window background (warm light grey)
    'bg_surface':     '#ffffff',   # Cards, panels (pure white)
    'bg_elevated':    '#ffffff',   # Dialogs, dropdowns
    'bg_input':       '#f7f7f9',   # Entry fields, text areas
    'bg_hover':       '#e9e9ec',   # Hover state for interactive surfaces

    # --- Text ---
    'text_primary':   '#1d1d1f',   # Main body text (near-black)
    'text_secondary': '#6e6e73',   # Muted/secondary text
    'text_tertiary':  '#aeaeb2',   # Disabled text, placeholders
    'text_inverse':   '#ffffff',   # Text on accent-colored backgrounds

    # --- Accent / Brand ---
    'accent':         '#4c8bf5',   # Primary accent (buttons, active states)
    'accent_hover':   '#3a7ae0',   # Accent hover
    'accent_pressed': '#2d6ad4',   # Accent pressed
    'accent_subtle':  '#e8f0fe',   # Accent tint for backgrounds

    # --- Borders ---
    'border_subtle':  '#e0e0e3',   # Subtle borders (cards, dividers)
    'border_default': '#c7c7cc',   # Default borders (inputs)
    'border_focus':   '#4c8bf5',   # Focus ring (matches accent)

    # --- Semantic (status) ---
    'success':        '#34a853',   # Green for success/ready states
    'success_bg':     '#e6f4ea',   # Success background tint
    'warning':        '#ea8600',   # Amber for warnings
    'warning_bg':     '#fef7e0',   # Warning background tint
    'error':          '#d93025',   # Red for errors
    'error_bg':       '#fce8e6',   # Error background tint
    'info':           '#4c8bf5',   # Blue for informational

    # --- Tab bar ---
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
# TYPOGRAPHY -- Cross-Platform Font Detection
# ============================================================

def get_system_fonts() -> dict:
    """Return platform-appropriate font families."""
    system = platform.system()
    if system == 'Windows':
        return {'family': 'Segoe UI', 'mono': 'Consolas'}
    elif system == 'Darwin':
        return {'family': 'Helvetica Neue', 'mono': 'Menlo'}
    else:
        return {'family': 'DejaVu Sans', 'mono': 'DejaVu Sans Mono'}


SYSTEM_FONTS = get_system_fonts()


def font(size: int, weight: str = '') -> tuple:
    """Build a font tuple for the system font family."""
    if weight:
        return (SYSTEM_FONTS['family'], size, weight)
    return (SYSTEM_FONTS['family'], size)


def mono_font(size: int) -> tuple:
    """Build a monospaced font tuple."""
    return (SYSTEM_FONTS['mono'], size)


# ============================================================
# SPACING -- Consistent Layout Constants
# ============================================================

SPACING = {
    'page_padding':  20,   # Main content area padding
    'section_gap':   16,   # Gap between card sections
    'element_gap':   10,   # Gap between elements in a section
    'inner_padding': 16,   # Padding inside cards/frames
    'button_gap':    10,   # Gap between adjacent buttons
    'input_gap':      8,   # Gap between label and input
}


# ============================================================
# THEME APPLICATION -- Configure All ttk Widget Styles
# ============================================================

def apply_dark_theme(root: tk.Tk):
    """Apply the modern light theme to all ttk widgets.

    Name kept as apply_dark_theme for backward compatibility.
    """
    style = ttk.Style(root)
    style.theme_use('clam')  # Best base for customization

    C = COLORS
    ff = SYSTEM_FONTS['family']

    # --- TFrame ---
    style.configure('TFrame', background=C['bg_base'])
    style.configure('Card.TFrame', background=C['bg_surface'])
    style.configure('Elevated.TFrame', background=C['bg_elevated'])

    # --- TLabel ---
    style.configure('TLabel',
        background=C['bg_base'],
        foreground=C['text_primary'],
        font=(ff, 11),
    )
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
    # Variants for labels on card/surface backgrounds
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
    # Section title for card-style sections
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

    # --- TButton ---
    style.configure('TButton',
        background=C['bg_surface'],
        foreground=C['text_primary'],
        borderwidth=1,
        focuscolor=C['accent'],
        font=(ff, 11),
        padding=(18, 8),
    )
    style.map('TButton',
        background=[
            ('active', C['bg_hover']),
            ('pressed', C['border_default']),
            ('disabled', C['bg_base']),
        ],
        foreground=[
            ('disabled', C['text_tertiary']),
        ],
    )
    # Primary (accent) button
    style.configure('Accent.TButton',
        background=C['accent'],
        foreground='#ffffff',
        font=(ff, 11, 'bold'),
        padding=(24, 12),
        borderwidth=0,
    )
    # Large CTA button (e.g. Generate)
    style.configure('BigAccent.TButton',
        background=C['accent'],
        foreground='#ffffff',
        font=(ff, 12, 'bold'),
        padding=(32, 14),
        borderwidth=0,
    )
    style.map('BigAccent.TButton',
        background=[
            ('active', C['accent_hover']),
            ('pressed', C['accent_pressed']),
            ('disabled', '#c7c7cc'),
        ],
        foreground=[
            ('disabled', '#ffffff'),
        ],
    )
    style.map('Accent.TButton',
        background=[
            ('active', C['accent_hover']),
            ('pressed', C['accent_pressed']),
            ('disabled', '#c7c7cc'),
        ],
        foreground=[
            ('disabled', '#ffffff'),
        ],
    )

    # --- TEntry ---
    style.configure('TEntry',
        fieldbackground=C['bg_input'],
        foreground=C['text_primary'],
        insertcolor=C['text_primary'],
        borderwidth=1,
        padding=(8, 6),
    )
    style.map('TEntry',
        fieldbackground=[
            ('focus', '#ffffff'),
            ('disabled', C['bg_base']),
        ],
        bordercolor=[
            ('focus', C['border_focus']),
            ('!focus', C['border_default']),
        ],
    )
    # Variant for entries on elevated surfaces (dialogs)
    style.configure('Elevated.TEntry',
        fieldbackground=C['bg_input'],
    )
    style.map('Elevated.TEntry',
        fieldbackground=[
            ('focus', '#ffffff'),
            ('disabled', C['bg_base']),
        ],
        bordercolor=[
            ('focus', C['border_focus']),
            ('!focus', C['border_default']),
        ],
    )

    # --- TCombobox ---
    style.configure('TCombobox',
        fieldbackground=C['bg_input'],
        background=C['bg_surface'],
        foreground=C['text_primary'],
        arrowcolor=C['text_secondary'],
        borderwidth=1,
        padding=(8, 6),
    )
    style.map('TCombobox',
        fieldbackground=[
            ('readonly', C['bg_input']),
            ('disabled', C['bg_base']),
        ],
        bordercolor=[
            ('focus', C['border_focus']),
        ],
    )
    # Combobox dropdown list
    root.option_add('*TCombobox*Listbox.background', C['bg_surface'])
    root.option_add('*TCombobox*Listbox.foreground', C['text_primary'])
    root.option_add('*TCombobox*Listbox.selectBackground', C['accent_subtle'])
    root.option_add('*TCombobox*Listbox.selectForeground', C['text_primary'])

    # --- TNotebook ---
    style.configure('TNotebook',
        background=C['bg_base'],
        borderwidth=0,
        tabmargins=(8, 8, 0, 0),
    )
    style.configure('TNotebook.Tab',
        background=C['tab_inactive_bg'],
        foreground=C['tab_inactive_text'],
        padding=(28, 12),
        font=(ff, 11),
        borderwidth=0,
    )
    style.map('TNotebook.Tab',
        background=[
            ('selected', C['tab_active_bg']),
            ('active', C['tab_hover_bg']),
        ],
        foreground=[
            ('selected', C['tab_active_text']),
        ],
        expand=[
            ('selected', (0, 0, 0, 2)),
        ],
    )

    # --- TLabelframe (kept for compatibility, prefer create_section) ---
    style.configure('TLabelframe',
        background=C['bg_surface'],
        foreground=C['text_primary'],
        borderwidth=1,
        bordercolor=C['border_subtle'],
        relief='flat',
    )
    style.configure('TLabelframe.Label',
        background=C['bg_surface'],
        foreground=C['text_primary'],
        font=(ff, 12, 'bold'),
    )

    # --- Treeview ---
    style.configure('Treeview',
        background=C['bg_surface'],
        foreground=C['text_primary'],
        fieldbackground=C['bg_surface'],
        borderwidth=0,
        font=(ff, 11),
        rowheight=30,
    )
    style.configure('Treeview.Heading',
        background=C['tree_header_bg'],
        foreground=C['tree_header_fg'],
        borderwidth=0,
        font=(ff, 10, 'bold'),
        padding=(8, 8),
    )
    style.map('Treeview',
        background=[('selected', C['tree_selected'])],
        foreground=[('selected', C['text_primary'])],
    )
    style.map('Treeview.Heading',
        background=[('active', C['bg_hover'])],
    )

    # --- Vertical.TScrollbar ---
    style.configure('Vertical.TScrollbar',
        background=C['scroll_thumb'],
        troughcolor=C['scroll_track'],
        borderwidth=0,
        arrowcolor=C['text_secondary'],
        width=10,
    )
    style.map('Vertical.TScrollbar',
        background=[('active', C['scroll_hover'])],
    )

    # --- TRadiobutton ---
    style.configure('TRadiobutton',
        background=C['bg_base'],
        foreground=C['text_primary'],
        indicatorcolor=C['border_default'],
        font=(ff, 11),
    )
    style.map('TRadiobutton',
        indicatorcolor=[('selected', C['accent'])],
        background=[('active', C['bg_hover'])],
    )
    # Variant for use on card/surface backgrounds
    style.configure('Surface.TRadiobutton',
        background=C['bg_surface'],
    )
    style.map('Surface.TRadiobutton',
        background=[('active', C['bg_hover'])],
    )
    # Variant for elevated surfaces (dialogs)
    style.configure('Elevated.TRadiobutton',
        background=C['bg_elevated'],
    )
    style.map('Elevated.TRadiobutton',
        background=[('active', C['bg_hover'])],
    )

    # --- TCheckbutton ---
    style.configure('TCheckbutton',
        background=C['bg_base'],
        foreground=C['text_primary'],
        indicatorcolor=C['border_default'],
        font=(ff, 11),
    )
    style.map('TCheckbutton',
        indicatorcolor=[('selected', C['accent'])],
        background=[('active', C['bg_hover'])],
    )

    # --- Horizontal.TProgressbar ---
    style.configure('Horizontal.TProgressbar',
        troughcolor=C['progress_track'],
        background=C['progress_fill'],
        borderwidth=0,
        thickness=6,
    )

    # --- TSeparator ---
    style.configure('TSeparator',
        background=C['border_subtle'],
    )

    # Root window configuration
    root.configure(bg=C['bg_base'])


# ============================================================
# TREEVIEW HELPERS
# ============================================================

def setup_treeview_tags(tree: ttk.Treeview):
    """Configure alternating row colors and status tags on a Treeview."""
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
