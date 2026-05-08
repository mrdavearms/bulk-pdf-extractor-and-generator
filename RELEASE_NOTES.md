**Small reliability fix.** This is a patch release with one targeted fix — no new features and no changes to how you use the app. Safe to upgrade at any time.

- **Fixed: template PDF stayed "in use" by the app on Windows after Load Data** — On the **Generate PDFs** tab, after you clicked **Load Data**, Windows could keep treating your template PDF as "open by another program" — even though you were just using it as a source for field names. You may have noticed this if you tried to:
  - Open the same template in Adobe Acrobat or Adobe Reader and got a "file in use" warning,
  - Rename, move, or delete the template in File Explorer and got blocked by Windows,
  - Run a second copy of the app on the same template,
  - Email or upload the template while the app was still open.

  The file is now released back to Windows as soon as the app finishes reading the form fields, so all of the above just work normally. **macOS users were not affected** — macOS handles open file handles differently and never blocked these operations.

- **Behind the scenes** — the app's internal architecture documentation has been brought up to date with the threading and caching improvements that landed in v2.11. No user-facing change.

---

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
