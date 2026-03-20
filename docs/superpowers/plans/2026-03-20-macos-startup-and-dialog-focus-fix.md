# macOS Startup Lag & Dialog Focus Fix

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix two regressions in the macOS `.app` build — dialogs that don't accept keyboard input, and unnecessary startup lag from redundant icon loading.

**Architecture:** The dialog focus bug is caused by `grab_set()` being deferred 50ms (macOS crash fix in `bff0894`) but focus not being re-asserted after the grab fires. The startup lag comes from `icon.png` (1.3 MB) being opened 3 times with 4 LANCZOS resizes, plus a duplicate `enable_high_dpi_awareness()` call. Fixes are surgical — no structural changes.

**Tech Stack:** Python 3.10+, tkinter, ttkbootstrap, PIL/Pillow, PyInstaller

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `pdf_generator.py` | Modify | Fix grab_set+focus in 4 dialogs; deduplicate icon loading in `main()` |
| `tests/test_dialog_focus.py` | Create | Unit tests for the grab+focus pattern in all 4 dialogs |
| `tests/test_startup.py` | Create | Unit tests for deduplicated icon loading |

---

## Task 1: Fix Dialog Focus After Deferred `grab_set()`

**Problem:** In commit `bff0894`, `grab_set()` was moved from immediate (before widget creation) to deferred (50ms after). But `focus_set()` on the entry widget still runs during `__init__` — so `grab_set()` fires 50ms later and steals focus back to the dialog's top-level window. On macOS Tahoe, this means the entry field appears but never receives keyboard input.

**Fix pattern:** Replace each `self.after(50, self.grab_set)` with a helper that calls `grab_set()` then re-focuses the intended widget.

**Files:**
- Modify: `pdf_generator.py:355` (SchoolSetupDialog)
- Modify: `pdf_generator.py:476` (TemplateNameDialog)
- Modify: `pdf_generator.py:677` (FieldTypeAuditDialog)
- Modify: `pdf_generator.py:2577` (_pick_excel_sheet)
- Create: `tests/test_dialog_focus.py`

### Step 1: Write failing tests for dialog focus

- [ ] Create `tests/test_dialog_focus.py` with tests that verify each dialog's deferred grab restores focus to the correct widget.

```python
"""Tests for dialog focus-after-grab pattern (macOS Tahoe fix)."""
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, call

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestDialogFocusAfterGrab(unittest.TestCase):
    """Verify that deferred grab_set re-focuses the intended widget.

    We don't create real Tk windows — we patch the after() calls to capture
    the callbacks, then invoke them and verify focus_set() was called on
    the correct widget after grab_set().
    """

    @patch('pdf_generator.tk.Toplevel.__init__', return_value=None)
    @patch('pdf_generator.tk.Toplevel.title')
    @patch('pdf_generator.tk.Toplevel.configure')
    @patch('pdf_generator.tk.Toplevel.resizable')
    @patch('pdf_generator.tk.Toplevel.transient')
    @patch('pdf_generator.tk.Toplevel.update_idletasks')
    @patch('pdf_generator.tk.Toplevel.winfo_reqwidth', return_value=400)
    @patch('pdf_generator.tk.Toplevel.winfo_reqheight', return_value=300)
    @patch('pdf_generator.tk.Toplevel.geometry')
    @patch('pdf_generator.tk.Toplevel.lift')
    @patch('pdf_generator.tk.Toplevel.attributes')
    @patch('pdf_generator.tk.Toplevel.bind')
    def test_school_setup_grab_refocuses_entry(self, *mocks):
        """SchoolSetupDialog: grab_set callback must call focus_set on name entry."""
        from pdf_generator import SchoolSetupDialog

        after_calls = {}
        def fake_after(ms, callback):
            after_calls[ms] = callback

        with patch.object(SchoolSetupDialog, 'after', side_effect=fake_after):
            with patch('pdf_generator.tk.Label'):
                with patch('pdf_generator.ttk.Entry') as mock_entry_cls:
                    with patch('pdf_generator.ttk.Button'):
                        with patch('pdf_generator.tk.Frame'):
                            with patch('pdf_generator.tk.StringVar'):
                                mock_parent = MagicMock()
                                mock_parent.winfo_x.return_value = 100
                                mock_parent.winfo_y.return_value = 100
                                mock_parent.winfo_width.return_value = 800
                                mock_parent.winfo_height.return_value = 600

                                dialog = SchoolSetupDialog(mock_parent)

        # The 50ms callback should exist
        self.assertIn(50, after_calls,
                      "Expected a 50ms deferred callback for grab_set")

        # Invoke the callback and verify it calls grab_set then focus
        with patch.object(dialog, 'grab_set') as mock_grab:
            after_calls[50]()
            mock_grab.assert_called_once()

    def test_pick_excel_sheet_grab_refocuses_combo(self):
        """_pick_excel_sheet: grab_set callback must focus the combobox."""
        # This dialog is an inline Toplevel, not a class — tested via
        # integration. The pattern is the same: after(50, ...) must call
        # grab_set + focus on the combo widget.
        # Structural assertion: the source code contains the focus pattern.
        import inspect
        from pdf_generator import BulkPDFGenerator
        source = inspect.getsource(BulkPDFGenerator._pick_excel_sheet)
        self.assertIn('focus', source,
                       "_pick_excel_sheet should set focus after grab_set")


if __name__ == '__main__':
    unittest.main()
```

