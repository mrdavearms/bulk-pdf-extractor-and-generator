# VCAA Evidence Application PDF Generator
## Wangaratta High School - 2026

A Mac application to batch-generate VCAA Special Examination Arrangements Evidence Application forms from Excel data.

---

## What's Included

- `vcaa_pdf_generator.py` — The main application
- `Launch_VCAA.command` — Double-click launcher for easy access
- `README.md` — This file

---

## First-Time Setup (Do Once)

### Step 1: Create the app folder and virtual environment

Open Terminal and run these commands one at a time:

```
mkdir -p ~/Documents/VCAA_App
cd ~/Documents/VCAA_App
python3 -m venv venv
source venv/bin/activate
pip install pypdf pandas openpyxl
```

### Step 2: Install tkinter (if needed)

If you get a tkinter error, run:

```
brew install python-tk@3.14
```

(Adjust the version number to match your Python version)

### Step 3: Copy the app files

Copy these files into `~/Documents/VCAA_App/`:
- `vcaa_pdf_generator.py`
- `Launch_VCAA.command`

### Step 4: Make the launcher executable

In Terminal, run:

```
chmod +x ~/Documents/VCAA_App/Launch_VCAA.command
```

### Step 5: Add to Dock (optional)

1. Open Finder → Documents → VCAA_App
2. Drag `Launch_VCAA.command` to your Dock

---

## How to Use

### Starting the App

Double-click `Launch_VCAA.command` (or the Dock icon if you added it)

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
| "No module named tkinter" | Run `brew install python-tk@3.14` |
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
