# Architecture -- Bulk PDF Generator v2.0

This document describes the internal architecture of the Bulk PDF Generator, covering module responsibilities, data flow, threading model, caching strategy, file safety, and platform considerations.

---

## Module Overview

The application is structured as seven Python modules with clear separation of concerns:

```
pdf_generator.py       ─── GUI + orchestration (main entry point)
    ├── models.py              ─── Data models and persistence
    ├── pdf_analyzer.py        ─── PDF field extraction engine
    ├── visual_preview.py      ─── PDF page rendering + field highlighting
    ├── combed_filler.py       ─── Character-by-character field filling
    ├── theme.py               ─── Centralised theme (colours, fonts, styles)
    └── markdown_renderer.py   ─── Markdown-to-tkinter Text renderer
```

All modules are pure Python with no circular imports. The main module imports all others; supporting modules only import `models` (for the `PDFField` dataclass) and `theme` (for rendering constants).

---

## Module Details

### `pdf_generator.py` -- Main Application

**~2100 lines.** Contains the `BulkPDFGenerator` class plus supporting dialog classes.

**Responsibilities:**
- tkinter root window, notebook (tabs), and all widget layout
- User interaction handling (button clicks, treeview selection, file dialogs)
- PDF generation orchestration (threading, progress, error reporting)
- Settings and template config persistence
- Lifecycle management (welcome dialog, school setup, window close cleanup)

**Key classes:**

| Class | Purpose |
|-------|---------|
| `BulkPDFGenerator` | Main app. Owns the root window, all tabs, settings, and state. |
| `ScrollableFrame` | Reusable scrollable container. Platform-aware mousewheel handling. |
| `WelcomeDialog` | First-run dialog. Routes user to Getting Started or Generate tab. |
| `SchoolSetupDialog` | Prompts for school name and year (used in output filenames). |
| `TemplateNameDialog` | Names a template when saving config. |

**Key methods on `BulkPDFGenerator`:**

| Method | What it does |
|--------|-------------|
| `setup_ui()` | Builds header, notebook, status bar, and all tabs |
| `create_section()` | Helper -- builds card-style sections with title + bordered content frame |
| `analyze_pdf_fields()` | Opens PDF with `PDFAnalyzer`, extracts fields, opens `VisualPreviewGenerator` |
| `on_field_selected()` | Renders field preview image on canvas when treeview row is clicked |
| `export_mapping_file()` | Writes `.xlsx` with field names, types, suggested Excel columns |
| `start_generation_tab3()` | Snapshots all UI state into a context dict, launches generation thread |
| `run_generation_tab3()` | Runs on background thread -- iterates rows, calls `_generate_single_pdf()` |
| `_generate_single_pdf()` | Fills one PDF via pypdf `PdfWriter`, handles combed fields |

---

### `models.py` -- Data Models

Three dataclasses with JSON serialisation:

**`PDFField`**
Represents a single field (or grouped combed field) extracted from a PDF. Stores field name, type, page number, combed metadata (length, sub-field names), bounding rectangle, and optional Excel column mapping.

**`TemplateConfig`**
Saved template configuration. Stores PDF path, field counts, mapping file reference, creation/usage timestamps, and critical field list. Serialises to/from JSON files.

**`AppSettings`**
Application preferences. Stores template directory, school info, combed field alignment, and welcome dialog state. Falls back to safe defaults on any load error.

**File safety:** Both `TemplateConfig.save_to_file()` and `AppSettings.save_to_file()` use atomic writes via `tempfile.NamedTemporaryFile` + `os.replace()`. This prevents corruption if the app crashes mid-write -- the old file remains intact until the new file is fully written and atomically swapped into place.

**Forward/backward compatibility:** `from_json()` methods filter incoming keys against the dataclass field set, silently dropping unknown keys (forward compat) and using field defaults for missing keys (backward compat).

---

### `pdf_analyzer.py` -- PDF Analysis Engine

Uses PyMuPDF (`fitz`) to open PDF documents and extract all form widgets.

**Combed field detection algorithm:**

1. Iterate all widgets across all pages
2. Match each field name against three regex patterns:
   - `Field[N]` (bracketed index)
   - `Field_N` (underscore separator)
   - `FieldN` (trailing digits)
3. Group matched fields by base name
4. For each group with 2+ members, check if indices form a contiguous sequence (e.g. 0,1,2,3 or 5,6,7,8)
5. If contiguous, emit a single `PDFField` with `is_combed=True` and all sub-field names
6. Otherwise, emit each as a separate regular field

The `_is_sequential()` method accepts contiguous sequences starting from any index (not just 0 or 1), handling PDFs where combed fields start at arbitrary offsets.

**Context manager pattern:** `PDFAnalyzer` implements `__enter__`/`__exit__` to ensure the fitz document is always closed, even on exceptions.

---

