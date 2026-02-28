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
| **Primary (origin)** | `https://gitlab.com/davearmswork/bulk-pdf-extractor-and-generator.git` |
| **Mirror (github)** | `https://github.com/mrdavearms/Bulk-PDF-generator-for-Vic-schools.git` (suspended) |
| **GitLab user** | `dave401` |
| **glab CLI** | Authenticated, v1.86.0+ |

## Source Files

| File | Purpose |
|------|---------|
| `vcaa_pdf_generator_v2.py` | Main application (~2700 lines) — GUI, dialogs, generation pipeline |
| `vcaa_models.py` | Data models: `PDFField`, `TemplateConfig`, `AppSettings` |
| `vcaa_pdf_analyzer.py` | PDF field extraction engine (PyMuPDF) |
| `vcaa_visual_preview.py` | PDF page rendering + field highlighting, dual-tier cache |
| `vcaa_combed_filler.py` | Character-by-character combed field filling |
| `vcaa_theme.py` | Centralised theme (colours, fonts, spacing) |
| `vcaa_markdown_renderer.py` | Markdown → tkinter Text widget renderer |
| `_generate_version.py` | Build-time script: bakes git commit + date into `_version.py` |
| `getting_started.md` | In-app guide content (rendered in Tab 0) |

## Key Architecture Decisions

- **Thread safety**: PDF generation runs on a background thread with `copy.deepcopy()` snapshot of all shared state. UI updates via `root.after()`.
- **Atomic file writes**: Template configs and settings use `tempfile` + `os.replace()` to prevent corruption on crash.
- **Dual-tier caching**: Preview renders cached in memory (LRU) and on disk (PNG).
- **Cross-platform scrolling**: Mousewheel handlers branch by `sys.platform` — Windows (`delta/120`), macOS (`delta`), Linux (`Button-4`/`Button-5`).
- **Backward-compatible persistence**: `from_json()` filters unknown keys so newer configs load in older versions.

## Release Workflow

Releases go to **GitLab Releases** (not GitHub). The `.exe` is NOT committed to git (`dist/` is in `.gitignore`).

### Quick release

```bash
./release.sh v2.X
```

This script automates: version baking, PyInstaller build, git tag + push, GitLab Release creation, `.exe` upload + linking, and README badge update.

### Manual release (if the script breaks)

```bash
# 1. Build
python _generate_version.py
python -m PyInstaller BulkPDFGenerator.spec --clean

# 2. Tag and push
git tag v2.X
git push origin main --tags

# 3. Create release
glab release create v2.X --name "Bulk PDF Generator v2.X" --notes "Release notes"

# 4. Upload exe (glab has a bug with direct file uploads, use curl)
TOKEN=$(glab auth status --show-token 2>&1 | grep "Token found" | sed 's/.*Token found: //')
curl --request POST --header "PRIVATE-TOKEN: $TOKEN" \
  --form "file=@dist/Bulk PDF Generator.exe" \
  "https://gitlab.com/api/v4/projects/davearmswork%2Fbulk-pdf-extractor-and-generator/uploads"

# 5. Link the upload to the release (use full_path from step 4 JSON response)
curl --request POST --header "PRIVATE-TOKEN: $TOKEN" \
  --header "Content-Type: application/json" \
  --data '{"name":"Bulk.PDF.Generator.exe","url":"https://gitlab.com<FULL_PATH>","filepath":"/binaries/Bulk.PDF.Generator.exe","link_type":"other"}' \
  "https://gitlab.com/api/v4/projects/davearmswork%2Fbulk-pdf-extractor-and-generator/releases/v2.X/assets/links"

# 6. Update README badge version and push
```

### Known quirks

- `glab release create` with file arguments fails with "Filepath is in an invalid format" — this is a glab CLI bug. Use the curl two-step (upload then link) as a workaround.
- GitLab project uploads go to `/-/project/<id>/uploads/<hash>/filename` — the `full_path` from the upload response is what you pass to the asset link.
- The README download badge is a static shields.io badge (not dynamic) — the version must be updated manually in `README.md` after each release (the release script handles this).

## Cross-Platform Build

- **Windows .exe**: Build on Windows with `python -m PyInstaller BulkPDFGenerator.spec --clean`. Output: `dist/Bulk PDF Generator.exe`.
- **macOS .app**: Must build on macOS. PyInstaller cannot cross-compile. Clone repo on Mac, install deps, run PyInstaller.
- **Linux**: Run from source. No packaging currently set up.

## Git LFS

**Not used and not needed.** The `.exe` is distributed via GitLab Releases (file hosting), not stored in git history. The `.gitignore` excludes `dist/` and `build/`. The only binaries tracked in git are small PNGs (icon, app visualisation).

## Field Data Types

Fields can be typed as `text`, `number`, or `date`:
- **Text**: pass-through
- **Number**: strips trailing `.0` from whole numbers
- **Date**: converts Excel serial numbers to DD/MM/YYYY (Australian format)

The audit dialog appears after PDF analysis with smart defaults (fields containing "date", "dob", "birth" → Date). Types are persisted in the template config JSON and restored on reload. Explicit user choices (including reverting a smart-guessed Date back to Text) are preserved.

Excel serial date range validation: only serials 1–2958465 are converted (1900-01-01 to 9999-12-31). Invalid values fall through to string conversion.

## Developer

Dave Armstrong — Principal, Wangaratta High School
Email: Dave.Armstrong@education.vic.gov.au
