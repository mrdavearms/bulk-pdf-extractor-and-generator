# VCAA PDF Generator - Enhanced Multi-Stage Application
## Technical Specification Document v2.0
**Date**: February 2026
**Project**: VCAA Evidence Application PDF Generator Enhancement

---

## Executive Summary

Transform the existing single-purpose PDF generator into a comprehensive multi-stage application that handles:
1. PDF template analysis and field extraction
2. Field mapping configuration
3. Batch PDF generation (existing functionality)

**Target Users**: School administrative staff working with multiple PDF form types
**Key Innovation**: Handle combed (character-by-character) fields automatically

---

## Architecture Overview

### Application Structure
```
┌─────────────────────────────────────────────────────────┐
│                  VCAA PDF Generator                     │
│                   Enhanced Edition                      │
├─────────────────────────────────────────────────────────┤
│  [Tab 1: Analyze]  [Tab 2: Map Fields]  [Tab 3: Generate]
├─────────────────────────────────────────────────────────┤
│                                                         │
│                   Tab Content Area                      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Technology Stack
- **GUI Framework**: tkinter (existing)
- **PDF Processing**: PyMuPDF (fitz) - NEW for field extraction
- **PDF Generation**: pypdf (existing)
- **Data Handling**: pandas, openpyxl (existing)
- **Image Generation**: Pillow (PIL) - NEW for visual previews
- **Config Storage**: JSON for templates, XLSX for field mappings

---

## Feature Specifications

## PHASE 1: Tab 1 - PDF Template Analysis

### 1.1 First-Run Experience

**Trigger**: No templates found in configured templates directory

**Welcome Dialog**:
```
┌─────────────────────────────────────────────────────────┐
│  Welcome to VCAA PDF Generator!                         │
│                                                         │
│  It looks like this is your first time.                │
│  Would you like to:                                     │
│                                                         │
│  ● Analyze a PDF template (recommended for new users)  │
│  ○ Load an existing template configuration             │
│  ○ Skip to PDF generation (I know what I'm doing)      │
│                                                         │
│                              [Continue]                 │
└─────────────────────────────────────────────────────────┘
```

**Behavior**:
- Option 1 → Opens Tab 1
- Option 2 → Opens file dialog for .json config
- Option 3 → Opens Tab 3 (existing functionality)

### 1.2 Tab 1 Layout

```
┌────────────────────────────────────────────────────────────┐
│  [1. Analyze Template] [2. Map Fields] [3. Generate PDFs]  │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  📁 Load Template                                          │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ PDF Template: [________________________] [Browse...] │ │
│  │                                                       │ │
│  │ Template Name: [Evidence Application 2026_______]    │ │
│  │ ○ Auto-name from PDF  ● Custom name                  │ │
│  │                                                       │ │
│  │ [Recent Templates ▼]                                 │ │
│  │   • VCAA Evidence Application 2026                   │ │
│  │   • Student Records Form 2025                        │ │
│  │   • Extension Request Template                       │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  [Analyze Fields]                                          │
│                                                            │
│  ───────── Analysis Results ─────────                      │
│                                                            │
│  Template: Evidence Application 2026                       │
│  Total Fields: 47  │  Pages: 3  │  Combed Fields: 3       │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ Field Name     │ Type         │ Page │ Length        │ │
│  ├──────────────────────────────────────────────────────┤ │
│  │ School_name    │ Text         │  1   │ Single        │ │
│  │ First_Name     │ Text-Combed  │  1   │ 10 chars      │ │
│  │ Surname        │ Text-Combed  │  1   │ 15 chars      │ │
│  │ VCAA_Number    │ Text         │  1   │ Single        │ │
│  │ DOB_Day        │ Text-Combed  │  1   │ 2 chars       │ │
│  │ DOB_Month      │ Text-Combed  │  1   │ 2 chars       │ │
│  │ DOB_Year       │ Text-Combed  │  1   │ 4 chars       │ │
│  │ Condition_1    │ Text         │  2   │ Single        │ │
│  │ ...            │              │      │               │ │
│  └──────────────────────────────────────────────────────┘ │
│                                   [↑↓ Scroll]             │
│                                                            │
│  ┌─ Field Preview ────────────────────────────────────┐   │
│  │  [Click a field above to preview its location]     │   │
│  │                                                     │   │
│  │  [Field highlight preview image appears here]      │   │
│  └─────────────────────────────────────────────────────┘  │
│                                                            │
│  [Export Mapping File (.xlsx)] [Save Template Config]     │
│                                                            │
│  Quick Actions:                                            │
│  [Skip to Generate PDFs →]                                │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### 1.3 Field Detection Algorithm

**PyMuPDF Implementation**:
```python
import fitz  # PyMuPDF

def analyze_pdf_fields(pdf_path):
    """
    Extract all form fields from PDF and detect combed fields.

    Returns:
        list of dicts: [
            {
                'field_name': 'First_Name',
                'field_type': 'Text-Combed',
                'page': 1,
                'length': 10,
                'is_combed': True,
                'combed_fields': ['First_Name[0]', 'First_Name[1]', ...],
                'rect': (x0, y0, x1, y1),  # For visual preview
                'current_value': ''
            },
            ...
        ]
    """
```

**Combed Field Detection Logic**:
1. Scan all widgets on all pages
2. Group fields by base name pattern: `Field_Name[N]`
3. If multiple fields match pattern → mark as combed
4. Store character count (length of group)
5. Create single entry with metadata about sub-fields

**Grouping Example**:
```
PDF contains: First_Name[0], First_Name[1], ... First_Name[9]

Output single entry:
{
    'field_name': 'First_Name',
    'field_type': 'Text-Combed',
    'length': 10,
    'combed_fields': ['First_Name[0]', ..., 'First_Name[9]']
}
```

### 1.4 Visual Field Preview

**Approach**: Static screenshot with annotations

**Implementation**:
1. When user clicks a field in the table:
   - Render the PDF page as PNG (300 DPI)
   - Draw red rectangle over field location using `rect` coordinates
   - Add label with field name
   - Display in preview panel

**Technical Details**:
```python
# PyMuPDF rendering
page = doc.load_page(field['page'] - 1)  # 0-indexed
pix = page.get_pixmap(dpi=300)
img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

# Draw highlight
draw = ImageDraw.Draw(img)
rect = field['rect']
draw.rectangle(rect, outline='red', width=3)
draw.text((rect[0], rect[1]-20), field['field_name'], fill='red')
```

**Performance Optimization**:
- Cache rendered pages (only render once per page)
- Use lower DPI (150) for preview, 300 for final export

### 1.5 Template Naming Dialog

**Trigger**: User clicks "Analyze Fields"

**Dialog**:
```
┌─────────────────────────────────────────────────────────┐
│  Template Name                                          │
│                                                         │
│  This configuration will be saved for reuse.            │
│                                                         │
│  Template Name:                                         │
│  [Evidence Application 2026_____________]               │
│                                                         │
│  Auto-generated from: Evidence_Application_2026.pdf     │
│                                                         │
│  ○ Use PDF filename (auto-clean)                        │
│  ● Custom name (editable above)                         │
│                                                         │
│  [Cancel]                        [Analyze & Save]       │
└─────────────────────────────────────────────────────────┘
```

**Auto-naming Rules**:
- Remove file extension: `.pdf`
- Replace underscores/hyphens with spaces: `_` → ` `, `-` → ` `
- Title case: `evidence application` → `Evidence Application`
- Keep year numbers: `2026` → `2026`

### 1.6 Configuration File Format

**File**: `{template_name}.json` stored in user-configured templates directory

**Structure**:
```json
{
  "template_name": "Evidence Application 2026",
  "pdf_filename": "Evidence_Application_2026.pdf",
  "pdf_path": "/Users/john/Desktop/Evidence_Application_2026.pdf",
  "created_date": "2026-02-17T14:30:00",
  "last_used": "2026-02-17T14:30:00",
  "total_fields": 47,
  "field_types": {
    "text": 42,
    "text_combed": 3,
    "checkbox": 0,
    "signature": 2
  },
  "mapping_file": "Evidence Application 2026_mapping.xlsx",
  "use_auto_matching": true,
  "critical_fields": ["surname", "First name", "VCAA student number"],
  "notes": "",
  "version": "2.0"
}
```

### 1.7 Export Mapping File (.xlsx)

**File**: `{template_name}_mapping.xlsx`

**Sheet 1: Field Mapping**

| PDF_Field_Name | Excel_Column_Name | Field_Type | Page | Required | Length | Notes |
|----------------|-------------------|------------|------|----------|--------|-------|
| School_name | School name | Text | 1 | Yes | - | Critical field |
| First_Name | First name | Text-Combed | 1 | Yes | 10 chars | Critical - used for filename |
| Surname | surname | Text-Combed | 1 | Yes | 15 chars | Critical - used for filename |
| VCAA_Number | VCAA student number | Text | 1 | Yes | - | Critical field |
| DOB_Day | day of birth | Text-Combed | 1 | No | 2 chars | Auto-format |
| DOB_Month | DOB month | Text-Combed | 1 | No | 2 chars | Auto-format |
| DOB_Year | dob year | Text-Combed | 1 | No | 4 chars | Auto-format |
| Provision_1 | Provision 1 | Text | 2 | No | - | |
| ... | ... | ... | ... | ... | ... | |

**Column Definitions**:
- **PDF_Field_Name**: Exact field name from PDF (or base name for combed fields)
- **Excel_Column_Name**: Pre-filled with smart guess (matches PDF name or uses common patterns)
- **Field_Type**: `Text`, `Text-Combed`, `Checkbox`, `Signature`
- **Page**: Page number (1-indexed)
- **Required**: `Yes` for critical fields, `No` otherwise
- **Length**: For combed fields: `N chars`, for others: `-`
- **Notes**: Auto-populated hints (e.g., "Used for filename", "Auto-format", "Critical field")

**Smart Guess Logic for Excel_Column_Name**:
1. If PDF field matches common patterns (e.g., `First_Name` → `First name`):
   - Convert to sentence case
   - Replace underscores with spaces
2. For known critical fields (surname, first name, student number):
   - Use exact Excel column names from existing app
3. Otherwise:
   - Use PDF field name as-is

**Sheet 2: Instructions (Read-Only)**

```
VCAA PDF Generator - Field Mapping Guide

HOW TO USE THIS FILE:
1. Review the "Excel_Column_Name" column
2. Update any column names to match YOUR Excel spreadsheet exactly
3. Mark "Required" fields as "Yes" if they must be filled
4. Save this file
5. Return to the app and load this mapping in Tab 2

IMPORTANT NOTES:
- Do NOT change the "PDF_Field_Name" column
- Column names are case-insensitive but must match spelling
- Combed fields will auto-split text (e.g., "John" → J-o-h-n)
- Leave Excel_Column_Name blank to skip a field

For help: See README.md
```

### 1.8 Settings Dialog (User-Configurable Templates Directory)

**Menu**: File → Settings (or Preferences on Mac)

**Dialog**:
```
┌─────────────────────────────────────────────────────────┐
│  Settings                                               │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Templates Library Location:                            │
│  [~/Documents/VCAA_App/templates___] [Browse Folder]   │
│                                                         │
│  ☑ Create folder if it doesn't exist                    │
│                                                         │
│  ───────────────────────────────────────────────────────│
│                                                         │
│  Default Behavior:                                      │
│  ☑ Show welcome screen on first launch                  │
│  ☑ Auto-load last used template                         │
│                                                         │
│  ───────────────────────────────────────────────────────│
│                                                         │
│  Advanced (Future):                                     │
│  ☐ Pad combed fields with spaces                        │
│  ☐ Right-align text in combed fields                    │
│                                                         │
│  [Restore Defaults]              [Cancel]  [Save]       │
└─────────────────────────────────────────────────────────┘
```

**Settings Storage**: `~/Documents/VCAA_App/settings.json`

```json
{
  "templates_directory": "/Users/john/Documents/VCAA_App/templates",
  "show_welcome": true,
  "auto_load_last_template": true,
  "last_template": "Evidence Application 2026",
  "combed_field_padding": false,
  "combed_field_align": "left"
}
```

---

## PHASE 2: Tab 2 - Field Mapping

### 2.1 Tab 2 Layout

```
┌────────────────────────────────────────────────────────────┐
│  [1. Analyze Template] [2. Map Fields] [3. Generate PDFs]  │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Field Mapping Configuration                               │
│                                                            │
│  Template: [Evidence Application 2026 ▼]  [Load Template] │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ ✓ Auto-matching enabled                              │ │
│  │   Excel columns must match PDF field names           │ │
│  │                                                       │ │
│  │   Want manual control?                               │ │
│  │   [Load Mapping File (.xlsx)] [Edit Mapping Below]  │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  ───────── Current Mapping ─────────                       │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ PDF Field       │ → │ Excel Column   │ Type │ Req'd │ │
│  ├──────────────────────────────────────────────────────┤ │
│  │ School_name     │ → │ School name    │ Text │  ✓    │ │
│  │ First_Name      │ → │ First name     │ Cmbd │  ✓    │ │
│  │ Surname         │ → │ surname        │ Cmbd │  ✓    │ │
│  │ VCAA_Number     │ → │ VCAA student # │ Text │  ✓    │ │
│  │ ...             │   │                │      │       │ │
│  └──────────────────────────────────────────────────────┘ │
│                                   [↑↓ Scroll]             │
│                                                            │
│  Validation:                                               │
│  ⚠️ 3 fields have no Excel column mapping                 │
│  ✓ All critical fields are mapped                         │
│                                                            │
│  [Save Mapping] [Export Updated .xlsx] [Reset to Default] │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### 2.2 Mapping Table Features

**Features**:
1. **Load Mapping File**: Opens file dialog to load `.xlsx` mapping file
2. **Edit Mapping Below**: Makes table cells editable (Excel column names only)
3. **Inline Editing**: Double-click Excel column cell to edit
4. **Validation**: Real-time checks for:
   - Unmapped critical fields
   - Duplicate Excel column assignments
   - Invalid field types
5. **Color Coding**:
   - Green: Mapped and validated
   - Yellow: Mapped but not required
   - Red: Critical field unmapped

### 2.3 Auto-Matching Logic (Default)

When user proceeds to Tab 3 without manual mapping:

```python
def auto_match_fields(pdf_fields, excel_columns):
    """
    Match Excel columns to PDF fields (case-insensitive).

    Priority:
    1. Exact match (case-insensitive)
    2. Remove underscores: First_Name → First Name
    3. Common aliases: surname → Surname, First name → First_Name
    """
    matches = {}

    # Create lowercase mapping
    excel_lower = {col.lower(): col for col in excel_columns}

    for pdf_field in pdf_fields:
        # Try exact match
        if pdf_field.lower() in excel_lower:
            matches[pdf_field] = excel_lower[pdf_field.lower()]
            continue

        # Try with spaces instead of underscores
        normalized = pdf_field.replace('_', ' ').lower()
        if normalized in excel_lower:
            matches[pdf_field] = excel_lower[normalized]
            continue

    return matches
```

---

## PHASE 3: Tab 3 - PDF Generation (Enhanced)

### 3.1 Tab 3 Layout (Existing + Template Selection)

**Changes to Existing Tab 3**:
1. Add template selection dropdown at top
2. If template has mapping → use it
3. If no mapping → fallback to auto-matching (current behavior)
4. Visual indicator showing which matching mode is active

```
┌────────────────────────────────────────────────────────────┐
│  [1. Analyze Template] [2. Map Fields] [3. Generate PDFs]  │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Template: [Evidence Application 2026 ▼] [Change Template]│
│  Matching: ✓ Using saved mapping (47/47 fields matched)   │
│                                                            │
│  ───────── File Selection ─────────                        │
│                                                            │
│  PDF Template: [Evidence_Application.pdf____] [Browse...] │
│  Excel Data:   [Student_Data.xlsx__________] [Browse...] │
│                                                            │
│  [Load & Preview Data]                                     │
│                                                            │
│  ───────── Validation Warnings ─────────                   │
│  [Existing validation display...]                          │
│                                                            │
│  ───────── Student Selection ─────────                     │
│  [Existing student table with checkboxes...]               │
│                                                            │
│  [Generate PDFs for X Students]                            │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### 3.2 Combed Field Filling Logic

**Implementation**:
```python
def fill_combed_field(writer, field_config, text_value):
    """
    Fill a combed field by splitting text into individual character boxes.

    Args:
        writer: PdfWriter object
        field_config: Dict with 'combed_fields' list and 'length'
        text_value: String to split (e.g., "John")
    """
    # Clean and prepare text
    text = str(text_value).strip()[:field_config['length']]  # Truncate if too long

    # Fill each character box
    for idx, char in enumerate(text):
        field_name = field_config['combed_fields'][idx]
        writer.update_page_form_field_values(page, {field_name: char})

    # Leave remaining boxes empty (no padding by default)
    # Future: Add padding option in settings
```

**Example**:
```
Excel: First name = "John"
PDF: First_Name[0] through First_Name[9]

Result:
First_Name[0] = "J"
First_Name[1] = "o"
First_Name[2] = "h"
First_Name[3] = "n"
First_Name[4] = ""
First_Name[5] = ""
...
First_Name[9] = ""
```

---

## Data Structures

### Template Configuration Object
```python
@dataclass
class TemplateConfig:
    template_name: str
    pdf_filename: str
    pdf_path: str
    created_date: datetime
    last_used: datetime
    total_fields: int
    field_types: dict
    mapping_file: str
    use_auto_matching: bool
    critical_fields: list
    notes: str
    version: str = "2.0"

    def to_json(self) -> dict:
        """Serialize to JSON for storage"""

    @classmethod
    def from_json(cls, data: dict) -> 'TemplateConfig':
        """Deserialize from JSON"""
```

### PDF Field Object
```python
@dataclass
class PDFField:
    field_name: str          # Base name (e.g., "First_Name")
    field_type: str          # "Text", "Text-Combed", "Checkbox", "Signature"
    page: int                # 1-indexed page number
    length: int              # For combed: character count, else None
    is_combed: bool          # True if field is combed
    combed_fields: list      # For combed: ["First_Name[0]", ...], else []
    rect: tuple              # (x0, y0, x1, y1) for visual preview
    current_value: str       # Current value in PDF (usually blank)
    is_critical: bool        # Marked as critical field
    excel_column: str        # Mapped Excel column name (or None)
```

---

## File Structure

```
VCAA_PDF_App/
├── vcaa_pdf_generator.py          # Main application (enhanced)
├── Launch_VCAA.command
├── README.md
├── TECHNICAL_SPEC.md              # This document
├── requirements.txt               # Updated dependencies
├── .gitignore
├── LICENSE
│
└── User-configured location (default: ~/Documents/VCAA_App/templates/):
    ├── settings.json                      # App settings
    │
    ├── Evidence Application 2026.json     # Template config
    ├── Evidence Application 2026_mapping.xlsx
    │
    ├── Student Records Form.json
    ├── Student Records Form_mapping.xlsx
    │
    └── .cache/                            # Cached page previews
        ├── Evidence_Application_2026_page1.png
        ├── Evidence_Application_2026_page2.png
        └── ...
```

---

## Dependencies

### Updated `requirements.txt`:
```
pypdf>=4.0.0
pandas>=2.0.0
openpyxl>=3.0.0
PyMuPDF>=1.23.0        # NEW: Field extraction & rendering
Pillow>=10.0.0         # NEW: Image manipulation for previews
```

---

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1)
- [ ] Refactor app to tabbed interface
- [ ] Implement settings dialog and persistence
- [ ] Create template directory structure
- [ ] Build TemplateConfig and PDFField data classes

