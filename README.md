# VCAA Evidence Application PDF Generator
## Wangaratta High School - 2026

A cross-platform application (macOS & Windows) to batch-generate VCAA Special Examination Arrangements Evidence Application forms from Excel data.

---

## What's Included

- `vcaa_pdf_generator.py` — The main application
- `Launch_VCAA.command` — Double-click launcher for macOS
- `Launch_VCAA.bat` — Double-click launcher for Windows
- `README.md` — This file

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
pip install pypdf pandas openpyxl
```

**For Windows:**
Open PowerShell or Command Prompt and run:
```powershell
mkdir "$HOME\Documents\VCAA_App"
cd "$HOME\Documents\VCAA_App"
python -m venv venv
.\venv\Scripts\activate
pip install pypdf pandas openpyxl
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

Copy these files into your `VCAA_App` folder:
- `vcaa_pdf_generator.py`
- `Launch_VCAA.command` (macOS) or `Launch_VCAA.bat` (Windows)

### Step 4: Finalize Launcher (macOS only)

On macOS, you must make the launcher executable. In Terminal, run:
```bash
chmod +x ~/Documents/VCAA_App/Launch_VCAA.command
```

### Step 5: Easy Access (optional)

- **macOS:** Drag `Launch_VCAA.command` to your Dock.
- **Windows:** Right-click `Launch_VCAA.bat` → *Send to* → *Desktop (create shortcut)*.

---

## How to Use

### How to Launch

**For macOS:**
Double-click `Launch_VCAA.command` (or the Dock icon if you added it).

**For Windows:**
Double-click `Launch_VCAA.bat` (or the desktop shortcut if you created one).

### Using the App

1. **Select PDF Template** — Browse to your blank `Evidence_Application.pdf`
2. **Select Excel File** — Browse to your student data spreadsheet
3. **Click "Load & Preview Data"**
4. **Select students:**
   - All students are selected by default (☑)
   - Click any row to toggle selection
   - Use "Select All" or "Deselect All" buttons for bulk changes
5. **Click "Generate PDFs for X Students"**
6. **Find your files** in the "Completed Applications" folder (created next to your Excel file)

---

## Excel Spreadsheet Requirements

Your Excel file needs these column headers (spelling matters, but capitalisation doesn't):

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

---

## Output

Files are saved to: `[Excel folder]/Completed Applications/`

Filename format: `FirstName_Surname_Evidence Application Wangaratta High School 2026.pdf`

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Python not found" | Install Python from python.org |
| "No module named pypdf" | Run `pip install pypdf pandas openpyxl` in the venv |
| "No module named tkinter" | **Mac:** `brew install python-tk@3.14` <br> **Windows:** Re-run Python installer, check "tcl/tk" |
| "Permission denied" on Excel file | Close Excel before running the app |
| Fields not filling | Check column names match exactly |
| Dates show timestamps | The app handles this automatically |

---

## Notes

- The **Signature** field in the PDF cannot be filled automatically — sign manually after generation
- Always **close Excel** before running the app
- Dates are formatted as Australian DD/MM/YYYY automatically

---

*Created February 2026*
