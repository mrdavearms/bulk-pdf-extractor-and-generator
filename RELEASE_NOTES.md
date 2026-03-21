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

## What's new in v2.8

### Now works with any PDF form — not just VCAA

- **Fully generic form support** — The app no longer assumes you're working with VCAA exam forms. It now works equally well with enrolment forms, leave applications, consent forms, compliance documents, or any other PDF that has fillable fields.

- **Smart field detection** — When you analyse a PDF, the app automatically recognises common identifier fields (Surname, First Name, Student Number, Employee ID, etc.) and marks them as "critical". These are used for the preview, validation warnings, and output filenames.

- **Improved Map Fields tab** — Tab 2 now shows a colour-coded guidance banner that tells you exactly what's happening: whether all fields matched, how many need manual mapping, or if you need to load a data file. Each field row also shows a helpful hint — "auto-matched", "manual", "⚠ will be blank", or "⚠ cryptic name — check visual preview".

- **Dynamic record preview** — The Generate tab preview now shows columns based on your actual form fields instead of hardcoded Surname / First Name / Student Number. This means the preview is useful for any form, not just student-related ones.

- **Smarter output filenames** — Generated PDFs are now named using your critical fields and template name (e.g. `John_Smith_Leave Application.pdf`) instead of the old hardcoded pattern. School name and year are still included if configured.

- **Template mappings remembered** — When you save a template with custom field mappings, the app tells you they've been saved. When you reload that template, you'll see a clear message that your mappings have been restored.

### Also included

- **Fixed: macOS dialog focus** — Dialogs (school name, template name, sheet picker) now regain keyboard focus correctly after the window grab on macOS Tahoe (26). Previously you had to click inside the field before typing.
- **Refreshed visual design** — Updated colour palette and spacing across the entire app for a cleaner, more modern look. Improved font detection with Inter support.
