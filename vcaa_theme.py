#!/usr/bin/env python3
"""
VCAA PDF Generator v2.0 -- Dark Theme System
Centralized theme module for colors, fonts, spacing, and ttk style configuration.
"""

import platform
import tkinter as tk
from tkinter import ttk


# ============================================================
# COLOR PALETTE -- Modern Dark Theme
# ============================================================

COLORS = {
    # --- Backgrounds (layered surface hierarchy) ---
    'bg_base':        '#1a1b1e',   # Window background (darkest)
    'bg_surface':     '#25262b',   # Panels, cards, frames
    'bg_elevated':    '#2c2e33',   # Elevated surfaces (dialogs, dropdowns)
    'bg_input':       '#1e1f23',   # Entry fields, text areas
    'bg_hover':       '#32343a',   # Hover state for interactive surfaces

    # --- Text ---
    'text_primary':   '#e1e2e5',   # Main body text
    'text_secondary': '#909296',   # Muted/secondary text
    'text_tertiary':  '#5c5f66',   # Disabled text, placeholders
    'text_inverse':   '#1a1b1e',   # Text on accent-colored backgrounds

    # --- Accent / Brand ---
    'accent':         '#4c8bf5',   # Primary accent (buttons, active tabs)
    'accent_hover':   '#3a7ae0',   # Accent hover
    'accent_pressed': '#2d6ad4',   # Accent pressed
    'accent_subtle':  '#2a3a5c',   # Accent tint for backgrounds

    # --- Borders ---
    'border_subtle':  '#373a40',   # Subtle borders (cards, dividers)
    'border_default': '#4a4d54',   # Default borders (inputs)
    'border_focus':   '#4c8bf5',   # Focus ring (matches accent)

    # --- Semantic (status) ---
    'success':        '#51cf66',   # Green for success/ready states
    'success_bg':     '#1e3a25',   # Success background tint
    'warning':        '#fcc419',   # Yellow/amber for warnings
    'warning_bg':     '#3a3520',   # Warning background tint
    'error':          '#ff6b6b',   # Red for errors
    'error_bg':       '#3a1e1e',   # Error background tint
    'info':           '#74c0fc',   # Blue for informational

    # --- Tab bar ---
    'tab_inactive_bg':   '#25262b',
    'tab_inactive_text': '#909296',
    'tab_active_bg':     '#1a1b1e',
    'tab_active_text':   '#e1e2e5',
    'tab_hover_bg':      '#2c2e33',

    # --- Treeview ---
    'tree_row_even':  '#25262b',
    'tree_row_odd':   '#2a2b30',
    'tree_selected':  '#2a3a5c',
    'tree_header_bg': '#2c2e33',
    'tree_header_fg': '#c1c2c5',

    # --- Scrollbar ---
    'scroll_track':   '#25262b',
    'scroll_thumb':   '#4a4d54',
    'scroll_hover':   '#5c5f66',

    # --- Progress bar ---
    'progress_track': '#2c2e33',
    'progress_fill':  '#4c8bf5',

    # --- Canvas / Preview ---
    'canvas_bg':      '#1e1f23',
    'canvas_border':  '#373a40',
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
    'page_padding':  15,   # Main content area padding
    'section_gap':   12,   # Gap between card sections
    'element_gap':    8,   # Gap between elements in a section
    'inner_padding': 12,   # Padding inside cards/frames
    'button_gap':     8,   # Gap between adjacent buttons
    'input_gap':      6,   # Gap between label and input
}


# ============================================================
# THEME APPLICATION -- Configure All ttk Widget Styles
# ============================================================

def apply_dark_theme(root: tk.Tk):
    """Apply the complete dark theme to all ttk widgets."""
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

    # --- TButton ---
    style.configure('TButton',
        background=C['bg_elevated'],
        foreground=C['text_primary'],
        borderwidth=1,
        focuscolor=C['accent'],
        font=(ff, 11),
        padding=(16, 8),
    )
    style.map('TButton',
        background=[
            ('active', C['bg_hover']),
            ('pressed', C['accent_pressed']),
            ('disabled', C['bg_surface']),
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
        padding=(20, 10),
        borderwidth=0,
    )
    style.map('Accent.TButton',
        background=[
            ('active', C['accent_hover']),
            ('pressed', C['accent_pressed']),
            ('disabled', '#3a3d44'),
        ],
        foreground=[
            ('disabled', C['text_tertiary']),
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
            ('focus', C['bg_input']),
            ('disabled', C['bg_surface']),
        ],
        bordercolor=[
            ('focus', C['border_focus']),
            ('!focus', C['border_default']),
        ],
    )

    # --- TCombobox ---
    style.configure('TCombobox',
        fieldbackground=C['bg_input'],
        background=C['bg_elevated'],
        foreground=C['text_primary'],
        arrowcolor=C['text_secondary'],
        borderwidth=1,
        padding=(8, 6),
    )
    style.map('TCombobox',
        fieldbackground=[
            ('readonly', C['bg_input']),
            ('disabled', C['bg_surface']),
        ],
        bordercolor=[
            ('focus', C['border_focus']),
        ],
    )
    # Combobox dropdown list
    root.option_add('*TCombobox*Listbox.background', C['bg_elevated'])
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
        padding=(24, 10),
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

    # --- TLabelframe ---
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
        rowheight=28,
    )
    style.configure('Treeview.Heading',
        background=C['tree_header_bg'],
        foreground=C['tree_header_fg'],
        borderwidth=0,
        font=(ff, 10, 'bold'),
        padding=(8, 6),
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
        indicatorcolor=C['bg_input'],
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

    # --- Horizontal.TProgressbar ---
    style.configure('Horizontal.TProgressbar',
        troughcolor=C['progress_track'],
        background=C['progress_fill'],
        borderwidth=0,
        thickness=8,
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
        foreground=COLORS['warning'],
    )
    tree.tag_configure('success_row',
        background=COLORS['success_bg'],
        foreground=COLORS['success'],
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
