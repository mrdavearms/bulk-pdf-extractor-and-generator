# Changelog

All notable changes to Bulk PDF Generator are documented here.

## [v2.7.5] — 2026-03-20

- **Fixed: macOS dialog input** — School name, template name, and sheet picker dialogs now accept keyboard input immediately on macOS Tahoe (26).
- **Faster macOS startup** — Eliminated redundant icon loading (1.3 MB image was opened 3 times, now once). ~24% faster startup.
- **Polished macOS DMG installer** — The disk image now opens with a professional background, drag-to-Applications arrow, and volume icon.
- **Ad-hoc code signing** — The macOS app is now signed, reducing Gatekeeper warnings.

## [v2.7.4] — 2026-03-20

- **Polished macOS DMG installer** — Professional background, drag-to-Applications arrow, and volume icon.
- **Ad-hoc code signing** — macOS app is now signed, reducing Gatekeeper warnings on subsequent versions.
- **Accurate macOS version metadata** — `CFBundleVersion` is now injected from the git tag at build time instead of being hardcoded.
- **Updated Gatekeeper instructions** — Release notes now cover both the classic right-click method (macOS 14 and earlier) and the System Settings path (macOS 15+).

## [v2.7.3] — 2026-03-20

- **Fixed: "Check for Updates" failing on Mac** — The update checker now works reliably on macOS. Previously it failed with an SSL certificate error because bundled Mac apps couldn't access the system certificate store.

## [v2.7.2] — 2026-03-19

- **Fixed: "Check for Updates" failing on Mac** — SSL certificate error fix for macOS (superseded by v2.7.3 with further fixes).

## [v2.7.1] — 2026-03-17

- **Fixed: crash on first launch** — Tab 2 (Map Fields) crashed immediately on opening due to a font configuration error. All Windows and macOS users on v2.7 were affected.

## [v2.7] — 2026-03-17

- **Check for Updates** — New button in the About tab lets you check for the latest version without leaving the app.
- **Fixed: crash on launch** on some school network accounts where the Documents folder is redirected to a network drive. The app now falls back to a local folder automatically.

## [v2.6] — 2026-03-15

- **Automated CI/CD** — Windows `.exe` and macOS `.app` are now built automatically via GitHub Actions. No more manual builds.
- **Dynamic version badge** — README version badge now auto-updates from the latest release.
- **Build status badge** — README shows live build status from GitHub Actions.

## [v2.5.6] — 2026-03-10

- About tab and Excel export updated to reference GitHub (migrated from GitLab).

## [v2.5.5] — 2026-03-10

- **Tab 2: Field Mapping Editor** — Tab 2 is now a live mapping editor replacing the previous disabled placeholder. Visual mapping grid, Auto-Map All, Clear All Mappings, live status indicators, persistent mappings saved to template JSON.
- **Tab 3 warning** — Validation now flags fields that have no mapping and won't auto-match any Excel column, with a prompt to fix them in Tab 2.

## [v2.5.4] — 2026-03-09

- **Security patch** — Upgrades pypdf 6.7.1 to 6.8.0, patching 4 Dependabot security advisories (infinite loop, RAM exhaustion, inefficient decoding).

## [v2.5.3] — 2026-03-09

- Windows release for v2.5 features.

## [v2.5] — 2026-03-09

- **Smart field type detection** — date/dob/birth fields auto-typed as Date.
- **Field Type Audit dialog** — Review and override field types after PDF analysis.
- **Date conversion** — Excel serial dates converted to DD/MM/YYYY (Australian format).
- **Number formatting** — Whole numbers strip trailing `.0`.
- **Combed field improvements** — Single-field detection, truncation handling.

## [v2.1] — 2026-02-22

- **Multi-sheet Excel support** — Sheet picker dialog for Excel files with multiple sheets.
- Atomic file writes for crash-safe settings and configs.
- LRU page cache for PDF preview.
- Fixed combed-field sequential detection and file-handle leak in preview renderer.

## [v2.0] — 2026-02-22

- Initial release of Bulk PDF Generator as a Windows executable.

[v2.7.5]: https://github.com/mrdavearms/bulk-pdf-extractor-and-generator/releases/tag/v2.7.5
[v2.7.4]: https://github.com/mrdavearms/bulk-pdf-extractor-and-generator/releases/tag/v2.7.4
[v2.7.3]: https://github.com/mrdavearms/bulk-pdf-extractor-and-generator/releases/tag/v2.7.3
[v2.7.2]: https://github.com/mrdavearms/bulk-pdf-extractor-and-generator/releases/tag/v2.7.2
[v2.7.1]: https://github.com/mrdavearms/bulk-pdf-extractor-and-generator/releases/tag/v2.7.1
[v2.7]: https://github.com/mrdavearms/bulk-pdf-extractor-and-generator/releases/tag/v2.7
[v2.6]: https://github.com/mrdavearms/bulk-pdf-extractor-and-generator/releases/tag/v2.6
[v2.5.6]: https://github.com/mrdavearms/bulk-pdf-extractor-and-generator/releases/tag/v2.5.6
[v2.5.5]: https://github.com/mrdavearms/bulk-pdf-extractor-and-generator/releases/tag/v2.5.5
[v2.5.4]: https://github.com/mrdavearms/bulk-pdf-extractor-and-generator/releases/tag/v2.5.4
[v2.5.3]: https://github.com/mrdavearms/bulk-pdf-extractor-and-generator/releases/tag/v2.5.3
[v2.5]: https://github.com/mrdavearms/bulk-pdf-extractor-and-generator/releases/tag/v2.5
[v2.1]: https://github.com/mrdavearms/bulk-pdf-extractor-and-generator/releases/tag/v2.1
[v2.0]: https://github.com/mrdavearms/bulk-pdf-extractor-and-generator/releases/tag/v2.0
