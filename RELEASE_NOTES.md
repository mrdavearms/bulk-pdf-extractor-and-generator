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

- **Fixed: macOS dialog input** — School name, template name, and sheet picker dialogs now accept keyboard input immediately on macOS Tahoe (26).
- **Faster macOS startup** — Eliminated redundant icon loading. ~24% faster startup.
- **Polished macOS DMG installer** — The disk image now opens with a professional background, drag-to-Applications arrow, and volume icon.
- **Ad-hoc code signing** — The macOS app is now signed, reducing Gatekeeper warnings.
