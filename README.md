# VCAA Evidence Application PDF Generator v2.0
## Wangaratta High School - 2026

A powerful cross-platform application (macOS & Windows) to analyze PDF templates, map form fields, and batch-generate VCAA Special Examination Arrangements Evidence Application forms from Excel data.

**NEW in v2.0:**
- 🔍 **Visual field preview** - Click any field to see its exact location on the PDF
- 🔤 **Automatic combed field detection** - Character-by-character fields handled automatically
- 📊 **Template analysis** - Understand your PDF structure before generating
- 💾 **Template library** - Save and reuse configurations
- 🎯 **Smart Excel mapping** - Intelligent column name suggestions

---

## What's Included

**Main Application:**
- `vcaa_pdf_generator_v2.py` — Enhanced v2.0 application with tabbed interface
- `vcaa_pdf_generator.py` — Original v1.0 application (preserved)

**Supporting Modules:**
- `vcaa_models.py` — Data structures and settings
- `vcaa_pdf_analyzer.py` — PDF field extraction engine
- `vcaa_visual_preview.py` — Visual field preview generator
- `vcaa_combed_filler.py` — Character-by-character field filler

**Launchers:**
- `Launch_VCAA.command` — macOS launcher
- `Launch_VCAA.bat` — Windows launcher (if available)

**Documentation:**
- `README.md` — This file
- `TECHNICAL_SPEC.md` — Complete technical specification
- `PHASE_1_SUMMARY.md` — Phase 1 implementation details
- `PHASE_2_SUMMARY.md` — Phase 2 implementation details

---

## First-Time Setup (Do Once)

### Step 1: Create the app folder and virtual environment

**For macOS:**
Open Terminal and run:
```bash
mkdir -p ~/Documents/VCAA_App
cd ~/Documents/VCAA_App
python3 -m venv venv
source venv/bin/activate
pip install pypdf pandas openpyxl PyMuPDF Pillow
```

**For Windows:**
Open PowerShell or Command Prompt and run:
```powershell
mkdir "$HOME\Documents\VCAA_App"
cd "$HOME\Documents\VCAA_App"
python -m venv venv
.\venv\Scripts\activate
pip install pypdf pandas openpyxl PyMuPDF Pillow
```

### Step 2: Install tkinter (if needed)

**For macOS:**
If you get a tkinter error, run:
```bash
brew install python-tk@3.14
```
(Adjust the version number to match your Python version)

**For Windows:**
Tkinter is usually included with the standard Python installer from python.org. If it's missing, re-run the installer and ensure "tcl/tk and IDLE" is checked.

### Step 3: Copy the app files

Copy all Python files from this repository into your `VCAA_App` folder:
- `vcaa_pdf_generator_v2.py` (recommended)
- `vcaa_models.py`
- `vcaa_pdf_analyzer.py`
- `vcaa_visual_preview.py`
- `vcaa_combed_filler.py`
- `vcaa_pdf_generator.py` (original, optional)
- `Launch_VCAA.command` (macOS) or `Launch_VCAA.bat` (Windows)

### Step 4: Finalize Launcher (macOS only)

On macOS, make the launcher executable:
```bash
chmod +x ~/Documents/VCAA_App/Launch_VCAA.command
```

**Update the launcher** to use v2.0:
```bash
# Edit Launch_VCAA.command and change the last line to:
python vcaa_pdf_generator_v2.py
```

### Step 5: Easy Access (optional)

- **macOS:** Drag `Launch_VCAA.command` to your Dock
- **Windows:** Right-click `Launch_VCAA.bat` → *Send to* → *Desktop (create shortcut)*

---

## How to Use v2.0

### Launch the Application

**For macOS:**
Double-click `Launch_VCAA.command` (or the Dock icon)

**For Windows:**
Double-click `Launch_VCAA.bat` (or desktop shortcut)

**Or run directly:**
```bash
cd ~/Documents/VCAA_App
source venv/bin/activate  # macOS/Linux
# or
.\venv\Scripts\activate  # Windows
python vcaa_pdf_generator_v2.py
```

---

## v2.0 Three-Stage Workflow

### Tab 1: Analyze Template 🔍

**Purpose:** Understand your PDF structure

1. **Load PDF Template**
   - Click "Browse..." and select your `Evidence_Application.pdf`
   - Template name auto-suggested (or customize)
   - View recent templates