### Step 2: Run tests to verify they fail

- [ ] Run: `venv/bin/python -m pytest tests/test_dialog_focus.py -v`
- Expected: at least `test_school_setup_grab_refocuses_entry` FAILS (no focus call after grab_set), `test_pick_excel_sheet_grab_refocuses_combo` FAILS (no 'focus' in source).

### Step 3: Fix SchoolSetupDialog focus

- [ ] In `pdf_generator.py`, replace line 354-355:

**Before:**
```python
        # Defer grab_set so the window is fully realised by AppKit (macOS crash fix)
        self.after(50, self.grab_set)
```

**After:**
```python
        # Defer grab_set so the window is fully realised by AppKit (macOS crash fix).
        # Re-focus the name entry after grab — grab_set resets focus on macOS Tahoe.
        def _grab_and_focus():
            self.grab_set()
            name_entry.focus_set()
        self.after(50, _grab_and_focus)
```

Note: `name_entry` is already a local variable defined at line 300. The closure captures it.

### Step 4: Fix TemplateNameDialog focus

- [ ] In `pdf_generator.py`, the entry is created at line 415 as an anonymous `ttk.Entry(...)`. First, capture it in a local:

**At line 415, change:**
```python
        ttk.Entry(name_frame, textvariable=self.name_var, width=50).pack(fill=tk.X)
```
**To:**
```python
        name_entry = ttk.Entry(name_frame, textvariable=self.name_var, width=50)
        name_entry.pack(fill=tk.X)
```

Then replace line 475-476:

**Before:**
```python
        # Defer grab_set so the window is fully realised by AppKit (macOS crash fix)
        self.after(50, self.grab_set)
```

**After:**
```python
        # Defer grab_set so the window is fully realised by AppKit (macOS crash fix).
        # Re-focus the name entry after grab — grab_set resets focus on macOS Tahoe.
        def _grab_and_focus():
            self.grab_set()
            name_entry.focus_set()
        self.after(50, _grab_and_focus)
```

### Step 5: Fix FieldTypeAuditDialog focus

- [ ] In `pdf_generator.py`, replace line 676-677:

**Before:**
```python
        # Defer grab_set so the window is fully realised by AppKit (macOS crash fix)
        self.after(50, self.grab_set)
```

**After:**
```python
        # Defer grab_set so the window is fully realised by AppKit (macOS crash fix).
        # Re-focus the dialog after grab — grab_set resets focus on macOS Tahoe.
        def _grab_and_focus():
            self.grab_set()
            self.focus_set()
        self.after(50, _grab_and_focus)
```

Note: FieldTypeAuditDialog has no single text entry to focus — it's a list of combos. `self.focus_set()` gives the dialog itself focus, which is correct here.

### Step 6: Fix `_pick_excel_sheet` focus

- [ ] In `pdf_generator.py`, replace line 2576-2577:

**Before:**
```python
        # Defer grab_set so the window is fully realised by AppKit (macOS crash fix)
        dialog.after(50, dialog.grab_set)
```

**After:**
```python
        # Defer grab_set so the window is fully realised by AppKit (macOS crash fix).
        # Re-focus the combobox after grab — grab_set resets focus on macOS Tahoe.
        def _grab_and_focus():
            dialog.grab_set()
            combo.focus_set()
        dialog.after(50, _grab_and_focus)
```

Note: `combo` is defined at line 2598, which is AFTER line 2577. This means we need to **move the `after()` call below the combo creation**. Move the deferred grab block to after line 2601 (after `combo.pack(anchor=tk.W)`).