### `visual_preview.py` -- Visual Preview

Renders PDF pages as PIL Images and draws field highlight overlays.

**Two-tier caching:**

1. **Memory cache** -- `OrderedDict` with LRU eviction, capped at 5 entries (~60MB at 200 DPI). Most-recently-used pages stay in memory for instant re-rendering.
2. **Disk cache** -- PNG files in `.preview_cache/` directory. Survives app restarts. Page images are named `page_{N}_dpi_{D}.png`.

**Cache flow:**
```
Request page 3 at 150 DPI
  → Check memory cache (OrderedDict key "3_150")
    → HIT: return cached Image (move to end for LRU)
    → MISS: check disk cache (page_3_dpi_150.png)
      → HIT: load from disk, img.load() to release file handle, store in memory
      → MISS: render via fitz, save to disk, store in memory
```

**File handle safety:** `Image.open()` holds the file handle open until garbage collection. We call `img.load()` immediately after `Image.open()` to force a full read into memory and release the file handle. This prevents "file in use" errors on Windows when the cache directory is cleaned.

**Font path reliability:** Platform font loading uses absolute paths (`%WINDIR%\Fonts\segoeui.ttf` on Windows, `/System/Library/Fonts/Helvetica.ttc` on macOS) with fallback to `ImageFont.load_default()` if the system font is unavailable.

**Cache cleanup:** `clear_cache()` only deletes files matching `page_*.png` to avoid accidentally removing unrelated files. Each deletion is wrapped in `try/except OSError` to handle locked files gracefully.

---

### `combed_filler.py` -- Combed Field Filler

Pure-logic module (no GUI dependency) that splits text values into individual character fields.

**Algorithm:**
1. Receive a `PDFField` and a text value
2. If not combed, return `{field_name: value}` (pass-through)
3. If combed:
   - Strip whitespace
   - Truncate to field length if too long
   - Apply alignment (left or right-justify)
   - Map each character to its corresponding sub-field name
   - Fill remaining positions with empty string (or space if padding enabled)

**Overflow detection:** `validate_overflow()` and `get_overflow_warnings()` check all data rows for values exceeding combed field lengths, returning structured warning dicts for UI display.

---

### `theme.py` -- Theme System

Centralised theme configuration. All colours, fonts, and spacing constants are defined here and imported by other modules.

**Colour palette:** Modern light theme inspired by Logitech Options+. Organised into semantic groups:
- Background layers (`bg_base`, `bg_surface`, `bg_elevated`, `bg_input`, `bg_hover`)
- Text hierarchy (`text_primary`, `text_secondary`, `text_tertiary`, `text_inverse`)
- Accent/brand colours with hover and pressed states
- Semantic status colours (success, warning, error, info) with background tints
- Component-specific colours (tab bar, treeview, scrollbar, progress bar, canvas)

**Typography:** `get_system_fonts()` detects the platform and returns appropriate font families:
- Windows: Segoe UI / Consolas
- macOS: Helvetica Neue / Menlo
- Linux: DejaVu Sans / DejaVu Sans Mono

**`apply_dark_theme()`** (name kept for backward compatibility) configures all ttk widget styles using the `clam` theme as a base. Covers: TFrame, TLabel (6 variants), TButton (3 variants), TEntry, TCombobox, TNotebook, TLabelframe, Treeview, TScrollbar, TRadiobutton (3 variants), TCheckbutton, TProgressbar, and TSeparator.

**Card section pattern:** The main app uses `create_section()` instead of `ttk.LabelFrame` for modern card-style layouts. This function creates:
- A bold title label
- An outer border frame (`bg=border_subtle`, 1px padding)
- An inner content frame (`bg=bg_surface`, 16px padding)
- Optional subtitle in secondary text colour

---

### `markdown_renderer.py` -- Markdown Renderer

Parses a subset of Markdown and renders formatted text into a `tkinter.Text` widget using the tag system.

**Supported syntax:**
- Headings: `#`, `##`, `###`
- Bold: `**text**`
- Bullet lists: `* item` or `- item`
- Hyperlinks: `[text](url)` -- clickable, opens in default browser
- Horizontal rules: `---`, `***`, `___`
- Paragraph breaks (blank lines)

**Implementation:** Each markdown element maps to a tkinter Text tag (`h1`, `h2`, `h3`, `body`, `bold`, `bullet`, `link_base`, `spacer`, `hr`). Inline parsing uses a single compiled regex to find bold spans and links within any line. Each link gets a unique tag with bound click, enter, and leave events for cursor changes and `webbrowser.open()`.

---

## Data Flow

### Template Analysis Flow

