<!-- Release notes for the next tagged release.
     The GitHub Actions workflow reads this file and injects it into the
     release page. Write in plain English for teachers — no jargon. -->

- **New: tick-boxes, drop-downs and selection lists now fill in** — Until now the generator only filled plain text boxes. It now also ticks check-boxes, selects radio-button options, and chooses drop-down and list values from your spreadsheet. So forms with "Yes/No" tick-boxes or option lists (not just typed fields) come out fully completed.
- **New: friendly value check** — If a spreadsheet value doesn't match a form's tick-box or drop-down (for example "Victoria" where the form only allows "VIC"), the file is still created and a short note lists what to double-check — so nothing fails silently. Signature fields, which can't be auto-filled, are flagged too.
- **New: automatic update notice** — The app now quietly checks once a day when it starts and shows a small banner at the top **only** if a newer version is available, with a Download button. No pop-ups, and it stays out of your way if you're already up to date or offline. This means you'll actually hear about future improvements instead of having to check by hand.
- **Helpful: the field list now shows what each field accepts** — When you analyse a form, drop-down fields show their allowed options and tick-boxes show a hint, so it's clearer what to put in your spreadsheet column.