### Phase 2: Tab 1 - Analysis (Week 2)
- [ ] Implement PDF field extraction with PyMuPDF
- [ ] Build combed field detection algorithm
- [ ] Create field analysis table UI
- [ ] Implement visual field preview (static screenshots)
- [ ] Build template naming dialog
- [ ] Create .xlsx export with smart column guessing

### Phase 3: Tab 2 - Mapping (Week 3)
- [ ] Build mapping table UI with inline editing
- [ ] Implement .xlsx loading and parsing
- [ ] Create validation logic
- [ ] Add save/export functionality

### Phase 4: Tab 3 - Enhanced Generation (Week 4)
- [ ] Integrate template selection dropdown
- [ ] Implement combed field filling logic
- [ ] Update auto-matching to use template configs
- [ ] Add matching mode indicators
- [ ] Test end-to-end workflow

### Phase 5: Polish & Testing (Week 5)
- [ ] First-run welcome experience
- [ ] Recent templates list
- [ ] Quick start button
- [ ] Error handling and edge cases
- [ ] User documentation updates
- [ ] Beta testing with real school forms

---

## Edge Cases & Error Handling

### 1. Combed Field Detection Failures
**Issue**: PDF has fields named `Name_1`, `Name_2` (sequential, not bracketed)
**Solution**: Also detect sequential numbering pattern, not just `[N]` pattern