```
User selects PDF file
  → PDFAnalyzer opens with context manager
    → fitz.open() loads document
    → analyze_fields() iterates all pages, collects widgets
    → _detect_combed_fields() groups by base name, checks sequences
    → Returns List[PDFField]
  → VisualPreviewGenerator opens (kept alive for preview clicks)
  → Fields displayed in Treeview
  → User clicks field → on_field_selected()
    → generate_field_preview() renders page + highlight overlay
    → Image displayed on tkinter Canvas with zoom support
```

### PDF Generation Flow

```
User clicks "Generate PDFs"
  → start_generation_tab3() snapshots ALL UI state into ctx dict
    ctx = {
      'pdf_path', 'output_folder', 'school_name', 'school_year',
      'analyzed_fields', 'pdf_fields', 'combed_padding', 'combed_align',
      'selected_rows' (list of row dicts)
    }
  → Background thread launched with ctx
    → run_generation_tab3(ctx) iterates selected rows
      → For each row:
        → Build output filename (sanitised, collision-safe)
        → _generate_single_pdf(ctx, row_data, output_path)
          → PdfReader opens template
          → PdfWriter clones pages
          → CombedFieldFiller splits combed values
          → writer.update_page_form_field_values() fills all fields
          → Write to output file
        → Progress callback via root.after() (thread-safe)
    → generation_complete_tab3() on main thread
```

### Thread Safety

PDF generation runs on a `threading.Thread` to keep the GUI responsive. Thread safety is achieved through:

1. **Context snapshot:** All UI state is captured into a plain `dict` before the thread starts. The background thread never touches tkinter widgets or `self` state -- it only reads from the snapshot.

2. **Main-thread callbacks:** Progress updates and completion handlers are scheduled via `root.after()`, which queues execution on the main thread event loop.

3. **Static method:** `format_value_tab3()` is a `@staticmethod` with no instance state access, making it safe to call from any thread.

---

## File Safety

### Atomic Writes

All configuration persistence (`TemplateConfig.save_to_file()`, `AppSettings.save_to_file()`) uses the atomic write pattern:

```python
with tempfile.NamedTemporaryFile('w', dir=same_dir, suffix='.tmp',
                                  delete=False, encoding='utf-8') as tmp:
    tmp.write(self.to_json())
    tmp_path = tmp.name
os.replace(tmp_path, filepath)
```

This ensures:
- The old file is never partially overwritten
- If the process crashes during write, the old file remains intact
- `os.replace()` is atomic on all major operating systems
- The temp file is created in the same directory to ensure same-filesystem rename

### Output Filename Collision Avoidance

Generated PDF filenames are constructed from student data (first name, surname, school name, year). To prevent accidental overwrites:

1. School name and year are sanitised: only alphanumeric characters, spaces, hyphens, and underscores are kept
2. If the output file already exists, a counter suffix is appended: `filename (1).pdf`, `filename (2).pdf`, etc.
3. The counter increments until a unique path is found

### Settings Resilience

`AppSettings.from_file()` catches `FileNotFoundError`, `json.JSONDecodeError`, `TypeError`, and `KeyError`, returning safe defaults on any failure. `TemplateConfig.from_file()` wraps errors in `ValueError` with descriptive messages identifying the problematic file. Both `from_json()` methods filter incoming keys against the dataclass field set, preventing crashes from extra keys added by newer app versions.

---

## Caching Strategy

### Visual Preview Cache

Two tiers to balance speed and memory:

| Tier | Storage | Capacity | Eviction | Persistence |
|------|---------|----------|----------|-------------|
| Memory | `OrderedDict` | 5 entries (~60MB) | LRU (oldest evicted) | Session only |
| Disk | PNG files in `.preview_cache/` | Unlimited | Manual (clear_cache) | Across sessions |

**Why two tiers?** Rendering a PDF page at 200 DPI via PyMuPDF takes 500-800ms. The memory cache makes repeated clicks on the same page instant (~50ms). The disk cache means previously rendered pages load quickly even after app restart.

**Memory cap:** At 200 DPI, a typical A4 page renders to ~12MB as a PIL Image. The 5-entry cap keeps memory usage under ~60MB. Pages are evicted in LRU order when the cap is exceeded.

### Template Config Cache

Template JSON files are small (<5KB) and loaded on demand. No caching -- direct file reads. The recent templates dropdown stores file paths, not parsed objects.

---

## Platform Considerations

### Windows
- Font: Segoe UI (absolute path via `%WINDIR%\Fonts\segoeui.ttf`)
- File opening: `os.startfile()` for "Open folder" functionality
- Mousewheel: `<MouseWheel>` event, delta divided by 120
- Launcher: `.bat` file that activates venv and runs Python

### macOS
- Font: Helvetica Neue (family name), Helvetica.ttc or SFNSText.ttf for PIL rendering
- File opening: `subprocess.run(['open', path])` with error handling
- Mousewheel: `<MouseWheel>` event, delta is already ±1
- Launcher: `.command` file (bash script) that activates venv and runs Python

