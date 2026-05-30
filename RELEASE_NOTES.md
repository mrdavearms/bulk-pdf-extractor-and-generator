<!-- Release notes for the next tagged release.
     The GitHub Actions workflow reads this file and injects it into the
     release page. Write in plain English for teachers — no jargon.

     If this file is empty (just this comment), release notes are
     auto-generated from conventional commit messages. You only need
     to write here if you want custom wording for a release.

     Format: Markdown bullet list. Bold the headline, em-dash, then explain.
     Example:
       - **New feature name** — What it does and why teachers care.
       - **Fixed: bug description** — What was broken and how it's fixed.
-->

This release is a round of reliability and accuracy fixes from a thorough code review. No new features — just a smoother, more trustworthy app.

- **Fixed: stray ".0" on number fields** — A field set to *Number* now prints clean whole numbers (for example `45` instead of `45.0`).
- **Smarter field detection** — Fields that look alike but are actually separate (such as *Address line 1* and *Address line 2*) are no longer mistakenly merged into a single character-by-character field, so your data lands in the right boxes.
- **Safe exit while generating** — Closing the app midway through generating PDFs now stops cleanly, without leaving half-finished files behind.
- **More reliable template loading** — Opening a saved template always shows its full list of fields, including older template files.
