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
    # --- Backgrounds (Tailwind Slate) ---
    'bg_base':        '#f8fafc',   # slate-50  — page background
    'bg_surface':     '#ffffff',   # white     — card/panel surfaces
    'bg_elevated':    '#ffffff',   # white     — raised surfaces
    'bg_input':       '#f8fafc',   # slate-50  — input field fill
    'bg_hover':       '#f1f5f9',   # slate-100 — hover highlight

    # --- Text (Tailwind Slate) ---
    'text_primary':   '#1e293b',   # slate-800
    'text_secondary': '#64748b',   # slate-500
    'text_tertiary':  '#64748b',   # slate-500 — was slate-400 (2.6:1 on white, fails WCAG AA)
    'text_inverse':   '#ffffff',

    # --- Accent / Brand (Tailwind Blue) ---
    'accent':         '#2563eb',   # blue-600  — primary interactive
    'accent_hover':   '#1d4ed8',   # blue-700  — hover
    'accent_pressed': '#1e40af',   # blue-800  — active/pressed
    'accent_subtle':  '#eff6ff',   # blue-50   — subtle background tint

    # --- Borders (Tailwind Slate) ---
    'border_subtle':  '#e2e8f0',   # slate-200
    'border_default': '#cbd5e1',   # slate-300
    'border_focus':   '#2563eb',   # blue-600

    # --- Semantic (Tailwind Emerald / Amber / Red) ---
    'success':        '#047857',   # emerald-700 — was emerald-500 (2.5:1 on white)
    'success_bg':     '#ecfdf5',   # emerald-50
    'success_hover':  '#065f46',   # emerald-800
    'success_pressed': '#064e3b',  # emerald-900
    'warning':        '#b45309',   # amber-700 — was amber-500 (2.1:1 on white)
    'warning_bg':     '#fffbeb',   # amber-50
    'error':          '#b91c1c',   # red-700 — was red-500 (3.8:1 on white)
    'error_bg':       '#fef2f2',   # red-50
    'info':           '#2563eb',   # blue-600 — was blue-500 (3.7:1 on white)

    # --- Tab bar ---
    'tab_inactive_bg':   '#e2e8f0',   # slate-200
    'tab_inactive_text': '#64748b',   # slate-500
    'tab_active_bg':     '#ffffff',
    'tab_active_text':   '#1e293b',   # slate-800
    'tab_hover_bg':      '#cbd5e1',   # slate-300

    # --- Treeview ---
    'tree_row_even':  '#ffffff',
    'tree_row_odd':   '#f8fafc',   # slate-50
    'tree_selected':  '#eff6ff',   # blue-50
    'tree_header_bg': '#f8fafc',   # slate-50
    'tree_header_fg': '#64748b',   # slate-500

    # --- Scrollbar ---
    'scroll_track':   '#f8fafc',   # slate-50
    'scroll_thumb':   '#cbd5e1',   # slate-300
    'scroll_hover':   '#94a3b8',   # slate-400

    # --- Progress bar ---
    'progress_track': '#e2e8f0',   # slate-200
    'progress_fill':  '#2563eb',   # blue-600

    # --- Canvas / Preview ---
    'canvas_bg':      '#f8fafc',   # slate-50
    'canvas_border':  '#e2e8f0',   # slate-200
}


# ============================================================
# TYPOGRAPHY
# ============================================================

def get_system_fonts() -> dict:
    """Return platform-appropriate font families.

    Font is resolved lazily by resolve_font_family() after Tk is
    initialised — see below.  We store preferred + fallback here.
    """
    system = platform.system()
    if system == 'Windows':
        return {
            'preferred': 'Inter',
            'family': 'Segoe UI',       # resolved at runtime
            'mono': 'Consolas',
        }
    elif system == 'Darwin':
        return {
            'preferred': 'Inter',
            'family': 'Helvetica Neue',  # resolved at runtime
            'mono': 'Menlo',
        }
    else:
        return {
            'preferred': 'Inter',
            'family': 'DejaVu Sans',     # resolved at runtime
            'mono': 'DejaVu Sans Mono',
        }


SYSTEM_FONTS = get_system_fonts()