2. **Analyze Fields**
   - Click "Analyze Fields" button
   - See all 47 fields discovered
   - View breakdown: regular fields vs. combed (character-by-character) fields

3. **Visual Preview**
   - Click any field in the table
   - **See red highlight** showing exact field location on PDF
   - **Yellow label** displays field name + character count
   - Verify field positions before generating

4. **Export & Save**
   - Click "Export Mapping File (.xlsx)"
   - Excel file created with smart column name suggestions
   - Click "Save Template Config" to reuse later

**What are Combed Fields?**
Combed fields are character-by-character boxes (like `☐☐☐☐☐☐☐☐☐☐` for a 10-letter name). v2.0 **automatically detects** these and splits your text accordingly:
- "John" → J-o-h-n (fills 4 boxes, leaves 6 empty)
- "Christopher" → Christophe (truncates to 10 characters)

---

### Tab 2: Map Fields (Optional) 📊

**Purpose:** Manual field mapping (future feature)

Currently shows auto-matching status. Future versions will allow custom field-to-column mappings.

**Default Behavior:** Auto-matching enabled (Excel column names must match PDF field names, case-insensitive)

---

### Tab 3: Generate PDFs ⚡

**Purpose:** Batch-generate filled PDFs

1. **Select Template** (optional)
   - Choose from analyzed templates
   - Or load PDF + Excel directly

2. **Select Files**
   - **PDF Template:** Your blank form
   - **Excel Data File:** Student data spreadsheet

3. **Load & Preview Data**
   - Click "Load & Preview Data"
   - See validation warnings (missing required fields)
   - All students selected by default

4. **Select Students**
   - Click rows to toggle selection
   - Use "Select All" / "Deselect All" buttons

5. **Generate PDFs**
   - Click "Generate PDFs for X Students"
   - Progress bar shows status
   - Files saved to `Completed Applications/` folder

6. **Result**
   - Perfect PDFs with combed fields automatically filled!
   - Open folder to view generated files

---

## Excel Spreadsheet Requirements

