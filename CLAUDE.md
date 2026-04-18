# Bulk PDF Generator — Project Context

## What This Is

A Python desktop app (tkinter/ttkbootstrap GUI) that batch-fills PDF forms from spreadsheet data. Originally built for VCAA Special Examination Arrangements forms but works with any PDF form. Distributed as a single Windows `.exe` via PyInstaller.

**This is NOT a web app. It does NOT deploy to Google Cloud.** It is a local desktop application.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| GUI | tkinter + ttkbootstrap (litera theme) |
| PDF reading | PyMuPDF (fitz) |
| PDF writing | pypdf |
| Data loading | pandas (Excel/CSV) |
| Excel export | openpyxl |
| Image processing | Pillow |
| Packaging | PyInstaller (single-file .exe) |
| Python | 3.10+ |

## Repository

| | |
|---|---|
| **Origin** | `https://github.com/mrdavearms/bulk-pdf-extractor-and-generator.git` |
| **CI/CD** | GitHub Actions (`.github/workflows/release.yml`) |

> GitLab remote is legacy and no longer actively maintained. Do not push to or sync with GitLab.

## Source Files

| File | Purpose |
|------|---------|
| `pdf_generator.py` | Main application (~3230 lines) — GUI, dialogs, generation pipeline |
| `models.py` | Data models: `PDFField`, `TemplateConfig`, `AppSettings` |
| `pdf_analyzer.py` | PDF field extraction engine (PyMuPDF) |
| `visual_preview.py` | PDF page rendering + field highlighting, dual-tier cache |
| `preview_renderer.py` | Threaded preview renderer — wraps `visual_preview.py` with debouncing, stale-result guard, and background PIL work |
| `combed_filler.py` | Character-by-character combed field filling |
| `theme.py` | Centralised theme (colours, fonts, spacing) |
| `markdown_renderer.py` | Markdown → tkinter Text widget renderer |
| `_generate_version.py` | Build-time script: bakes git commit, date, and version tag into `_version.py` |
| `getting_started.md` | In-app guide content (rendered in Tab 0) |
| `tests/` | Unit test suite — run with `venv/bin/python -m pytest tests/ -v` |

## Key Architecture Decisions

- **Thread safety**: PDF generation runs on a background thread with `copy.deepcopy()` snapshot of all shared state. UI updates via `root.after()`.
- **PyMuPDF thread safety (CRITICAL)**: `fitz.Document` is NOT thread-safe. `_get_page_image()` must ALWAYS run on the main thread. Only pure PIL operations (`Image.copy()`, `ImageDraw`, `Image.resize()`) are safe to run off-thread. `PreviewRenderer` enforces this boundary — never move PyMuPDF calls off-thread.
- **Atomic file writes**: Template configs and settings use `tempfile` + `os.replace()` to prevent corruption on crash.
- **Dual-tier caching**: Preview renders cached in memory (LRU) and on disk (PNG).
- **Cross-platform scrolling**: Mousewheel handlers branch by `sys.platform` — Windows (`delta/120`), macOS (`delta`), Linux (`Button-4`/`Button-5`).
- **Backward-compatible persistence**: `from_json()` filters unknown keys so newer configs load in older versions.
- **Field mapping**: `PDFField.excel_column` stores the explicit Excel column name per field. `TemplateConfig.field_excel_columns` persists these as `{field_name: col_name}`. Generation checks `field.excel_column` first, then falls back to auto-match by field name (case-insensitive). Tab 2 is the UI for viewing and editing these mappings.
- **Tab lifecycle**: Tab 2 starts disabled; enabled by `analyze_pdf_fields()` after successful analysis. `_refresh_tab2_mappings()` is the single rebuild point — called after analysis, after Excel load, and after template load.
- **Tab 2 in-place updates**: `self._mapping_rows` (list of dicts, one per field) tracks widget references for `_refresh_tab2_mappings()` in-place updates. Rebuild only when field names or count change; otherwise update comboboxes/labels in-place to avoid widget churn.
- **Data directory resilience**: `_resolve_data_dir()` tries `~/Documents/BulkPDFGenerator` first; falls back to `%LOCALAPPDATA%/BulkPDFGenerator` if `makedirs` fails (common on school networks with GPO-redirected Documents folders). Both `settings_file` and `templates_directory` derive from this resolved path.
- **Build version**: `_get_build_info()` returns a 3-tuple `(commit, date, version_tag)` — `BUILD_VERSION` is baked at build time via `git describe --tags --abbrev=0`. Result cached on `self._build_info` in `__init__` to avoid duplicate subprocess calls.
- **Update check**: `check_for_update(current_version)` is a module-level pure function (no GUI dependency) hitting the GitHub Releases API. Called from `_run_update_check()` on a daemon thread; result dispatched to `_show_update_result()` via `root.after()` — consistent with the existing thread-safety pattern.