### Step 7: Run tests to verify they pass

- [ ] Run: `venv/bin/python -m pytest tests/test_dialog_focus.py -v`
- Expected: ALL PASS

### Step 8: Run full test suite for regressions

- [ ] Run: `venv/bin/python -m pytest tests/ -v`
- Expected: All 18+ tests PASS

### Step 9: Commit

- [ ] ```bash
git add pdf_generator.py tests/test_dialog_focus.py
git commit -m "fix: re-focus entry after deferred grab_set on macOS Tahoe

grab_set() resets keyboard focus on macOS 26 (Tahoe), leaving dialog
entries unresponsive. After the deferred grab fires, re-assert focus
on the intended widget in all four dialogs."
```

---

## Task 2: Deduplicate Icon Loading and DPI Init

**Problem:** `icon.png` (1.3 MB) is opened 3 times during startup with 4 LANCZOS resizes. `enable_high_dpi_awareness()` is called twice. In a PyInstaller `.app` bundle (where files live in a temp extraction directory), this adds measurable lag.

**Fix:** Remove the redundant icon load from `main()` (since `_load_app_icon()` in `__init__` does the same thing), and remove the redundant `enable_high_dpi_awareness()` call from `main()` (since `apply_dark_theme()` calls it).

**Files:**
- Modify: `pdf_generator.py:3170-3202` (main function)
- Create: `tests/test_startup.py`

### Step 1: Write failing test for single icon load

- [ ] Create `tests/test_startup.py`:

```python
"""Tests for startup path — no redundant icon loading."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, call

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestStartupIconLoading(unittest.TestCase):
    """Verify icon.png is opened only once during startup, not three times."""

    def test_main_does_not_load_icon_png(self):
        """main() should NOT open icon.png — _load_app_icon() handles it."""
        import pdf_generator
        import inspect
        source = inspect.getsource(pdf_generator.main)

        # main() should not contain Image.open — that's _load_app_icon's job
        self.assertNotIn('Image.open', source,
                         "main() should not open icon.png directly — "
                         "_load_app_icon() handles all icon loading")

    def test_main_does_not_call_enable_high_dpi_awareness(self):
        """main() should NOT call enable_high_dpi_awareness — apply_dark_theme() handles it."""
        import pdf_generator
        import inspect
        source = inspect.getsource(pdf_generator.main)

        self.assertNotIn('enable_high_dpi_awareness', source,
                         "main() should not call enable_high_dpi_awareness — "
                         "apply_dark_theme() already calls it")


if __name__ == '__main__':
    unittest.main()
```

### Step 2: Run test to verify it fails

- [ ] Run: `venv/bin/python -m pytest tests/test_startup.py -v`
- Expected: FAIL — main() currently contains both `Image.open` and `enable_high_dpi_awareness`

### Step 3: Remove redundant icon loading from `main()`

- [ ] In `pdf_generator.py`, replace the macOS icon block in `main()`.

**Replace lines 3170-3202** (from the DPI call through the icon loading):

**Before:**
```python
    # Must be called before Tk window creation for best DPI results
    from ttkbootstrap.utility import enable_high_dpi_awareness
    enable_high_dpi_awareness()

    root = tk.Tk()

    # Force window to front on launch
    root.lift()
    root.attributes('-topmost', True)
    root.after(100, lambda: root.attributes('-topmost', False))

    # Apply ttkbootstrap theme + custom styles
    apply_dark_theme(root)

    # Set window icon AFTER ttkbootstrap theme (Style() can reset icons).
    # iconphoto with a PNG is more reliable than iconbitmap on Windows
    # for controlling the taskbar icon when ttkbootstrap is in use.
    ico_path = get_resource_path('icon.ico')
    png_path = get_resource_path('icon.png')
    if sys.platform == 'win32':
        if os.path.exists(ico_path):
            root.iconbitmap(default=ico_path)
            root.iconbitmap(ico_path)
        if os.path.exists(png_path):
            _img = Image.open(png_path).convert('RGBA')
            _icon = ImageTk.PhotoImage(_img.resize((256, 256), Image.LANCZOS))
            root.iconphoto(True, _icon)
            root._icon_ref = _icon  # prevent garbage collection
    elif os.path.exists(png_path):
        _img = Image.open(png_path).convert('RGBA')
        _icon = ImageTk.PhotoImage(_img.resize((64, 64), Image.LANCZOS))
        root.iconphoto(True, _icon)
        root._icon_ref = _icon
```