### 2. Missing Excel Columns
**Issue**: User's Excel file doesn't have columns that mapping expects
**Solution**: Show warning dialog listing missing columns, offer to skip those fields

### 3. Combed Field Overflow
**Issue**: Excel value "Christopher" but combed field only has 10 boxes
**Solution**: Truncate to "Christophe" and show warning

### 4. Template Config Not Found
**Issue**: User loads .xlsx mapping but corresponding .json config is missing
**Solution**: Prompt to re-analyze the PDF to regenerate config

### 5. PDF Path Changed
**Issue**: Template config has `/old/path/Form.pdf` but file moved
**Solution**: Prompt user to relocate PDF, update config

### 6. Corrupted Mapping File
**Issue**: User edited .xlsx and broke structure
**Solution**: Validate on load, show specific errors, offer to export fresh template

---

## Testing Strategy

### Unit Tests
- [ ] Combed field detection algorithm (various naming patterns)
- [ ] Auto-matching logic (case variations, underscores, aliases)
- [ ] Text truncation for combed fields
- [ ] Template config serialization/deserialization

### Integration Tests
- [ ] Full workflow: Analyze → Map → Generate
- [ ] Skip mapping workflow (direct to generate)
- [ ] Multiple template switching
- [ ] Settings persistence

### User Acceptance Testing
- [ ] Test with 5 different school PDF forms
- [ ] Verify combed field handling across different PDFs
- [ ] Confirm visual previews are accurate
- [ ] Validate Excel export is user-friendly