Your Excel file needs these column headers (spelling matters, but capitalization doesn't):

### Required for filenames:
- `surname`
- `First name`

### Student details:
- `School name`
- `VCAA school code`
- `VCAA student number`
- `day of birth`
- `DOB month`
- `dob year`

### Condition information:
- `List the students conditions egdysgraphia anxiety`
- `how has each of these conditions or issues impacted`

### Provisions (up to 5):
- `Provision 1` through `Provision 5`
- `Date implemented 1` through `Date implemented 5`
- `How have EACH of these PROVISIONS assisted the student to access andor respond to Schoolbased Assessments andor examinations`
- `What evidence was used to make decisions regarding the provisions used by the student`
- `Any other relevant social and educational information to support the application optional`

### Staff details:
- `STAFF MEMBER NAME`
- `STAFF MEMBER Position`
- `SIGNATURE DAY`
- `SIGNATURE MONTH`
- `SIGNATURE YEAR`

**Note:** If your PDF has combed (character-by-character) fields, v2.0 will **automatically split** text like names and dates into individual boxes!

---

## Output

**Location:** `[Excel folder]/Completed Applications/`

**Filename format:** `FirstName_Surname_Evidence Application Wangaratta High School 2026.pdf`

**Features:**
- All fields filled automatically
- Combed fields split character-by-character
- Dates formatted as DD/MM/YYYY (Australian format)
- Names truncated if too long for boxes

---

## Advanced Features (v2.0)

### Template Library

Save analyzed templates for reuse:
1. Analyze PDF in Tab 1
2. Click "Save Template Config"
3. Next time: Select from "Recent Templates" dropdown
4. Skip re-analysis!

**Storage:** `~/Documents/VCAA_App/templates/`

### Visual Preview Caching

Field previews are cached for speed:
- First click: ~500-800ms (renders page)
- Subsequent clicks: ~50-100ms (from cache)
- Cache persists between sessions

**Cache location:** `~/Documents/VCAA_App/templates/.preview_cache/`

### Combed Field Auto-Detection

Supports 3 patterns:
- `Field[0]`, `Field[1]`, ... (bracketed)
- `Field_0`, `Field_1`, ... (underscore)
- `Field0`, `Field1`, ... (sequential)

**Behavior:**
- Left-aligned by default
- No space padding (future: configurable)
- Truncates if text too long

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Python not found" | Install Python from python.org |
| "No module named pypdf" | Run `pip install pypdf pandas openpyxl PyMuPDF Pillow` |
| "No module named tkinter" | **Mac:** `brew install python-tk@3.14` <br> **Windows:** Re-run Python installer, check "tcl/tk" |
| "No module named vcaa_models" | Copy all `.py` files to your VCAA_App folder |
| "Permission denied" on Excel | Close Excel before running the app |
| Fields not filling | Check column names match exactly (case-insensitive) |
| Preview not showing | Click "Analyze Fields" first in Tab 1 |
| Combed fields not splitting | Ensure you analyzed the PDF in Tab 1 before generating |
| Text truncated in boxes | Normal behavior - combed fields have character limits |

---

## Upgrading from v1.0

**v1.0 still works!** Both versions are included.

**To use v2.0:**
1. Install new dependencies: `pip install PyMuPDF Pillow`
2. Copy new `.py` files to your VCAA_App folder
3. Update launcher to run `vcaa_pdf_generator_v2.py`
4. Enjoy new features!

**Backward Compatibility:**
- v2.0's Tab 3 works exactly like v1.0
- Can skip Tab 1/2 and go straight to generation
- No changes to Excel format required

---

## Configuration

Settings stored in: `~/Documents/VCAA_App/settings.json`

```json
{
  "templates_directory": "/path/to/templates",
  "show_welcome": true,
  "auto_load_last_template": true,
  "combed_field_padding": false,
  "combed_field_align": "left"
}
```

**Future:** Settings dialog to change these from the app.

---

## Notes

- The **Signature** field in the PDF cannot be filled automatically — sign manually after generation
- Always **close Excel** before running the app
- Dates are formatted as Australian DD/MM/YYYY automatically
- Combed fields (character boxes) are filled automatically in v2.0
- Visual preview requires analyzing the PDF first (Tab 1)
- Template configurations save time on repeat use

---

## File Structure

```
~/Documents/VCAA_App/
├── venv/                          # Virtual environment
├── vcaa_pdf_generator_v2.py       # v2.0 application (recommended)
├── vcaa_pdf_generator.py          # v1.0 application (original)
├── vcaa_models.py                 # Data structures
├── vcaa_pdf_analyzer.py           # PDF analysis engine
├── vcaa_visual_preview.py         # Preview generator
├── vcaa_combed_filler.py          # Combed field filler
├── Launch_VCAA.command            # Launcher
├── settings.json                  # App settings (auto-created)
└── templates/                     # Template library (auto-created)
    ├── .preview_cache/            # Preview image cache
    ├── Evidence Application 2026.json
    └── Evidence Application 2026_mapping.xlsx
```

---

## What's New in v2.0

### Phase 1 Features:
- ✅ Tabbed interface (Analyze | Map Fields | Generate)
- ✅ PDF field extraction and analysis
- ✅ Combed field detection (3 pattern types)
- ✅ Template library with JSON configs
- ✅ Smart Excel column mapping export
- ✅ Recent templates dropdown
- ✅ First-run welcome dialog

### Phase 2 Features:
- ✅ Visual field preview with highlighting
- ✅ Click-to-preview interaction
- ✅ Two-tier caching (memory + disk)
- ✅ Combed field auto-splitting in generation
- ✅ Character-by-character box filling
- ✅ Automatic text truncation
- ✅ Date splitting (DD/MM/YYYY → boxes)

### Coming Soon (Phase 3+):
- Tab 2: Manual field mapping UI
- Overflow warnings before generation
- Settings dialog for preferences
- Cache management controls

---

## Credits

**Created:** February 2026
**For:** Wangaratta High School
**Version:** 2.0 (Enhanced Edition)

Built with:
- Python 3
- tkinter (GUI)
- pypdf (PDF generation)
- PyMuPDF (PDF analysis & rendering)
- pandas (Excel data processing)
- openpyxl (Excel file handling)
- Pillow (Image manipulation)

**Development:** Co-created with Claude Sonnet 4.5

---

## Support

For technical documentation, see:
- `TECHNICAL_SPEC.md` - Complete v2.0 specification
- `PHASE_1_SUMMARY.md` - Phase 1 implementation details
- `PHASE_2_SUMMARY.md` - Phase 2 implementation details

**Repository:** https://github.com/mrdavearms/VCAA-PDF-Generator

---

*VCAA Evidence Application PDF Generator v2.0 - Making form filling easier, one PDF at a time.*