## Tab Overview

| Tab | Name | Purpose |
|-----|------|---------|
| 0 | Getting Started | In-app guide (Markdown rendered) |
| 1 | Analyse Template | PDF analysis, field audit, visual preview, template save |
| 2 | Map Fields | Explicit field→Excel column mapping editor |
| 3 | Generate PDFs | Load data, preview students, batch generate |
| 4 | About | Version, build info, developer contact |

## Release Workflow

Releases are built by **GitHub Actions** and published to **GitHub Releases**. The `.exe` and `.app` are NOT committed to git (`dist/` is in `.gitignore`).

**GitHub compliance rule**: never link directly to binary assets (`.exe`, `.dmg`) in the README — link to the Releases *page* only. Direct binary links triggered GitHub's storage-abuse detection and caused account suspension.

### Automated release (GitHub Actions)

```bash
git tag v2.X
git push origin --tags
```

This triggers `.github/workflows/release.yml` which:
1. Builds Windows `.exe` on `windows-latest` using `BulkPDFGenerator.spec`
2. Builds macOS `.app` on `macos-latest` using `BulkPDFGenerator_mac.spec`, ad-hoc signs it, then packages as a polished `Bulk.PDF.Generator.macOS.dmg` via `create-dmg` (background image, Applications shortcut, volume icon)
3. `CFBundleVersion` / `CFBundleShortVersionString` are injected from the git tag at build time (the spec keeps placeholder values)
4. Creates a GitHub Release with both binaries attached

The README download badge auto-updates via shields.io — no manual step needed.

Releases are **fully automatic** — published as soon as the build completes, no manual step needed. Release notes are auto-generated from conventional commit messages since the last tag (`fix:` → **Fixed:**, `feat:` → **New:**, `perf:` → **Performance:**, etc.). `RELEASE_NOTES.md` is an optional override for custom wording; it is auto-cleared after each release so stale notes never carry forward.

Pre-release tags (`v2.8-beta`, `v2.8-rc1`, etc.) are automatically flagged as pre-releases on GitHub and excluded from the "Latest" badge on the README.

## Cross-Platform Build

Both platforms are built automatically by GitHub Actions. For local builds:
- **Windows .exe**: `python -m PyInstaller BulkPDFGenerator.spec --clean` → `dist/Bulk PDF Generator.exe`
- **macOS .app**: `python -m PyInstaller BulkPDFGenerator_mac.spec --clean` → `dist/Bulk PDF Generator.app`
- **Linux**: Run from source. No packaging currently set up.

## Git LFS

**Not used and not needed.** Binaries are distributed via GitHub Releases, not stored in git history. The `.gitignore` excludes `dist/` and `build/`. The only binaries tracked in git are small PNGs (icon, app visualisation).

## Field Data Types

Fields can be typed as `text`, `number`, or `date`:
- **Text**: pass-through
- **Number**: strips trailing `.0` from whole numbers
- **Date**: converts Excel serial numbers to DD/MM/YYYY (Australian format)

The audit dialog appears after PDF analysis with smart defaults (fields containing "date", "dob", "birth" → Date). Types are persisted in the template config JSON and restored on reload. Explicit user choices (including reverting a smart-guessed Date back to Text) are preserved.

Excel serial date range validation: only serials 1–2958465 are converted (1900-01-01 to 9999-12-31). Invalid values fall through to string conversion.

## Dev Environment

- **Python**: Use `venv/bin/python` — system `python`/`python3` doesn't have project deps. Install pytest once: `venv/bin/pip install pytest`.
- **Run tests**: `venv/bin/python -m pytest tests/ -v`
- **Performance tests**: `tests/test_performance.py` uses `inspect.getsource()` to verify structural patterns (anti-patterns absent from source) rather than flaky timing assertions. 17 tests covering threading, debounce, batch updates, throttling, dialog geometry.
- **Main class**: `BulkPDFGenerator` (not `BulkPDFApp` or similar)
- **About tab method**: `setup_tab_about()` (not `setup_tab4_about`)
- **Generation worker method**: `run_generation_tab3()` (not `generate_pdfs_worker` or similar)
- **Mocking**: patch at the module level — e.g. `patch.object(_generate_version.os.path, 'abspath', ...)` not `patch('os.path.abspath')`

## Developer

Dave Armstrong — Principal, Wangaratta High School
Email: Dave.Armstrong@education.vic.gov.au