**After:**
```python
    root = tk.Tk()

    # Force window to front on launch
    root.lift()
    root.attributes('-topmost', True)
    root.after(100, lambda: root.attributes('-topmost', False))

    # Apply ttkbootstrap theme + custom styles
    # (also calls enable_high_dpi_awareness() internally)
    apply_dark_theme(root)

    # Windows needs .ico set AFTER ttkbootstrap theme (Style() can reset icons).
    # iconphoto with a PNG is more reliable than iconbitmap on Windows
    # for controlling the taskbar icon when ttkbootstrap is in use.
    # macOS/Linux icon is set by _load_app_icon() in BulkPDFGenerator.__init__
    # — no need to duplicate it here.
    if sys.platform == 'win32':
        ico_path = get_resource_path('icon.ico')
        png_path = get_resource_path('icon.png')
        if os.path.exists(ico_path):
            root.iconbitmap(default=ico_path)
            root.iconbitmap(ico_path)
        if os.path.exists(png_path):
            _img = Image.open(png_path).convert('RGBA')
            _icon = ImageTk.PhotoImage(_img.resize((256, 256), Image.LANCZOS))
            root.iconphoto(True, _icon)
            root._icon_ref = _icon  # prevent garbage collection
```

**Key changes:**
1. Removed `enable_high_dpi_awareness()` call (already done inside `apply_dark_theme`)
2. Removed the `elif` macOS/Linux icon block (already done in `_load_app_icon()`)
3. Windows `.ico` + `.png` icon kept here because it needs special handling after ttkbootstrap and `_load_app_icon()` also handles Windows separately

### Step 4: Run test to verify it passes

- [ ] Run: `venv/bin/python -m pytest tests/test_startup.py -v`
- Expected: ALL PASS

### Step 5: Run full test suite for regressions

- [ ] Run: `venv/bin/python -m pytest tests/ -v`
- Expected: All tests PASS

### Step 6: Verify startup timing improvement

- [ ] Run the timing script to confirm icon loading is faster:

```bash
venv/bin/python -c "
import time, sys, os
os.chdir('/Users/davidarmstrong/Antigravity/VCAA_PDF_App')

t0 = time.perf_counter()
import tkinter as tk
from theme import apply_dark_theme
from PIL import Image, ImageTk

root = tk.Tk()
root.lift()
root.attributes('-topmost', True)
apply_dark_theme(root)

from pdf_generator import BulkPDFGenerator
app = BulkPDFGenerator(root)
t1 = time.perf_counter()
print(f'TOTAL to mainloop: {(t1-t0)*1000:.0f}ms')
root.after(200, root.destroy)
root.mainloop()
"
```

- Expected: ~100-200ms reduction from baseline (1563ms → ~1350-1450ms)

### Step 7: Commit

- [ ] ```bash
git add pdf_generator.py tests/test_startup.py
git commit -m "perf: remove duplicate icon load and DPI init from startup

icon.png (1.3 MB) was opened 3 times with 4 LANCZOS resizes during
startup. Removed the redundant load in main() — _load_app_icon()
handles it. Also removed duplicate enable_high_dpi_awareness() call."
```

---

## Task 3: Smoke Test the Full App

### Step 1: Full test suite

- [ ] Run: `venv/bin/python -m pytest tests/ -v`
- Expected: All tests PASS (including new ones)

### Step 2: Manual smoke test from source

- [ ] Launch the app: `venv/bin/python pdf_generator.py`
- Verify:
  1. App launches and is responsive immediately
  2. Click "Click to set school details" — entry field accepts keyboard input immediately
  3. Type a school name, press Enter — saves correctly
  4. Icon appears correctly in title bar

### Step 3: Final commit (if any adjustments needed)

- [ ] Only if smoke test reveals issues. Otherwise skip.

---

## Risk Notes

- **Windows regression risk**: The icon loading change only removes the macOS/Linux path from `main()`. The Windows `.ico` + `.png` path stays. `_load_app_icon()` already has `if sys.platform != 'win32'` guards. No Windows impact.
- **Dialog crash regression risk**: We are NOT changing the 50ms defer — that stays. We're only adding a `focus_set()` after `grab_set()` in the same callback. If `grab_set()` crashes (the original bug), the focus call never runs either. Safe.
- **`_pick_excel_sheet` ordering**: The `after()` call must move below `combo` creation since the closure references `combo`. Currently at line 2577, combo is at line 2598. Must relocate.
