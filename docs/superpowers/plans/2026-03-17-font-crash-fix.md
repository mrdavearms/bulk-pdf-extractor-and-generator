# Font Crash Fix & Hardening Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix a crash on first launch in v2.7 (`TypeError: font() got an unexpected keyword argument 'bold'`), harden `theme.font()` with a runtime guard, and ship as v2.7.1.

**Architecture:** TDD — write the failing test first, then add the guard, then fix the 3 broken call sites. All tests are pure unit tests with no tkinter display required.

**Tech Stack:** Python 3.10+, `unittest`, `theme.font()` in `theme.py`, `pdf_generator.py`

---

## Chunk 1: Tests + Guard

### Task 1: Write the failing test for the runtime guard

**Files:**
- Create: `tests/test_theme_font.py`

- [ ] **Step 1: Create `tests/test_theme_font.py` with all 6 tests**

```python
"""Tests for theme.font() — regression guard for font() call patterns."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from theme import font, SYSTEM_FONTS


class TestFont(unittest.TestCase):

    def setUp(self):
        self.family = SYSTEM_FONTS['family']

    def test_font_no_weight(self):
        """font(10) returns a 2-tuple (family, size)."""
        result = font(10)
        self.assertEqual(result, (self.family, 10))

    def test_font_bold(self):
        """font(10, 'bold') returns a 3-tuple (family, size, 'bold')."""
        result = font(10, 'bold')
        self.assertEqual(result, (self.family, 10, 'bold'))

    def test_font_italic(self):
        """font(10, 'italic') returns a 3-tuple (family, size, 'italic')."""
        result = font(10, 'italic')
        self.assertEqual(result, (self.family, 10, 'italic'))

    def test_font_bold_italic(self):
        """font(10, 'bold italic') returns a 3-tuple (family, size, 'bold italic')."""
        result = font(10, 'bold italic')
        self.assertEqual(result, (self.family, 10, 'bold italic'))

    def test_font_invalid_weight_raises(self):
        """font(10, 'Bold') raises ValueError — wrong case is rejected."""
        with self.assertRaises(ValueError):
            font(10, 'Bold')

    def test_font_invalid_kwarg_raises(self):
        """font(9, bold=True) raises TypeError — documents the v2.7 crash pattern."""
        with self.assertRaises(TypeError):
            font(9, bold=True)  # type: ignore


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run the tests — expect 1 failure**

```bash
venv/bin/python -m pytest tests/test_theme_font.py -v
```

Expected output: 5 PASS, 1 FAIL
- `test_font_invalid_weight_raises` → FAIL (currently `font(10, 'Bold')` returns a tuple instead of raising)
- All others → PASS (including `test_font_invalid_kwarg_raises` — Python raises `TypeError` for unknown kwargs before the function body runs)

---

### Task 2: Add `_VALID_WEIGHTS` guard to `theme.py`

**Files:**
- Modify: `theme.py:104-107`

- [ ] **Step 3: Add the guard — replace the `font()` function body in `theme.py`**

Current code at line 104:
```python
def font(size: int, weight: str = '') -> tuple:
    if weight:
        return (SYSTEM_FONTS['family'], size, weight)
    return (SYSTEM_FONTS['family'], size)
```

Replace with (insert `_VALID_WEIGHTS` constant above, update function body):
```python
_VALID_WEIGHTS = {'', 'bold', 'italic', 'bold italic'}


def font(size: int, weight: str = '') -> tuple:
    if weight not in _VALID_WEIGHTS:
        raise ValueError(
            f"font() weight must be one of {sorted(_VALID_WEIGHTS)!r}, got {weight!r}"
        )
    if weight:
        return (SYSTEM_FONTS['family'], size, weight)
    return (SYSTEM_FONTS['family'], size)
