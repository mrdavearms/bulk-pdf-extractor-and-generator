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

- **Fixed: "Check for Updates" no longer freezes on macOS** — the result used to appear in a pop-up that could hide behind the main window, making the app seem stuck. It now reports right under the button: "✓ You're on the latest version", or an "Update available" message with a **Download** button. No pop-up, no freeze.