### Linux
- Font: DejaVu Sans (family name), `ImageFont.load_default()` for PIL rendering
- File opening: `subprocess.run(['xdg-open', path])` with error handling
- Mousewheel: `<Button-4>` / `<Button-5>` events (scroll up/down)
- No launcher provided (run directly from terminal)

### Mousewheel Scoping

Mousewheel events are bound per-widget (not `bind_all`) to prevent conflicts between multiple `ScrollableFrame` instances and the preview canvas. Each scrollable container binds on `<Enter>` and unbinds on `<Leave>`.

---

## Error Handling Patterns

### PDF Operations
- All PDF open/close operations use context managers (`with PDFAnalyzer(...) as analyzer:`)
- The `VisualPreviewGenerator` is kept alive between field clicks for performance, but explicitly closed in `_close_preview_generator()` on tab switch, new analysis, or window close
- If preview generation fails (e.g. corrupted PDF), the error is caught and the preview canvas shows nothing rather than crashing

### Background Thread Errors
- The generation thread wraps each PDF in `try/except Exception`
- Individual failures are counted and reported in the completion summary
- The thread continues generating remaining PDFs after a single failure
- Error messages capture `str(e)` before the exception scope closes (avoiding stale closure references in lambda callbacks)

### File I/O
- CSV files are first tried with `utf-8-sig` encoding (handles BOM), falling back to `latin-1`
- File extension matching is case-insensitive (`.CSV`, `.Xlsx`, etc.)
- Markdown file loading catches `FileNotFoundError`, `PermissionError`, `UnicodeDecodeError`, and `OSError`
- Disk cache cleanup silently skips locked files (`try/except OSError` per file)

---

## UI Architecture

### Layout Hierarchy

```
root (tk.Tk)
  ├── header_frame (tk.Frame, bg_surface)
  │     ├── title + subtitle (left side)
  │     ├── school info (right side)
  │     └── 3px accent stripe (bottom border)
  ├── notebook (ttk.Notebook)
  │     ├── Tab 0: Getting Started (ScrollableFrame → Text widget with markdown)
  │     ├── Tab 1: Analyse Template (ScrollableFrame → sections)
  │     │     ├── Load Template section (card)
  │     │     ├── Analysis Results section (card)
  │     │     │     ├── Treeview (field list)
  │     │     │     └── Canvas (PDF preview with zoom)
  │     │     └── Action buttons
  │     ├── Tab 2: Map Fields (ScrollableFrame → sections)
  │     ├── Tab 3: Generate PDFs (ScrollableFrame → sections)
  │     │     ├── File Selection section (card)
  │     │     ├── Validation section (card)
  │     │     ├── Student Preview section (card with Treeview)
  │     │     └── Generation controls + progress bar
  │     └── Tab 4: About (centred card)
  └── status_bar (tk.Frame, bg_surface)
        └── status_label (tk.Label)
```

### Card Section Pattern

All major UI sections use `create_section()` which produces:

```
  Section Title                    ← SectionTitle.TLabel
  Optional subtitle                ← SectionSubtitle.TLabel
┌─────────────────────────────┐   ← Outer frame (bg=border_subtle, 1px padding)
│                             │
│   Inner content frame       │   ← Inner frame (bg=bg_surface, 16px padding)
│   (returned to caller)      │
│                             │
└─────────────────────────────┘
```

This replaces tkinter's `ttk.LabelFrame` with a cleaner, more modern appearance that matches the light theme.

### Zoom Preview

The PDF field preview canvas supports:
- Zoom in/out buttons (50% to 400%)
- "Fit" button to reset to fit-to-width
- Mouse wheel zoom (when cursor is over the canvas)
- Preview rendering caches the raw PIL Image at the current DPI, then applies zoom by resizing for display

---

## Security Considerations

- **No network access:** The app is fully offline. No data is sent anywhere.
- **No credential storage:** No passwords, API keys, or tokens.
- **File system scope:** The app reads PDFs and spreadsheets selected by the user, and writes output PDFs to a user-selected directory. It does not traverse directories or access files outside user selection.
- **Filename sanitisation:** Output filenames strip all characters except alphanumeric, spaces, hyphens, and underscores to prevent path traversal or shell injection via crafted student names.
- **No code execution:** User data (names, dates, etc.) is treated as plain text values for PDF form fields. No data is evaluated as code.

---

## Future Considerations

- **Tab 2 (Map Fields):** Currently a placeholder. The intended feature is a drag-and-drop UI for manually mapping PDF fields to Excel columns when auto-matching fails.
- **Settings dialog:** In-app UI for changing combed field alignment, padding, and other preferences currently stored in `settings.json`.
- **Overflow warnings:** Pre-generation warnings when data values exceed combed field lengths, with option to proceed or cancel.
- **Cache management:** UI controls to view cache size and clear cached preview images.