```

- [ ] **Step 4: Run the tests — all 6 must pass**

```bash
venv/bin/python -m pytest tests/test_theme_font.py -v
```

Expected: 6 PASS, 0 FAIL, 0 ERROR

- [ ] **Step 5: Commit**

```bash
git add tests/test_theme_font.py theme.py
git commit -m "test: add font() unit tests and harden with _VALID_WEIGHTS guard"
```

---

## Chunk 2: Fix Call Sites + Release

### Task 3: Fix the 3 broken call sites in `pdf_generator.py`

**Files:**
- Modify: `pdf_generator.py:2147,2149,2151`

- [ ] **Step 6: Fix the 3 broken calls**

Find these three lines (all in `setup_tab2_mapping`, lines 2147–2151):
```python
tk.Label(header_frame, text="PDF Field",    font=font(9, bold=True),
tk.Label(header_frame, text="Excel Column", font=font(9, bold=True),
tk.Label(header_frame, text="Status",       font=font(9, bold=True),
```

Change `bold=True` → `'bold'` on each. The lines should read:
```python
tk.Label(header_frame, text="PDF Field",    font=font(9, 'bold'),
tk.Label(header_frame, text="Excel Column", font=font(9, 'bold'),
tk.Label(header_frame, text="Status",       font=font(9, 'bold'),
```

(The rest of each line — `fg=`, `bg=`, `width=`, `.pack(...)` — is unchanged.)

- [ ] **Step 7: Run the full test suite to verify no regressions**

```bash
venv/bin/python -m pytest tests/ -v
```

Expected: all tests pass (current suite: `test_generate_version.py`, `test_update_check.py`, `test_version_display.py`, `test_theme_font.py`). Some tests in `test_version_display.py` may skip in headless environments — that is expected and fine.

- [ ] **Step 8: Commit the call site fix**

```bash
git add pdf_generator.py
git commit -m "fix: replace font(9, bold=True) with font(9, 'bold') in setup_tab2_mapping

Fixes crash on first launch: TypeError: font() got an unexpected keyword
argument 'bold'. Three header labels in Tab 2 used the wrong keyword."
```

---

### Task 4: Tag and release v2.7.1

- [ ] **Step 9: Add v2.7.1 release notes to the CI workflow body**

Open `.github/workflows/release.yml`. Find this exact line in the `body:` field:
```
            <!-- Add release notes above this line before tagging -->
```

Insert ONE new line immediately above it (do not touch any surrounding content — the download links, headings, and `<details>` block must be left exactly as-is):
```
            - **Fixed: crash on first launch** — Tab 2 (Map Fields) crashed immediately on opening due to a font configuration error. All Windows and macOS users on v2.7 are affected.
```

After the edit that section should read:
```
            ## What's new in ${{ github.ref_name }}

            - **Fixed: crash on first launch** — Tab 2 (Map Fields) crashed immediately on opening due to a font configuration error. All Windows and macOS users on v2.7 are affected.

            <!-- Add release notes above this line before tagging -->
```

- [ ] **Step 10: Commit the workflow update**

```bash
git add .github/workflows/release.yml
git commit -m "docs: add v2.7.1 release notes to CI workflow body"
```

- [ ] **Step 11: Merge to main and push to GitHub to trigger CI**

```bash
git checkout main
git merge test --no-edit
git push github main
git checkout test
git push origin test
```

- [ ] **Step 12: Tag v2.7.1 and push the tag to trigger the release build**

```bash
git tag v2.7.1
git push github v2.7.1
git push origin v2.7.1
```

Expected: GitHub Actions starts two build jobs (Windows + macOS). Monitor at:
`https://github.com/mrdavearms/bulk-pdf-extractor-and-generator/actions`

- [ ] **Step 13: Update the live v2.7.1 release notes after CI completes**

Once the release is created by CI, update it to match the teacher-friendly format:

```bash
cat > /tmp/v2.7.1-notes.md << 'NOTES'
## ⬇ Download

### 🪟 Windows
**[Bulk.PDF.Generator.exe](https://github.com/mrdavearms/bulk-pdf-extractor-and-generator/releases/download/v2.7.1/Bulk.PDF.Generator.exe)** — Double-click to run. No installation needed.
> **Windows security prompt:** Windows may show a "Windows protected your PC" screen. This is normal for newly released apps. Click **More info → Run anyway** to proceed.

### 🍎 macOS
**[Bulk.PDF.Generator.macOS.zip](https://github.com/mrdavearms/bulk-pdf-extractor-and-generator/releases/download/v2.7.1/Bulk.PDF.Generator.macOS.zip)** — Unzip, then open the app.
> First time only: right-click the app → Open (macOS security prompt).

---

## What's new in v2.7.1

- **Fixed: crash on first launch** — Tab 2 (Map Fields) crashed immediately on opening due to a font configuration error. All Windows and macOS users on v2.7 are affected; please update.

<details>
<summary>Technical details</summary>

Three `tk.Label` calls in `setup_tab2_mapping` passed `bold=True` as a keyword
argument to `theme.font()`, which only accepts a positional `weight` string.
Python raised `TypeError` before the function body ran. Fixed by changing
`font(9, bold=True)` → `font(9, 'bold')`. Also added `_VALID_WEIGHTS` runtime
guard in `theme.font()` and 6 unit tests covering valid and invalid call patterns.

Built by GitHub Actions from commit `${{ github.sha }}`.

</details>
NOTES

gh release edit v2.7.1 \
  --repo mrdavearms/bulk-pdf-extractor-and-generator \
  --notes-file /tmp/v2.7.1-notes.md
```