---

## Future Enhancements (Post-v2.0)

### Version 2.1
- [ ] Advanced combed field settings (padding, alignment)
- [ ] Batch template analysis (multiple PDFs at once)
- [ ] Template sharing/export (package .json + .xlsx for colleagues)

### Version 2.2
- [ ] Cloud template library (shared school-wide)
- [ ] OCR for non-fillable PDFs
- [ ] PDF preview in Tab 3 (show sample filled form)

### Version 3.0
- [ ] Web-based version (Django/Flask backend)
- [ ] Multi-user template management
- [ ] Audit log (who generated which PDFs when)

---

## Success Metrics

### Technical
- Successfully analyze 95%+ of school PDF forms
- Combed field detection accuracy: 98%+
- App startup time: <2 seconds
- Field preview generation: <1 second per page

### User Experience
- First-time user completes full workflow in <10 minutes
- Template reuse saves 80%+ time on subsequent generations
- 90%+ of users prefer new multi-stage app over single-purpose tool

---

## Appendix A: Sample Code Snippets

### A.1 Combed Field Detection
```python
def detect_combed_fields(widgets):
    """
    Group combed fields by base name pattern.

    Supported patterns:
    - Field_Name[0], Field_Name[1], ...
    - FieldName_0, FieldName_1, ...
    """
    import re
    from collections import defaultdict

    # Group by base name
    groups = defaultdict(list)

    for widget in widgets:
        name = widget.field_name

        # Pattern 1: Field[N]
        match = re.match(r'^(.+?)\[(\d+)\]$', name)
        if match:
            base = match.group(1)
            index = int(match.group(2))
            groups[base].append((index, name, widget))
            continue

        # Pattern 2: Field_N
        match = re.match(r'^(.+?)_(\d+)$', name)
        if match:
            base = match.group(1)
            index = int(match.group(2))
            groups[base].append((index, name, widget))
            continue

        # Not combed - single field
        groups[name].append((0, name, widget))

    # Process groups
    result = []
    for base_name, items in groups.items():
        if len(items) > 1:
            # Combed field
            items.sort()  # Sort by index
            result.append({
                'field_name': base_name,
                'field_type': 'Text-Combed',
                'is_combed': True,
                'length': len(items),
                'combed_fields': [item[1] for item in items],
                'page': items[0][2].page_number + 1,  # 1-indexed
                'rect': items[0][2].rect,
            })
        else:
            # Single field
            widget = items[0][2]
            result.append({
                'field_name': base_name,
                'field_type': widget.field_type_string,
                'is_combed': False,
                'length': None,
                'combed_fields': [],
                'page': widget.page_number + 1,
                'rect': widget.rect,
            })

    return result
```