def resolve_font_family():
    """Check if Inter is available and update SYSTEM_FONTS['family'].

    Must be called AFTER the Tk root window is created, because
    tkinter.font.families() requires an active Tk instance.
    """
    try:
        import tkinter.font as tkfont
        available = tkfont.families()
        if SYSTEM_FONTS['preferred'] in available:
            SYSTEM_FONTS['family'] = SYSTEM_FONTS['preferred']
    except Exception:
        pass  # keep platform default


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
    'page_padding':  24,   # was 20 — matches Tailwind p-6
    'section_gap':   20,   # was 16 — more breathing room
    'element_gap':   12,   # was 10
    'inner_padding': 20,   # was 16 — matches Tailwind p-5
    'button_gap':    12,   # was 10
    'input_gap':     10,   # was 8
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
    # litera paints every ttk.Frame white, which hid the page/card split:
    # labels asking for bg_base drew pale boxes on a white page. The page
    # is bg_base and cards are bg_surface, so set the base TFrame to match.
    style.configure('TFrame', background=C['bg_base'])
    # The notebook's tab strip and pane edge were white too; match the page,
    # and let the selected tab join the page it opens onto.
    style.configure('TNotebook',
        background=C['bg_base'],
        lightcolor=C['bg_base'],
        darkcolor=C['bg_base'],
    )
    style.map('TNotebook.Tab',
        background=[('selected', C['bg_base']), ('!selected', C['bg_surface'])],
        lightcolor=[('selected', C['bg_base']), ('!selected', C['bg_surface'])],
    )
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
    # litera's selected row is white on grey #adb5bd (2.1:1).
    style.map('Treeview',
        background=[('selected', C['tree_selected'])],
        foreground=[('selected', C['text_primary'])],
    )

    # ── Solid buttons ───────────────────────────────────────────
    # litera's are white on #4582ec (3.7:1) and #02b875 (2.6:1), and they
    # get LIGHTER on hover/press. Use our accent/success colours and darken
    # on hover/press so every state keeps white text at 4.5:1 or better.
    # Build each style first: ttkbootstrap builds on first use and would
    # overwrite anything configured before then.
    solid_buttons = {
        'TButton':         (C['accent'], C['accent_hover'], C['accent_pressed']),
        'primary.TButton': (C['accent'], C['accent_hover'], C['accent_pressed']),
        'success.TButton': (C['success'], C['success_hover'], C['success_pressed']),
    }
    for name, (base, hover, pressed) in solid_buttons.items():
        tbs.Bootstyle.update_ttk_widget_style(None, name)
        disabled = style.lookup(name, 'background', ['disabled'])
        states = [
            ('disabled', disabled),
            ('pressed !disabled', pressed),
            ('hover !disabled', hover),
        ]
        style.configure(name, background=base, bordercolor=base,
                        darkcolor=base, lightcolor=base)
        style.map(name, background=states, bordercolor=states,
                  darkcolor=states, lightcolor=states)

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
        foreground='#92400e',   # amber-800
    )
    tree.tag_configure('success_row',
        background=COLORS['success_bg'],
        foreground='#065f46',   # emerald-800
    )
    tree.tag_configure('combed',
        foreground=COLORS['accent'],
    )


def bind_treeview_hover(tree: ttk.Treeview):
    """Add hover highlighting to a Treeview widget.

    Throttled to fire at most every 50ms — on macOS trackpads, <Motion>
    fires at 60Hz which floods the Tcl event loop with identify_row() calls.
    """
    hovered = {'item': None}
    _throttle_id = [None]  # mutable container for nonlocal-like access

    def _process_motion(y):
        """Actually process the hover — called from throttle timer."""
        _throttle_id[0] = None
        item = tree.identify_row(y)
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

    def on_motion(event):
        # Throttle: skip if a timer is already pending
        if _throttle_id[0] is not None:
            return
        _throttle_id[0] = tree.after(50, _process_motion, event.y)

    def on_leave(event):
        # Cancel pending throttle timer
        if _throttle_id[0] is not None:
            tree.after_cancel(_throttle_id[0])
            _throttle_id[0] = None
        if hovered['item']:
            tags = list(tree.item(hovered['item'], 'tags'))
            if 'hover' in tags:
                tags.remove('hover')
                tree.item(hovered['item'], tags=tags)
            hovered['item'] = None

    tree.bind('<Motion>', on_motion)
    tree.bind('<Leave>', on_leave)
