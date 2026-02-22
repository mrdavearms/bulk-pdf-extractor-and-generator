# Bulk PDF Generator v2.0

A desktop application that batch-fills PDF form templates from spreadsheet data — turning hours of manual data entry into a single click, so staff can focus on the work that actually matters.

Originally built to streamline VCAA Special Examination Arrangements Evidence Application forms, but works with **any** PDF form template.

> A Principal-developed app for educators and school leaders. Use with care and always review all generated outputs before use.

---

## ⬇️ Download for Windows

**No Python or technical setup required. Just download and run.**

### [Download Bulk PDF Generator.exe](https://github.com/mrdavearms/VCAA-PDF-Generator/releases/latest/download/Bulk%20PDF%20Generator.exe)

Or visit the [Releases page](https://github.com/mrdavearms/VCAA-PDF-Generator/releases) to see all versions.

---

### Step 1 — Download the file

Click the download link above. Your browser will save **`Bulk PDF Generator.exe`** — put it somewhere convenient, like your Desktop or a shared school drive.

---

### Step 2 — Run the app

Double-click **`Bulk PDF Generator.exe`**.

> **The first time you run it, Windows may show a security warning.** This is expected — see below for how to get past it.

---

### ⚠️ Windows Security Warning

Because this app is not commercially signed (signing certificates cost hundreds of dollars per year), Windows Defender SmartScreen will flag it the first time you run it. **The app is safe.** This is a standard false positive with self-distributed software.

**What you'll see:**

> *"Windows protected your PC"*
> *"Microsoft Defender SmartScreen prevented an unrecognised app from starting."*

**What to do:**

1. Click **"More info"** (the small link below the warning message)
2. A **"Run anyway"** button will appear at the bottom
3. Click **"Run anyway"**

You'll only need to do this **once**. After that, Windows remembers your choice and the app opens normally.

> **Note for school IT environments:** If your school's managed security software blocks the app entirely (with no "Run anyway" option), your IT administrator can whitelist the application or add an exclusion. The source code is fully open at [github.com/mrdavearms/VCAA-PDF-Generator](https://github.com/mrdavearms/VCAA-PDF-Generator) for inspection.

---

## 🎓 Try It With Sample Data

Not sure where to start? A set of sample files is included alongside the app so you can see exactly how it works before touching any of your own data.

### What's included

| File | What it is |
|------|-----------|
| `Sample_Template.pdf` | A blank PDF form with named fields ready to fill |
| `Sample_Data.xlsx` | A sample spreadsheet with four rows of fictional student data |
| `Sample_Output_1.pdf` – `Sample_Output_4.pdf` | Four pre-generated PDFs showing what the app produces |

### How to use them

1. Open the app and go to **Tab 3 — Generate PDFs**
2. Under **PDF Template**, browse to `Sample_Template.pdf`
3. Under **Excel / CSV Data File**, browse to `Sample_Data.xlsx`
4. Click **Load & Preview Data** — four rows will appear
5. Click **Generate PDFs**
6. Compare your output with the four sample output files to confirm everything is working correctly

Once you're comfortable with how it works, you're ready to use it with your own PDF template and real data.

---

## How to Use

The app has four tabs:

### Getting Started (Tab 0)

An in-app guide explaining how to prepare PDF templates — naming form fields, setting up combed fields, and getting your spreadsheet ready. Read this first if you're setting up a new template.

### Analyse Template (Tab 1)

1. Click **Browse** and select your blank PDF form
2. Click **Analyse Fields** — the app scans every form field
3. Click any field in the list to see it **highlighted in red** on the PDF preview
4. Click **Export Mapping File** to get a ready-made Excel template with the right column headers
5. Click **Save Template Config** to save your setup for next time

### Generate PDFs (Tab 3)

1. Select your PDF template and your filled-in Excel/CSV data file
2. Click **Load & Preview Data**

   > **If your Excel file has multiple sheets**, a dialog will appear asking which sheet contains your data. This is normal — especially if you're using a file exported by the app itself (which includes a *Data*, *Field Mapping*, and *Instructions* sheet). Simply select the sheet that holds your rows of student or applicant data and click **Load this sheet**. If you cancel the dialog, nothing is loaded.

3. You'll see a row for each person in your data
4. Select the rows you want (all are selected by default)
5. Click **Generate PDFs** — a progress bar shows each file being created
6. When finished, the output folder opens automatically

### About (Tab 4)

Developer info and contact details.

---

## What Are Combed Fields?

Government PDF forms often use character-by-character boxes for things like student numbers:

```
[ V ][ C ][ A ][ A ][ 1 ][ 2 ][ 3 ][ 4 ][ 5 ][ 6 ]
```

The app **automatically detects** these and splits your data correctly — you just put the full value in your spreadsheet and it handles the rest.

---

## Spreadsheet Requirements

Your Excel or CSV file needs column headers that **match your PDF field names** (case-insensitive — `Surname`, `SURNAME`, and `surname` all work).

Two columns are needed to name the output files:
- A column containing the person's **surname**
- A column containing their **first name**

All other columns are matched to PDF fields automatically. Unmatched columns are ignored.

**Supported formats:** `.xlsx`, `.xls`, `.csv`

### Multi-sheet Excel files

If your workbook contains more than one sheet, the app will ask you to pick which one holds your data before loading. This is particularly relevant if you're using an Excel file that was exported by the **Analyse Template** tab — that file contains three sheets (*Data*, *Field Mapping*, and *Instructions*) and only the *Data* sheet has the rows you want to fill.

> **Tip:** If you'd prefer to avoid the prompt entirely, save a copy of your data sheet as a separate single-sheet `.xlsx` or `.csv` file. Single-sheet files always load immediately without any confirmation step.

---

## Output Files

Generated PDFs are saved to a **`Completed Applications`** folder next to your data file (or a custom folder you choose). Filename format:

```
FirstName_Surname_Evidence Application SchoolName Year.pdf
```

If a file already exists, the app adds `(1)`, `(2)`, etc. rather than overwriting.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Windows shows "Windows protected your PC" | Click **More info** → **Run anyway** (see above) |
| IT security blocks the app entirely | Ask your IT administrator to whitelist it, or point them to the open source code |
| A "Select Sheet" dialog appeared when loading my Excel file | This is expected. Your file has multiple sheets — select the one containing your student/applicant data rows and click **Load this sheet** |
| I accidentally cancelled the sheet-picker dialog | Just click **Load & Preview Data** again to re-open it |
| Fields not filling in output PDFs | Check that your Excel column headers match the PDF field names (case-insensitive) |
| Visual preview not showing | Click **Analyse Fields** first in Tab 1 |
| Combed fields not splitting into boxes | Analyse the PDF in Tab 1 before generating in Tab 3 |
| "Permission denied" error on Excel file | Close the file in Excel before running the app |
| Text cut off in combed boxes | Expected — combed fields have a fixed number of characters |

---

## For Developers — Running from Source

If you want to run the Python source directly, or contribute to the project:

### Requirements

- Python 3.10+
- Packages: `pip install -r requirements.txt`
- tkinter (included with standard Python on Windows; on macOS: `brew install python-tk@3.xx`)

### Setup

```bash
git clone https://github.com/mrdavearms/VCAA-PDF-Generator.git
cd VCAA-PDF-Generator
python -m venv venv

# Windows
.\venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
python vcaa_pdf_generator_v2.py
```

### Building the Windows Executable

```bash
pip install pyinstaller
python -m PyInstaller BulkPDFGenerator.spec --clean
# Output: dist/Bulk PDF Generator.exe
```

Or just double-click **`build_windows.bat`**.

### Dependencies

| Package | Purpose |
|---------|---------|
| pypdf | PDF form filling |
| pandas | Excel/CSV data processing |
| openpyxl | Excel file creation |
| PyMuPDF (fitz) | PDF analysis, field extraction, page rendering |
| Pillow | Image manipulation for visual preview |
| tkinter | GUI framework (stdlib) |

### Project Structure

```
VCAA-PDF-Generator/
├── vcaa_pdf_generator_v2.py         # Main application
├── vcaa_models.py                   # Data models and persistence
├── vcaa_pdf_analyzer.py             # PDF field extraction engine
├── vcaa_visual_preview.py           # PDF page rendering + field highlighting
├── vcaa_combed_filler.py            # Character-by-character field filling
├── vcaa_theme.py                    # Theme system (colours, fonts, styles)
├── vcaa_markdown_renderer.py        # Markdown renderer for Getting Started tab
├── getting_started.md               # In-app guide content
├── icon.png / icon.ico              # Application icon
├── requirements.txt                 # Python dependencies
├── BulkPDFGenerator.spec            # PyInstaller build config
├── build_windows.bat                # Windows build script
├── Launch_BulkPDFGenerator.bat      # Windows launcher (from source)
├── Launch_BulkPDFGenerator.command  # macOS launcher (from source)
├── README.md                        # This file
└── ARCHITECTURE.md                  # Technical architecture documentation
```

---

## Developer

**Dave Armstrong**
A Principal-developed app for educators and school leaders.
[Dave.Armstrong@education.vic.gov.au](mailto:Dave.Armstrong@education.vic.gov.au)

---

## Licence

MIT — see [LICENSE](LICENSE) for details.
