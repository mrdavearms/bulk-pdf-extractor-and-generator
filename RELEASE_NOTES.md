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

## What's new in v2.9

### Major performance improvements — especially on Mac

- **Fixed: app freezing and lagging on macOS** — The app was nearly unusable on Mac, with tabs not responding, field selection freezing the window, and general sluggishness throughout. This release completely fixes those issues. Field previews now render in the background instead of freezing the window, and all bulk operations (Select All, loading data, switching tabs) are dramatically faster.

- **Smoother field preview** — Clicking through fields in the Analyse tab now feels instant. A fast preview appears immediately, then a high-quality version follows a moment later — no more waiting for each click.

- **Faster data loading** — Loading a spreadsheet with hundreds of rows no longer causes a visible pause. The "Select All" operation and field mapping panel both update much more efficiently.

- **Smoother scrolling and hover effects** — Mouse hover highlighting and scrolling in all lists and dialogs is now throttled to prevent unnecessary work, making the whole app feel more responsive.

- **Dialogs no longer flicker** — The School Setup, Template Name, and Field Type dialogs now appear cleanly without the brief flicker that was visible on macOS.