### A.2 Visual Field Preview
```python
def generate_field_preview(pdf_path, field, cache_dir):
    """
    Generate annotated preview image for a field.
    Uses cache to avoid re-rendering.
    """
    import os
    from PIL import Image, ImageDraw, ImageFont
    import fitz

    # Check cache
    cache_key = f"{os.path.basename(pdf_path)}_page{field['page']}.png"
    cache_path = os.path.join(cache_dir, cache_key)

    if not os.path.exists(cache_path):
        # Render page
        doc = fitz.open(pdf_path)
        page = doc.load_page(field['page'] - 1)
        pix = page.get_pixmap(dpi=150)  # Lower DPI for preview
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        img.save(cache_path)
        doc.close()
    else:
        img = Image.open(cache_path)

    # Annotate
    draw = ImageDraw.Draw(img)
    rect = field['rect']

    # Scale rect to image coordinates (PDF points → pixels at 150 DPI)
    scale = 150 / 72  # DPI / PDF points
    x0, y0, x1, y1 = [coord * scale for coord in rect]

    # Draw highlight
    draw.rectangle([x0, y0, x1, y1], outline='red', width=3)

    # Draw label
    label = field['field_name']
    if field['is_combed']:
        label += f" ({field['length']} chars)"

    draw.text((x0, y0 - 20), label, fill='red')

    return img
```

---

## Appendix B: User Documentation Outline

### Updated README.md Structure
1. **What's New in v2.0**
   - Multi-stage workflow
   - Template library
   - Combed field support

2. **Getting Started**
   - First-time setup
   - Welcome wizard walkthrough

3. **Tab 1: Analyzing Templates**
   - How to analyze a PDF
   - Understanding combed fields
   - Exporting mapping files

4. **Tab 2: Custom Field Mapping**
   - When to use custom mapping
   - Editing .xlsx files
   - Validation tips

5. **Tab 3: Generating PDFs**
   - Same as before (existing docs)

6. **Template Management**
   - Saving and loading templates
   - Sharing templates with colleagues
   - Settings configuration

7. **Troubleshooting**
   - Combed fields not detected
   - Mapping validation errors
   - PDF path issues

---

*End of Technical Specification v2.0*
