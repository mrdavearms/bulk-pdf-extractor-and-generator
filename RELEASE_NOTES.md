<!-- Release notes for the next tagged release.
     The GitHub Actions workflow reads this file and injects it into the
     release page. Write in plain English for teachers — no jargon.

     Format: Markdown bullet list. Bold the headline, em-dash, then explain.
     Example:
       - **New feature name** — What it does and why teachers care.
       - **Fixed: bug description** — What was broken and how it's fixed.

     After a release is published, clear everything above the instructions
     comment and start fresh for the next version.
-->

## What's new in v2.10

### Reliability and stability fixes

This release fixes a number of issues discovered during a full codebase audit. Most of these affect edge cases that teachers on school networks are most likely to encounter.

- **Fixed: "Failed to load data" error after loading a spreadsheet** — A bug caused the app to show a confusing error message every time you loaded an Excel file after analysing a template. Auto-mapping of fields now works correctly.

- **Fixed: loading a saved template could produce wrong output** — If you loaded a saved template on a fresh launch without re-analysing, the app would silently skip your saved field mappings, data types, and combed field settings. Templates now restore all settings automatically.

- **Fixed: date fields showing numbers instead of dates** — Date columns stored as serial numbers in Excel (e.g. "45000" instead of "17/03/2023") were being written as-is into the PDF. They are now correctly converted to DD/MM/YYYY format.

- **Fixed: app crashing on startup on some school networks** — On machines where both the Documents folder and the local app data folder are unavailable (common with GPO-locked school networks), the app would crash before any window appeared. It now falls back gracefully.

- **Fixed: Excel file stays locked after loading** — On Windows, the Excel file remained locked after you loaded it, preventing you from editing or re-saving it until you restarted the app. The file is now released immediately after loading.

- **Fixed: combed fields crashing on certain PDFs** — Combed fields where the PDF didn't report a character limit could crash the app. These are now handled safely.

- **Fixed: settings corruption with non-ASCII school names** — If your school name contained accented or special characters, it could become garbled after restarting the app on Windows. Settings are now always read and written as UTF-8.

- **Fixed: preview cache showing wrong PDF** — If you switched between two PDF templates with the same number of pages, the preview could show pages from the previous template. Each PDF now has its own cache.

- **Fixed: Windows download link on GitHub Releases** — The download link for the Windows .exe in previous releases could return a 404 error. This is now fixed.

- **Improved: template file and settings resilience** — Saved templates and settings files are now more resilient to file system errors on network drives. Temporary files are cleaned up properly if a save is interrupted.

### Performance

- **10–50× faster batch generation** — The PDF template is now read once per run instead of once per student. Generating 200 PDFs used to re-parse the template 200 times. Now it parses it once.

### Additional bug fixes (critical audit)

- **Fixed: student IDs with leading zeros corrupted in CSV files** — When loading a CSV spreadsheet, student IDs like "0123456" were silently converted to "123456". CSV files now load with full string preservation, matching the behaviour of Excel files.

- **Fixed: date columns not converting in all generation paths** — Date fields (e.g. DOB, expiry dates) stored as Excel serial numbers only converted to DD/MM/YYYY format when a template had been fully analysed first. They now convert correctly in all cases.

- **Fixed: generation errors shown only after all PDFs produced** — If some rows failed (e.g. a missing field value caused an error), the app would silently continue and only report the final count. The completion dialog now lists which rows failed and why (up to 20 shown), and all errors are saved to `app.log` in your data folder.

- **Fixed: preview could crash on some screen resolutions** — The field preview was querying screen dimensions from a background thread, which is not safe in tkinter. This could cause silent crashes on certain screen configurations. Fixed by moving the screen size query to the main thread.

- **Fixed: Select All / Deselect All buttons could silently stop working** — On some ttkbootstrap theme configurations, the buttons could hit an internal error and stop responding without any message. They now handle this gracefully.

- **Improved: preview disk cache capped at 200MB** — The app now automatically trims the oldest cached preview images on startup to stay within a 200MB budget. This prevents quota alerts on school networks with redirected Documents folders.
