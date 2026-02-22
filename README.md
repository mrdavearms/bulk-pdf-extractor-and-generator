# Bulk PDF Generator v2.0

A cross-platform desktop application that batch-fills PDF form templates from spreadsheet data. Built with Python and tkinter, it handles regular text fields, checkboxes, and combed (character-by-character) fields automatically.

Originally built to streamline VCAA Special Examination Arrangements Evidence Application forms for schools, but works with any PDF form template.

**Repository:** [github.com/mrdavearms/VCAA-PDF-Generator](https://github.com/mrdavearms/VCAA-PDF-Generator)

---

## Features

- **PDF template analysis** -- scans any PDF form and extracts all fields with type detection
- **Combed field auto-detection** -- character-by-character fields (e.g. student numbers) detected and filled automatically
- **Visual field preview** -- click any detected field to see its exact location highlighted on the PDF page, with zoom and pan controls
- **Batch generation** -- fill hundreds of PDFs from a single Excel/CSV spreadsheet in one click
- **Template library** -- save analysed templates for instant reuse
- **Excel mapping export** -- generates a ready-to-use spreadsheet with smart column name suggestions
- **Cross-platform** -- Windows and macOS, with platform-aware fonts, file handling, and launchers

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/mrdavearms/VCAA-PDF-Generator.git
cd VCAA-PDF-Generator
```

### 2. Create a virtual environment and install dependencies

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

> **Note:** tkinter is required but ships with standard Python on Windows. On macOS, install via `brew install python-tk@3.xx` (matching your Python version). On Linux, install `python3-tk` via your package manager.

### 3. Run the application

```bash
python vcaa_pdf_generator_v2.py
```

Or use the platform launchers:
- **Windows:** Double-click `Launch_BulkPDFGenerator.bat`
- **macOS:** Double-click `Launch_BulkPDFGenerator.command` (make executable first: `chmod +x Launch_BulkPDFGenerator.command`)

---

## How It Works

The app uses a tabbed workflow:

### Tab 0: Getting Started

An in-app guide explaining how to prepare PDF templates in Adobe Acrobat Pro -- naming form fields, editing properties, and setting up combed fields. Rendered from markdown with clickable hyperlinks.

### Tab 1: Analyse Template

1. Load a PDF template (browse or select from recent templates)
2. Click **Analyse Fields** to scan for all form fields
3. Review the field list -- regular text fields, combed fields, checkboxes, and signatures are identified
4. Click any field to see its exact location highlighted on the PDF page
5. Export a mapping spreadsheet (`.xlsx`) with smart column name suggestions
6. Save the template configuration for future use

### Tab 2: Map Fields

Displays auto-matching status. Fields are matched to Excel columns by case-insensitive name comparison. Reserved for future manual mapping UI.

### Tab 3: Generate PDFs

1. Select the PDF template and Excel/CSV data file
2. Click **Load & Preview Data** to validate
3. Review warnings (missing required fields, combed field overflow)
4. Select/deselect individual students
5. Click **Generate PDFs** -- progress bar tracks each file
6. Output folder opens automatically when complete

### Tab 4: About

Developer information and project links.

---

## Combed Field Detection

Combed fields are character-by-character boxes common in government forms (e.g. `[ J ][ o ][ h ][ n ]` for a name field). The analyser automatically detects three naming patterns:

| Pattern | Example | Detected As |
|---------|---------|-------------|
| Bracketed | `StudentNumber[0]`, `StudentNumber[1]`, ... | `StudentNumber` (combed) |
| Underscore | `Name_0`, `Name_1`, ... | `Name` (combed) |
| Sequential | `DOB0`, `DOB1`, ... | `DOB` (combed) |

The app groups these into a single logical field, splits input text character-by-character, and fills each box. Text longer than the field length is truncated automatically.

---

## Excel / CSV Requirements

Your spreadsheet needs column headers that match your PDF field names. Matching is **case-insensitive**, so `Surname` matches `surname`, `SURNAME`, etc.

Two columns are required for output filenames:
- `surname` (or matching variant)
- `First name` (or matching variant)

All other columns are matched to PDF fields by name. Unmatched columns are silently skipped.

**Supported formats:** `.xlsx`, `.xls`, `.csv` (UTF-8 and Latin-1 encoding auto-detected for CSV)

---

## Output

Generated PDFs are saved to a `Completed Applications` subfolder (configurable via the output folder browse button). Filename format:

```
FirstName_Surname_Evidence Application SchoolName Year.pdf
```

If a file already exists, a counter suffix is appended: `(1)`, `(2)`, etc. School name and year are sanitised to remove special characters.

---

## Configuration

Settings are stored in `~/Documents/VCAA_App/settings.json` and created automatically on first run:

```json
{
  "templates_directory": "~/Documents/VCAA_App/templates",
  "show_welcome": true,
  "auto_load_last_template": true,
  "combed_field_padding": false,
  "combed_field_align": "left",
  "school_name": "",
  "school_year": ""
}
```

Template configurations are saved as JSON files in the templates directory alongside their mapping spreadsheets.

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| pypdf | >= 4.0.0 | PDF form filling (read/write) |
| pandas | >= 2.0.0 | Excel/CSV data processing |
| openpyxl | >= 3.0.0 | Excel file creation for mapping export |
| PyMuPDF (fitz) | >= 1.23.0 | PDF analysis, field extraction, page rendering |
| Pillow | >= 10.0.0 | Image manipulation for visual preview |
| tkinter | (stdlib) | GUI framework |

---

## Project Structure

```
VCAA-PDF-Generator/
├── vcaa_pdf_generator_v2.py      # Main application (GUI + orchestration)
├── vcaa_models.py                # Data models (PDFField, TemplateConfig, AppSettings)
├── vcaa_pdf_analyzer.py          # PDF field extraction and combed detection
├── vcaa_visual_preview.py        # PDF page rendering and field highlighting
├── vcaa_combed_filler.py         # Character-by-character field filling
├── vcaa_theme.py                 # Centralised theme system (colours, fonts, styles)
├── vcaa_markdown_renderer.py     # Markdown-to-tkinter Text widget renderer
├── getting_started.md            # In-app Getting Started guide content
├── requirements.txt              # Python dependencies
├── Launch_BulkPDFGenerator.bat   # Windows launcher
├── Launch_BulkPDFGenerator.command  # macOS launcher
├── README.md                     # This file
├── ARCHITECTURE.md               # Technical architecture documentation
└── LICENSE                       # MIT licence
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: No module named 'tkinter'` | **macOS:** `brew install python-tk@3.xx` / **Windows:** re-run Python installer, tick "tcl/tk and IDLE" / **Linux:** `sudo apt install python3-tk` |
| `ModuleNotFoundError: No module named 'pypdf'` | Run `pip install -r requirements.txt` inside your virtual environment |
| Fields not filling in generated PDFs | Ensure Excel column headers match PDF field names (case-insensitive) |
| Visual preview not showing | Click **Analyse Fields** first in Tab 1 |
| Combed fields not splitting | Analyse the PDF in Tab 1 before generating in Tab 3 |
| Permission denied on Excel file | Close Excel/LibreOffice before running the app |
| Text truncated in combed boxes | Expected behaviour -- combed fields have fixed character limits |

---

## Developer

**Dave Armstrong**
Victorian Department of Education
[Dave.Armstrong@education.vic.gov.au](mailto:Dave.Armstrong@education.vic.gov.au)

Built with Python, tkinter, and Claude.

---

## Licence

MIT -- see [LICENSE](LICENSE) for details.
