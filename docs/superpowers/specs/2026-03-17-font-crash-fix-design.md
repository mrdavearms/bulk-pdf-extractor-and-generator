# Font Crash Fix & Hardening — Design Spec

**Goal:** Fix a v2.7 crash (`TypeError: font() got an unexpected keyword argument 'bold'`) in `setup_tab2_mapping`, audit all `font()` call sites, harden the `font()` helper against bad inputs, and add a regression test — then ship as v2.7.1.

**Architecture:** Three-layer fix: correct the broken call sites, add a runtime guard inside `theme.font()`, and cover the helper with unit tests. No structural changes to the codebase.

**Tech stack:** Python 3.10+, tkinter/ttkbootstrap, `unittest`.

---

## 1. Root Cause

`theme.font()` has the signature `def font(size: int, weight: str = '') -> tuple`. Three labels added in `setup_tab2_mapping` (lines 2147, 2149, 2151) mistakenly pass `bold=True` as a keyword argument. Python raises `TypeError` before the function body runs because `bold` is not a defined parameter.

The correct pattern, used at line 1349 and everywhere else in the file, is `font(9, 'bold')`.

---

## 2. Audit Results

| File | Call pattern | Count | Status |
|------|-------------|-------|--------|
| `pdf_generator.py` | `font(N)` | 18 | ✅ correct |
| `pdf_generator.py` | `font(11, 'bold')` | 1 | ✅ correct |
| `pdf_generator.py` | `font(9, bold=True)` | 3 | ❌ broken |
| `markdown_renderer.py` | imports `font`, never calls it | — | ✅ no issue |
| `visual_preview.py` | does not import `font` | — | ✅ no issue |

Only 3 broken call sites, all in `setup_tab2_mapping`.

---

## 3. Changes

### 3a. Fix broken call sites — `pdf_generator.py` lines 2147, 2149, 2151

**Before:**
```python
tk.Label(header_frame, text="PDF Field",    font=font(9, bold=True), ...)
tk.Label(header_frame, text="Excel Column", font=font(9, bold=True), ...)
tk.Label(header_frame, text="Status",       font=font(9, bold=True), ...)
```

**After:**
```python
tk.Label(header_frame, text="PDF Field",    font=font(9, 'bold'), ...)
tk.Label(header_frame, text="Excel Column", font=font(9, 'bold'), ...)
tk.Label(header_frame, text="Status",       font=font(9, 'bold'), ...)
```

### 3b. Runtime guard — `theme.py`

Add a `_VALID_WEIGHTS` set and validate on entry so future bad weight strings fail immediately with a clear message rather than silently producing bad tkinter font tuples.

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

Note: `bold=True` is a `TypeError` Python raises before the function body, so the guard cannot catch it — but the test suite documents it explicitly.

### 3c. New test file — `tests/test_theme_font.py`

Five tests, all pure unit tests (no tkinter display required):

| Test | Verifies |
|------|---------|
| `test_font_no_weight` | `font(10)` returns `(family, 10)` 2-tuple |
| `test_font_bold` | `font(10, 'bold')` returns `(family, 10, 'bold')` 3-tuple |
| `test_font_invalid_weight_raises` | `font(10, 'Bold')` raises `ValueError` |
| `test_font_invalid_kwarg_raises` | `font(9, bold=True)` raises `TypeError` |
| `test_mono_font` | `mono_font(10)` returns `(mono_family, 10)` 2-tuple |

---

## 4. Release

Tag as `v2.7.1` immediately after the fix lands on `main` to push a corrected build to Windows and macOS users via CI.

Release note summary: *"Fixed crash on first launch when Tab 2 (Map Fields) loads — Windows and macOS affected."*

---

## 5. Out of Scope

- Mypy / static type checking in CI (separate future task)
- `Literal` type hints on `weight` parameter (low value without mypy)
- Any other `theme.py` changes
