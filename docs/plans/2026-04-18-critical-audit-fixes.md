# Critical Audit Fixes — v2.10 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ship v2.10 with all 7 Critical findings from the 2026-04-18 deep audit resolved — prioritising silent-data-corruption fixes first, then the big generation-perf win, then stability/diagnostics, then threading safety, cache hygiene, and UI resilience.

**Architecture:** Each Critical finding becomes one phase = one commit. TDD where feasible (fidelity and cache-eviction logic are unit-testable; UI/threading fixes use structural tests via `inspect.getsource()` the way `tests/test_performance.py` already does). Ship behind the existing manual QA loop — no feature flags. Keep backwards-compat with existing template/settings JSON.

**Tech Stack:** Python 3.10+, pandas, pypdf, PyMuPDF (fitz), tkinter/ttkbootstrap, pytest (via `venv/bin/python -m pytest`).

**Source-of-truth audit report:** See the session that produced this plan — 4 parallel code-reviewer agents.

**Execution order (user-approved):** C1 → C2 → C3 → C6 → C4 → C5 → C7

---

## Phase 1 — Fidelity: CSV dtype + fallback data_type (C1 + C2)

**Rationale for bundling:** Both are silent-data-corruption bugs in the same generation pipeline, both small, both share a test file. One commit = clean "v2.10 fixes silent data corruption" release note.

### Task 1.1: Write failing test for CSV leading-zero preservation (C1)

**Files:**
- Create: `tests/test_data_fidelity.py`

**Step 1: Write the failing test**

```python
"""Fidelity tests — prove silent-data-corruption bugs stay fixed.

These tests live at the data boundary: what the user put in the spreadsheet
must be what ends up in the PDF. No silent coercion, no lost leading zeros,
no lost dates.
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd


class TestCsvLeadingZeroPreservation(unittest.TestCase):
    """CSV load must use dtype=str so leading-zero IDs survive (C1)."""

    def test_csv_load_matches_excel_dtype_str(self):
        """The CSV branch of load_data_tab3 must pass dtype=str to pd.read_csv.

        Before fix: CSV path used pd.read_csv(path, encoding=...) with no
        dtype, so pandas auto-inferred numeric dtype for columns containing
        digits — silently stripping leading zeros from student IDs and
        reformatting Excel-serial dates. Excel path already uses dtype=str.
        """
        from pdf_generator import BulkPDFGenerator
        import inspect
        source = inspect.getsource(BulkPDFGenerator.load_data_tab3)
        # Both read_csv calls must pass dtype=str
        csv_reads = [line for line in source.split('\n') if 'read_csv' in line]
        self.assertTrue(len(csv_reads) >= 1,
                        "Expected at least one pd.read_csv call in load_data_tab3")
        for line in csv_reads:
            self.assertIn('dtype=str', line,
                          f"pd.read_csv must pass dtype=str to preserve leading "
                          f"zeros and prevent date re-formatting: {line.strip()}")

    def test_csv_dtype_str_actually_preserves_leading_zeros(self):
        """Documentation test: confirms the pandas behaviour the fix relies on.

        This test does NOT exercise load_data_tab3 (that would require
        booting tkinter) — the structural test above is the real regression
        guard. This test exists so a future reader can see WHY dtype=str
        matters if they're tempted to remove it.
        """
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.csv', delete=False, encoding='utf-8-sig'
        ) as f:
            f.write('Student ID,Name\n')
            f.write('00123,Smith\n')
            f.write('00045,Jones\n')
            path = f.name

        # Without dtype=str — leading zeros would be lost (inferred as int64)
        df_numeric = pd.read_csv(path, encoding='utf-8-sig')
        self.assertEqual(df_numeric.iloc[0]['Student ID'], 123,
                         "Baseline: without dtype=str pandas coerces to int")

        # With dtype=str — what the fix applies
        df_str = pd.read_csv(path, dtype=str, encoding='utf-8-sig')
        self.assertEqual(df_str.iloc[0]['Student ID'], '00123',
                         "dtype=str must preserve the literal string '00123'")
        self.assertEqual(df_str.iloc[1]['Student ID'], '00045')
```

**Step 2: Run test — verify failure**

Run: `venv/bin/python -m pytest tests/test_data_fidelity.py::TestCsvLeadingZeroPreservation -v`
Expected: `test_csv_load_matches_excel_dtype_str` FAILS with "pd.read_csv must pass dtype=str"

### Task 1.2: Implement CSV dtype=str fix

**Files:**
- Modify: `pdf_generator.py:2937-2941`

**Step 1: Apply the edit**

Replace:
```python
if excel_path.lower().endswith('.csv'):
    try:
        self.df = pd.read_csv(excel_path, encoding='utf-8-sig')
    except UnicodeDecodeError:
        self.df = pd.read_csv(excel_path, encoding='latin-1')
```

With:
```python
if excel_path.lower().endswith('.csv'):
    # dtype=str mirrors the Excel path — preserves leading zeros on
    # student IDs and prevents pandas from silently re-formatting
    # Excel-serial-style date columns.
    try:
        self.df = pd.read_csv(excel_path, dtype=str, encoding='utf-8-sig')
    except UnicodeDecodeError:
        self.df = pd.read_csv(excel_path, dtype=str, encoding='latin-1')
```

**Step 2: Run the failing test — verify pass**

Run: `venv/bin/python -m pytest tests/test_data_fidelity.py::TestCsvLeadingZeroPreservation -v`
Expected: both tests PASS

### Task 1.3: Write failing test for fallback path data_type (C2)

**Files:**
- Modify: `tests/test_data_fidelity.py`

**Step 1: Append test class**

```python
class TestFallbackPathDateConversion(unittest.TestCase):
    """Fallback auto-match path must pass data_type so date fields convert (C2).

    Before fix: when analyzed_fields is empty (no template loaded), the
    fallback branch at pdf_generator.py:3388 called format_value_tab3(val)
    with no data_type, defaulting to 'text'. Any Excel serial date in those
    fields was written to the PDF as a raw integer like '45000' instead of
    '01/03/2023'.
    """

    def test_fallback_path_passes_data_type(self):
        """The else-branch in _generate_single_pdf must resolve a data_type.

        Either by matching against analyzed_fields if available, or by
        inferring from field name (contains 'date'|'dob'|'birth') — must NOT
        be a bare format_value_tab3(val) call.
        """
        from pdf_generator import BulkPDFGenerator
        import inspect
        source = inspect.getsource(BulkPDFGenerator._generate_single_pdf)
        # The fallback else-branch is the second format_value_tab3 call —
        # it must pass a data_type kwarg or positional arg.
        calls = [line.strip() for line in source.split('\n')
                 if 'format_value_tab3' in line and 'def ' not in line]
        self.assertTrue(len(calls) >= 2,
                        "Expected two format_value_tab3 call sites "
                        "(analyzed path + fallback path)")
        for call in calls:
            self.assertIn('data_type', call,
                          f"format_value_tab3 must receive a data_type arg "
                          f"so Excel-serial dates convert in the fallback "
                          f"path: {call}")
```

**Step 2: Run test — verify failure**

Run: `venv/bin/python -m pytest tests/test_data_fidelity.py::TestFallbackPathDateConversion -v`
Expected: FAIL with "format_value_tab3 must receive a data_type arg"

### Task 1.4: Implement fallback data_type inference

**Files:**
- Modify: `pdf_generator.py:3379-3389`

**Step 1: Apply the edit**

Replace:
```python
else:
    # Fallback to original auto-matching (no combed field support)
    row_dict_lower = {str(col).lower(): val for col, val in row_data.items()}

    for pdf_field in ctx['pdf_fields']:
        pdf_field_lower = pdf_field.lower()

        # Try to find matching Excel column
        if pdf_field_lower in row_dict_lower:
            val = self.format_value_tab3(row_dict_lower[pdf_field_lower])
            field_values[pdf_field] = val
```

With:
```python
else:
    # Fallback to original auto-matching (no combed field support).
    # Infer data_type from field name so Excel-serial dates still convert
    # when the user hasn't run the field audit dialog (no analyzed_fields).
    row_dict_lower = {str(col).lower(): val for col, val in row_data.items()}

    for pdf_field in ctx['pdf_fields']:
        pdf_field_lower = pdf_field.lower()

        # Try to find matching Excel column
        if pdf_field_lower in row_dict_lower:
            inferred_type = "date" if any(
                token in pdf_field_lower
                for token in ("date", "dob", "birth")
            ) else "text"
            val = self.format_value_tab3(
                row_dict_lower[pdf_field_lower],
                data_type=inferred_type,
            )
            field_values[pdf_field] = val
```

**Step 2: Run the failing test — verify pass**

Run: `venv/bin/python -m pytest tests/test_data_fidelity.py -v`
Expected: all 3 tests in the file PASS

### Task 1.5: Run full suite, commit

**Step 1: Run all tests**

Run: `venv/bin/python -m pytest tests/ -v`
Expected: all green — no regressions

**Step 2: Commit**

```bash
git add tests/test_data_fidelity.py pdf_generator.py
git commit -m "$(cat <<'EOF'
fix: prevent silent data corruption in CSV loads and fallback generation path

C1: CSV path now passes dtype=str to pd.read_csv — mirrors the Excel path,
preserves leading-zero student IDs, and stops pandas from silently re-
formatting Excel-serial date columns.

C2: The fallback auto-match branch in _generate_single_pdf (used when no
template has been analysed) now infers a data_type from the field name so
Excel-serial dates convert to DD/MM/YYYY instead of being written as raw
integers like "45000".

Both bugs produced silent wrong values in generated PDFs with no error
raised and no user-visible indication — the highest-severity failure mode
for this app's users.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Phase 2 — Performance: hoist PdfReader above the per-student loop (C3)

**Rationale:** Single isolated change, 10–50× generation speedup on large batches, small blast radius. Ship alone so the perf win is bisectable.

### Task 2.1: Write structural test

**Files:**
- Create: `tests/test_generation_perf.py`

**Step 1: Write the failing test**

```python
"""Generation-path performance regression tests (C3).

Structural tests via inspect.getsource — mirrors the pattern in
tests/test_performance.py rather than relying on flaky timing.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestReaderHoistedOutOfLoop(unittest.TestCase):
    """PdfReader(ctx['pdf_path']) must NOT appear inside _generate_single_pdf.

    Before fix: _generate_single_pdf called PdfReader(ctx['pdf_path']) on
    every student — 100 students = 100 redundant parses of the same PDF.
    After fix: reader is parsed once in run_generation_tab3 and passed in
    via ctx (or a new arg) to _generate_single_pdf.
    """

    def test_single_pdf_does_not_reopen_reader(self):
        from pdf_generator import BulkPDFGenerator
        import inspect
        source = inspect.getsource(BulkPDFGenerator._generate_single_pdf)
        self.assertNotIn(
            "PdfReader(", source,
            "_generate_single_pdf must not call PdfReader() — the reader "
            "should be opened once in run_generation_tab3 and passed in via "
            "ctx. Opening it per-student is a 10–50x generation slowdown."
        )

    def test_run_generation_opens_reader_once(self):
        from pdf_generator import BulkPDFGenerator
        import inspect
        source = inspect.getsource(BulkPDFGenerator.run_generation_tab3)
        self.assertIn(
            "PdfReader(", source,
            "run_generation_tab3 must open the PdfReader once before the "
            "per-student loop."
        )
```

**Step 2: Run — verify failure**

Run: `venv/bin/python -m pytest tests/test_generation_perf.py -v`
Expected: `test_single_pdf_does_not_reopen_reader` FAILS (reader IS in _generate_single_pdf today).

### Task 2.2: Hoist reader into ctx, reuse via writer.append per student

**Files:**
- Modify: `requirements.txt` (pin pypdf minimum version — safety gate for reader reuse)
- Modify: `pdf_generator.py:3233-3318` (add reader open before loop)
- Modify: `pdf_generator.py:3325-3338` (drop reader open in _generate_single_pdf)

**Step 0: Verify / pin pypdf>=3.0 in requirements.txt**

Sharing a `PdfReader` across multiple `writer.append(reader)` calls is only safe on pypdf 3.x+, where the internal `reader._pages` cache is populated read-only after first access. On pypdf 1.x/2.x the cache was mutated on access and sharing could corrupt the second clone.

Open `requirements.txt`. If the line does not exist or is unpinned, add / update it to:
```
pypdf>=3.0
```

If a stricter pin already exists (e.g. `pypdf>=4.0`) leave it alone.

**Step 1: Modify `run_generation_tab3` to open reader once**

Near the top of `run_generation_tab3` (inside the `try:` block at line 3239, before the `total = len(...)` at line 3248), insert:

```python
# Open the PDF template ONCE for the whole batch — opening per-student
# re-parses the cross-ref table and object stream every iteration, which
# dominates wall-clock time on batches of 50+ students. (C3)
reader = PdfReader(ctx['pdf_path'])
ctx['_reader'] = reader
```

**Step 2: Modify `_generate_single_pdf` to reuse the reader**

Replace:
```python
def _generate_single_pdf(self, ctx, row_data, output_path):
    """Generate a single PDF with combed field support.

    THREAD SAFETY: This method runs on the generation worker thread.
    It must only access local variables and the immutable *ctx* snapshot
    dict — never read or write any ``self.*`` attribute directly.
    All UI updates must be dispatched via ``self.root.after()``.
    """
    reader = PdfReader(ctx['pdf_path'])
    writer = PdfWriter()

    # Clone the PDF
    writer.append(reader)
```

With:
```python
def _generate_single_pdf(self, ctx, row_data, output_path):
    """Generate a single PDF with combed field support.

    THREAD SAFETY: This method runs on the generation worker thread.
    It must only access local variables and the immutable *ctx* snapshot
    dict — never read or write any ``self.*`` attribute directly, with
    one documented exception: ``self.logger`` is safe to call from any
    thread (logging.Logger and RotatingFileHandler both acquire internal
    locks). All UI updates must be dispatched via ``self.root.after()``.

    The PdfReader is opened once per batch in ``run_generation_tab3`` and
    handed in via ``ctx['_reader']`` — re-opening per student was the
    dominant cost on large batches (C3).
    """
    reader = ctx['_reader']
    writer = PdfWriter()

    # Clone the PDF from the shared reader. Safe on pypdf 3.x+ — the
    # reader's internal page cache is populated read-only after first
    # access, so writer.append() does not mutate the reader. Requires the
    # pypdf>=3.0 pin in requirements.txt.
    writer.append(reader)
```

**Step 3: Also remove the now-dead `field_types_lookup` dict (Important finding #3 in perf audit)**

Delete lines 3353-3355:
```python
# Build lookup of field data types
field_types_lookup = {f.field_name.lower(): f.data_type
                      for f in ctx['analyzed_fields']}
```

This dict is constructed but never read — `field.data_type` is accessed directly.

**Step 4: Run tests**

Run: `venv/bin/python -m pytest tests/test_generation_perf.py tests/test_data_fidelity.py tests/ -v`
Expected: all green

### Task 2.3: Commit

```bash
git add tests/test_generation_perf.py pdf_generator.py
git commit -m "$(cat <<'EOF'
perf: open PDF template once per batch instead of once per student

C3: _generate_single_pdf was calling PdfReader(ctx['pdf_path']) on every
student, re-parsing the cross-reference table and object stream 1× per
output PDF. Moved the open into run_generation_tab3 and shared the reader
via ctx['_reader']. For a 100-student batch on a typical multi-page form
this trims 5–50 seconds of pure overhead.

Also removed the dead field_types_lookup dict — constructed every call but
never read.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Phase 3 — Stability: surface per-row generation errors + add log file (C6)

**Rationale:** When a batch completes with "2 errors" the user currently cannot tell *which* rows failed or *why*. On a read-only output folder or AV-locked path they get no guidance. We bundle the minor-tier "no log file" finding here because it's the same user problem (production diagnostics) and they share the same infrastructure.

### Task 3.1: Set up `logging` with a rotating file handler

**Files:**
- Modify: `pdf_generator.py` — add logging bootstrap in `BulkPDFGenerator.__init__` or a module-level helper near `_resolve_data_dir`.

**Step 1: Add log setup helper near the top of the class (or reuse `_resolve_data_dir`)**

Locate `_resolve_data_dir()` — logging config goes right after the directory is resolved so logs land next to `settings.json`.

Add a new module-level function just before the `BulkPDFGenerator` class:

```python
def _setup_app_logging(data_dir: str) -> logging.Logger:
    """Configure a rotating file logger for production diagnostics.

    Logs go to {data_dir}/app.log with a 1MB cap and 3 rotated backups.
    Tkinter callbacks swallow tracebacks silently in a windowed .exe;
    this is the only way a teacher's bug report can include context.
    """
    from logging.handlers import RotatingFileHandler
    log_path = os.path.join(data_dir, 'app.log')
    logger = logging.getLogger('bulk_pdf_generator')
    # Idempotent — avoid duplicate handlers on hot-reload / re-init
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    try:
        handler = RotatingFileHandler(
            log_path, maxBytes=1_000_000, backupCount=3, encoding='utf-8'
        )
        handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
        ))
        logger.addHandler(handler)
    except OSError:
        # Data dir unwritable — fall back to null handler so log calls
        # don't raise, but we lose diagnostics. Non-fatal.
        logger.addHandler(logging.NullHandler())
    return logger
```

Add `import logging` to the imports block at the top if not already present.

**Step 2: Initialise the logger in `BulkPDFGenerator.__init__`**

After the data-dir / settings load block, call:

```python
self.logger = _setup_app_logging(self._data_dir)
self.logger.info("BulkPDFGenerator started (build %s)", BUILD_VERSION)
```

### Task 3.2: Collect per-row errors and surface them in completion dialog

**Files:**
- Modify: `pdf_generator.py:3249-3323` (`run_generation_tab3` — accumulate errors)
- Modify: `pdf_generator.py:3487-3508` (`generation_complete_tab3` — display error list)

**Step 1: Write a failing test**

Append to `tests/test_generation_perf.py`:

```python
class TestErrorSurfacing(unittest.TestCase):
    """Per-row generation errors must be accumulated and surfaced (C6)."""

    def test_run_generation_collects_error_details(self):
        """run_generation_tab3 must accumulate error rows into a list,
        not just increment a counter."""
        from pdf_generator import BulkPDFGenerator
        import inspect
        source = inspect.getsource(BulkPDFGenerator.run_generation_tab3)
        # Must keep a list of error details, not just a counter
        self.assertIn('error_details', source,
                      "run_generation_tab3 must collect error_details "
                      "(row label + reason) so the completion dialog can "
                      "show WHICH rows failed, not just HOW MANY.")

    def test_completion_dialog_shows_error_details(self):
        from pdf_generator import BulkPDFGenerator
        import inspect
        source = inspect.getsource(BulkPDFGenerator.generation_complete_tab3)
        self.assertIn('error_details', source,
                      "generation_complete_tab3 must display the per-row "
                      "error details provided by run_generation_tab3.")
```

Run: expected FAIL.

**Step 2: Implement error accumulation**

Replace the inner try/except at lines 3293-3300:
```python
try:
    self._generate_single_pdf(ctx, row, output_path)
    success_count += 1
    status_text = f"Created: {filename}"
except Exception as e:
    error_count += 1
    row_label = '_'.join(name_parts) if name_parts else f'Row_{idx+1}'
    status_text = f"Error: {row_label} - {str(e)}"
```

With:
```python
try:
    self._generate_single_pdf(ctx, row, output_path)
    success_count += 1
    status_text = f"Created: {filename}"
except Exception as e:
    error_count += 1
    row_label = '_'.join(name_parts) if name_parts else f'Row_{idx+1}'
    err_str = str(e)
    error_details.append(f"{row_label}: {err_str}")
    self.logger.exception("Generation failed for %s", row_label)
    status_text = f"Error: {row_label} - {err_str}"
```

Initialise `error_details = []` at the top of the `try:` block near `error_count = 0` (line 3250).

**Step 3: Pass error_details through to completion**

Change the final-message block (lines 3312-3318) to:
```python
# Final message
final_message = f"Complete! {success_count} PDFs created"
if error_count > 0:
    final_message += f", {error_count} errors"
final_message += f"\n\nOutput folder: {output_folder}"

self.root.after(
    0, self.generation_complete_tab3,
    final_message, output_folder, error_details,
)
```

**Step 4: Update `generation_complete_tab3` signature**

Change:
```python
def generation_complete_tab3(self, message, output_folder):
```
To:
```python
def generation_complete_tab3(self, message, output_folder, error_details=None):
```

And right before the final `messagebox.askyesno` call, if errors exist, show them first:
```python
if error_details:
    # Cap at 20 rows to keep the dialog manageable; full list is in the log file
    preview = "\n".join(error_details[:20])
    if len(error_details) > 20:
        preview += f"\n… and {len(error_details) - 20} more (see app.log)"
    messagebox.showwarning(
        f"{len(error_details)} rows failed",
        f"The following rows could not be generated:\n\n{preview}",
    )
```

**Step 5: Run tests, verify pass**

Run: `venv/bin/python -m pytest tests/test_generation_perf.py tests/ -v`
Expected: all green.

### Task 3.3: Commit

```bash
git add tests/test_generation_perf.py pdf_generator.py
git commit -m "$(cat <<'EOF'
fix: surface per-row generation errors and add rotating app log

C6: The per-student try/except in run_generation_tab3 used to only increment
an error counter. The final dialog said "2 errors" with no way to tell which
rows failed or why — and on read-only or AV-locked output folders every row
could fail silently. Errors are now accumulated as "row_label: reason"
strings and shown in a warning dialog before the completion prompt.

Also adds a rotating file logger at {data_dir}/app.log (1MB × 3 backups) so
the next teacher bug report can include actual context — the windowed .exe
has no console and currently drops all tracebacks.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Phase 4 — Threading: capture canvas dimensions on main thread (C4)

**Rationale:** `winfo_width()` / `winfo_height()` are Tcl calls and Tcl is not thread-safe. The current code calls them from `_resize_and_deliver`, which runs on a daemon worker thread. On Windows this can return garbage or raise TclError.

### Task 4.1: Write structural test

**Files:**
- Modify: `tests/test_performance.py` (this file already covers threading anti-patterns — extend it).

**Step 1: Append test class**

```python
class TestCanvasDimsCapturedOnMainThread(unittest.TestCase):
    """_resize_and_deliver runs off-thread; winfo_* calls must NOT appear in it (C4)."""

    def test_resize_and_deliver_has_no_winfo_calls(self):
        from preview_renderer import PreviewRenderer
        import inspect
        source = inspect.getsource(PreviewRenderer._resize_and_deliver)
        self.assertNotIn(
            'winfo_width', source,
            "_resize_and_deliver runs on a worker thread — Tcl is not thread-"
            "safe. Canvas dims must be captured on the main thread and passed "
            "in as args."
        )
        self.assertNotIn('winfo_height', source)

    def test_resize_and_deliver_receives_canvas_dims(self):
        from preview_renderer import PreviewRenderer
        import inspect
        sig = inspect.signature(PreviewRenderer._resize_and_deliver)
        self.assertIn('canvas_w', sig.parameters,
                      "_resize_and_deliver must accept canvas_w as an argument "
                      "(captured on the main thread before the worker spawns).")
        self.assertIn('canvas_h', sig.parameters)
```

Run: expected FAIL on both.

### Task 4.2: Capture dims at the main-thread boundaries and plumb through

**Files:**
- Modify: `preview_renderer.py` — multiple edits below. Each step is a discrete, wholesale replacement — do NOT merge or skip any step, and do NOT leave the old text in place alongside the new.

**Step 1: Add a helper method `_capture_canvas_dims` to `PreviewRenderer`**

Insert this method immediately after `_resolve_font()` (around line 77):

```python
def _capture_canvas_dims(self) -> tuple[int, int]:
    """Read canvas dimensions on the current (main) thread.

    MUST be called from the main thread only — Tcl is not thread-safe.
    """
    w = self._canvas.winfo_width()
    h = self._canvas.winfo_height()
    if w <= 1:
        w = 600
    if h <= 1:
        h = 300
    return w, h
```

**Step 2: WHOLESALE replace the tail of `_worker_render` (lines 209-217)**

Current text (delete these 9 lines entirely — the comment line at 209, the direct call at 210, the blank line, the 3-line guard, and the 4-line `root.after(_schedule_quality_pass ...)` call):

```python
        # Fast pass: BILINEAR resize
        self._resize_and_deliver(preview_img, zoom_level, my_id, use_lanczos=False)

        # Schedule quality pass (LANCZOS) after 300ms settle
        if not self._shutdown and my_id == self._request_id:
            self._root.after(
                0,
                self._schedule_quality_pass, preview_img, zoom_level, my_id,
            )
```

Replace with (this is the ENTIRE new tail of `_worker_render` — nothing else follows):

```python
        # Hand back to main thread: it captures canvas dims (Tcl is not
        # thread-safe) and spawns the resize worker. Quality (LANCZOS)
        # pass is chained from within _do_resize. (C4)
        if self._shutdown or my_id != self._request_id:
            return
        self._root.after(
            0, self._do_resize, preview_img, zoom_level, my_id, False,
        )
```

Verify afterwards: the string `_resize_and_deliver(` must no longer appear anywhere inside `_worker_render`, and `_schedule_quality_pass` must no longer appear anywhere inside `_worker_render`.

**Step 3: DELETE the entire `_schedule_quality_pass` method**

Delete these 7 lines (currently at approx 219-228):

```python
    def _schedule_quality_pass(
        self, raw_img: Image.Image, zoom_level: float, my_id: int
    ):
        """Main thread: schedule a LANCZOS re-render after 300ms."""
        if self._shutdown or my_id != self._request_id:
            return
        self._quality_timer = self._root.after(
            300,
            self._do_resize, raw_img, zoom_level, my_id, True,
        )
```

After this step, `grep -n _schedule_quality_pass preview_renderer.py` must return zero matches. The quality-pass scheduling is moved into `_do_resize` in Step 4.

**Step 4: WHOLESALE replace `_do_resize` (lines 230-243 in the original file)**

Current text (delete entirely):

```python
    def _do_resize(
        self, raw_img: Image.Image, zoom_level: float, my_id: int, use_lanczos: bool
    ):
        """Main thread entry: spawn a resize worker thread."""
        self._quality_timer = None
        if self._shutdown or my_id != self._request_id:
            return

        t = threading.Thread(
            target=self._resize_and_deliver,
            args=(raw_img, zoom_level, my_id, use_lanczos),
            daemon=True,
        )
        t.start()
```

Replace entirely with:

```python
    def _do_resize(
        self, raw_img: Image.Image, zoom_level: float, my_id: int, use_lanczos: bool
    ):
        """Main thread entry: capture canvas dims, spawn resize worker.

        Called for both the initial fast (BILINEAR) pass and the settle
        quality (LANCZOS) pass. The quality pass is self-scheduled from
        here when use_lanczos is False, so there is no longer a separate
        _schedule_quality_pass method. (C4)
        """
        self._quality_timer = None
        if self._shutdown or my_id != self._request_id:
            return

        # Capture Tcl-dependent canvas dims on the main thread — NEVER in
        # the worker, because Tcl is not thread-safe. (C4)
        canvas_w, canvas_h = self._capture_canvas_dims()

        t = threading.Thread(
            target=self._resize_and_deliver,
            args=(raw_img, zoom_level, my_id, use_lanczos, canvas_w, canvas_h),
            daemon=True,
        )
        t.start()

        # Chain the LANCZOS quality pass 300ms after the fast pass fires.
        # Only the fast pass schedules the quality pass (prevents infinite
        # chaining when the quality pass itself calls _do_resize).
        if not use_lanczos and not self._shutdown and my_id == self._request_id:
            self._quality_timer = self._root.after(
                300,
                self._do_resize, raw_img, zoom_level, my_id, True,
            )
```

**Step 5: WHOLESALE replace `_resize_and_deliver` signature and body (lines 245-275)**

Current text (delete entirely):

```python
    def _resize_and_deliver(
        self,
        raw_img: Image.Image,
        zoom_level: float,
        my_id: int,
        use_lanczos: bool,
    ):
        """Worker thread: resize image and deliver to main thread."""
        if self._shutdown or my_id != self._request_id:
            return

        try:
            canvas_width = self._canvas.winfo_width()
            canvas_height = self._canvas.winfo_height()
            if canvas_width <= 1:
                canvas_width = 600
            if canvas_height <= 1:
                canvas_height = 300

            img_w, img_h = raw_img.size
            base_scale = min(canvas_width / img_w, canvas_height / img_h) * 0.95
            scale = base_scale * zoom_level

            new_w = max(1, int(img_w * scale))
            new_h = max(1, int(img_h * scale))

            resampling = Image.Resampling.LANCZOS if use_lanczos else Image.Resampling.BILINEAR
            resized = raw_img.resize((new_w, new_h), resampling)

        except Exception:
            return
```

Replace entirely with (note the new `canvas_w`, `canvas_h` params at the end of the signature — exact names, the test asserts on them):

```python
    def _resize_and_deliver(
        self,
        raw_img: Image.Image,
        zoom_level: float,
        my_id: int,
        use_lanczos: bool,
        canvas_w: int,
        canvas_h: int,
    ):
        """Worker thread: resize image (pure PIL) and deliver to main thread.

        Canvas dimensions are passed in — this method MUST NOT call any
        Tcl (winfo_*) functions because Tcl is not thread-safe. (C4)
        """
        if self._shutdown or my_id != self._request_id:
            return

        try:
            img_w, img_h = raw_img.size
            base_scale = min(canvas_w / img_w, canvas_h / img_h) * 0.95
            scale = base_scale * zoom_level

            new_w = max(1, int(img_w * scale))
            new_h = max(1, int(img_h * scale))

            resampling = Image.Resampling.LANCZOS if use_lanczos else Image.Resampling.BILINEAR
            resized = raw_img.resize((new_w, new_h), resampling)

        except Exception:
            return
```

**Step 6: Post-edit invariant check**

Run these three greps — all must return the expected results:

```bash
grep -n "winfo_width\|winfo_height" preview_renderer.py
# Expected: only line ~80 (inside _capture_canvas_dims). No other matches.

grep -n "_schedule_quality_pass" preview_renderer.py
# Expected: zero matches.

grep -n "_resize_and_deliver(" preview_renderer.py
# Expected: exactly 2 matches — the def line, and the threading.Thread(target=...) call in _do_resize.
```

If any grep disagrees, Steps 2–5 were applied incompletely — re-read the file and fix before running tests.

**Step 7: Run tests**

Run: `venv/bin/python -m pytest tests/test_performance.py::TestCanvasDimsCapturedOnMainThread tests/ -v`
Expected: all green.

### Task 4.3: Commit

```bash
git add tests/test_performance.py preview_renderer.py
git commit -m "$(cat <<'EOF'
fix: capture canvas dimensions on main thread, never in preview worker

C4: PreviewRenderer._resize_and_deliver runs on a daemon worker thread but
was calling canvas.winfo_width()/winfo_height() — Tcl calls. Tcl is not
thread-safe; on Windows this can return garbage or raise TclError under
load. Dims are now captured in _do_resize on the main thread and passed to
the worker as plain ints.

Also inlined the quality (LANCZOS) pass scheduling into _do_resize so the
scheduling is co-located with the dispatch. No behaviour change from the
user's perspective — same fast BILINEAR pass then quality LANCZOS at 300ms.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Phase 5 — Cache hygiene: bound the disk preview cache (C5)

**Rationale:** The PNG cache in `~/Documents/BulkPDFGenerator/.preview_cache/` grows forever. On GPO-redirected profiles with quotas (noted in CLAUDE.md), this becomes a real problem. Cap at ~200MB, prune on startup.

### Task 5.1: Unit-test the pruning logic

**Files:**
- Create: `tests/test_cache_eviction.py`

**Step 1: Write the failing test**

```python
"""Disk-cache pruning tests (C5)."""
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestPruneDiskCache(unittest.TestCase):
    """visual_preview._prune_disk_cache must evict oldest files first."""

    def test_prune_noop_below_cap(self):
        from visual_preview import _prune_disk_cache
        with tempfile.TemporaryDirectory() as d:
            for i in range(3):
                with open(os.path.join(d, f"x_page_{i}_dpi_200.png"), "wb") as f:
                    f.write(b"x" * 1024)  # 1KB each
            _prune_disk_cache(d, max_bytes=10_000)
            self.assertEqual(len(os.listdir(d)), 3,
                             "Should not prune when under cap")

    def test_prune_evicts_oldest_first(self):
        from visual_preview import _prune_disk_cache
        with tempfile.TemporaryDirectory() as d:
            paths = []
            for i in range(5):
                p = os.path.join(d, f"x_page_{i}_dpi_200.png")
                with open(p, "wb") as f:
                    f.write(b"x" * 1024)
                # Stagger mtimes so "oldest" is deterministic
                os.utime(p, (time.time() - (5 - i), time.time() - (5 - i)))
                paths.append(p)

            # Cap at 2.5KB → must drop until ≤2.5KB → leave 2 newest
            _prune_disk_cache(d, max_bytes=2500)
            remaining = sorted(os.listdir(d))
            self.assertEqual(remaining, ['x_page_3_dpi_200.png',
                                         'x_page_4_dpi_200.png'])

    def test_prune_ignores_non_cache_files(self):
        from visual_preview import _prune_disk_cache
        with tempfile.TemporaryDirectory() as d:
            # A user file in the cache dir must not be deleted
            with open(os.path.join(d, "do_not_delete.txt"), "w") as f:
                f.write("keep me")
            with open(os.path.join(d, "x_page_1_dpi_200.png"), "wb") as f:
                f.write(b"x" * 10_000)
            _prune_disk_cache(d, max_bytes=100)
            self.assertIn('do_not_delete.txt', os.listdir(d))
```

Run: `venv/bin/python -m pytest tests/test_cache_eviction.py -v` — expected FAIL (function doesn't exist yet).

### Task 5.2: Implement `_prune_disk_cache` and call on startup

**Files:**
- Modify: `visual_preview.py`

**Step 1: Add the prune function at module scope**

Near the bottom of `visual_preview.py`, after `format_cache_size`:

```python
_DISK_CACHE_MAX_BYTES = 200 * 1024 * 1024  # 200MB


def _prune_disk_cache(cache_dir: str, max_bytes: int = _DISK_CACHE_MAX_BYTES) -> None:
    """Evict oldest cache PNGs until total size ≤ max_bytes.

    Only touches files matching the cache naming pattern ('_page_' in name
    and '.png' extension) — leaves any user files in the cache dir alone.
    Safe against transient OSErrors (skips locked files).
    """
    if not os.path.isdir(cache_dir):
        return

    entries = []
    total = 0
    try:
        for name in os.listdir(cache_dir):
            if not (name.endswith('.png') and '_page_' in name):
                continue
            path = os.path.join(cache_dir, name)
            try:
                stat = os.stat(path)
            except OSError:
                continue
            entries.append((stat.st_mtime, stat.st_size, path))
            total += stat.st_size
    except OSError:
        return

    if total <= max_bytes:
        return

    # Oldest-first
    entries.sort(key=lambda e: e[0])
    for _, size, path in entries:
        if total <= max_bytes:
            break
        try:
            os.remove(path)
            total -= size
        except OSError:
            pass
```

**Step 2: Call prune on `VisualPreviewGenerator.__enter__`**

In `__enter__` (after `os.makedirs(self.cache_dir, exist_ok=True)` or equivalent), add:
```python
_prune_disk_cache(self.cache_dir)
```

**Step 3: Run tests**

Run: `venv/bin/python -m pytest tests/test_cache_eviction.py tests/ -v`
Expected: all green.

### Task 5.3: Commit

```bash
git add tests/test_cache_eviction.py visual_preview.py
git commit -m "$(cat <<'EOF'
fix: bound disk preview cache at 200MB, prune oldest on startup

C5: The .preview_cache/ directory (inside the user's data dir) accumulated
PNGs forever — only clear_cache() ever pruned, and only via manual UI
action. A teacher working with 5 form templates across a school year could
end up with ~200MB of cached renders in a GPO-redirected Documents folder
where quotas are enforced.

Added _prune_disk_cache(cache_dir, max_bytes) at module scope in
visual_preview — oldest-first eviction by mtime, skips non-cache files, safe
against OSErrors. Called from VisualPreviewGenerator.__enter__ so every app
start silently trims back to the 200MB budget.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Phase 6 — UI resilience: guard select/deselect against grid-managed treeview (C7)

**Rationale:** `tree.pack_info()` raises `TclError` if the treeview was geometry-managed with `grid` or `place`. Some ttkbootstrap themes switch managers under the hood. Unhandled TclError in a tkinter callback = silent dead button for the user.

### Task 6.1: Write failing test

**Files:**
- Modify: `tests/test_performance.py`

**Step 1: Append test class**

```python
class TestSelectAllResilientToGeometryManager(unittest.TestCase):
    """select_all_tab3 / deselect_all_tab3 must not crash if treeview uses
    grid or place instead of pack (C7)."""

    def test_select_all_guards_pack_info(self):
        """select_all_tab3 (directly or via a helper) must guard pack_info()
        against TclError raised by non-pack geometry managers."""
        from pdf_generator import BulkPDFGenerator
        import inspect
        # Check both the method itself AND the _bulk_update_treeview helper
        # (refactor target) — the TclError guard may live in either.
        sources = [inspect.getsource(BulkPDFGenerator.select_all_tab3)]
        if hasattr(BulkPDFGenerator, '_bulk_update_treeview'):
            sources.append(inspect.getsource(
                BulkPDFGenerator._bulk_update_treeview))
        combined = '\n'.join(sources)
        self.assertIn(
            'TclError', combined,
            "select_all_tab3 (or a helper it delegates to) must wrap "
            "pack_info()/pack_forget() in try/except tk.TclError so a "
            "grid/place-managed or unmapped treeview doesn't crash a "
            "tkinter callback into silent failure."
        )

    def test_deselect_all_guards_pack_info(self):
        from pdf_generator import BulkPDFGenerator
        import inspect
        sources = [inspect.getsource(BulkPDFGenerator.deselect_all_tab3)]
        if hasattr(BulkPDFGenerator, '_bulk_update_treeview'):
            sources.append(inspect.getsource(
                BulkPDFGenerator._bulk_update_treeview))
        combined = '\n'.join(sources)
        self.assertIn(
            'TclError', combined,
            "deselect_all_tab3 (or a helper it delegates to) must wrap "
            "pack_info()/pack_forget() in try/except tk.TclError — "
            "same reason as select_all_tab3."
        )
```

Run: expected FAIL.

### Task 6.2: Refactor to shared helper with guard

**Files:**
- Modify: `pdf_generator.py:3143-3174`

**Step 1: Extract the detach/reattach pattern into a helper**

Add (once) near the two methods:

```python
def _bulk_update_treeview(self, tree, apply_fn):
    """Detach tree during a bulk item mutation to avoid per-row redraws.

    Falls back to a plain in-place update if pack_info() raises TclError
    (treeview managed by grid/place, or unmapped). (C7)
    """
    try:
        pack_info = tree.pack_info()
    except tk.TclError:
        # Not pack-managed — skip the detach optimisation, just mutate.
        apply_fn()
        return

    tree.pack_forget()
    try:
        apply_fn()
    finally:
        tree.pack(**pack_info)
```

**Step 2: Rewrite `select_all_tab3` and `deselect_all_tab3`**

```python
def select_all_tab3(self):
    """Select all in Tab 3 (batched if pack-managed, else plain loop)."""
    tree = self.tree_tab3

    def _apply():
        for item_id in self.selected_rows:
            self.selected_rows[item_id]['selected'] = True
            current_values = list(tree.item(item_id, 'values'))
            current_values[0] = 'Yes'
            tree.item(item_id, values=current_values)

    self._bulk_update_treeview(tree, _apply)
    self.update_selection_count_tab3()

def deselect_all_tab3(self):
    """Deselect all in Tab 3 (batched if pack-managed, else plain loop)."""
    tree = self.tree_tab3

    def _apply():
        for item_id in self.selected_rows:
            self.selected_rows[item_id]['selected'] = False
            current_values = list(tree.item(item_id, 'values'))
            current_values[0] = ''
            tree.item(item_id, values=current_values)

    self._bulk_update_treeview(tree, _apply)
    self.update_selection_count_tab3()
```

**Step 3: Run tests**

Run: `venv/bin/python -m pytest tests/test_performance.py tests/ -v`
Expected: all green.

### Task 6.3: Commit

```bash
git add tests/test_performance.py pdf_generator.py
git commit -m "$(cat <<'EOF'
fix: guard treeview bulk-select against non-pack geometry managers

C7: select_all_tab3 and deselect_all_tab3 called tree.pack_info() directly.
If any layer ever switches the treeview to grid or place — which some
ttkbootstrap themes do under the hood — pack_info() raises TclError inside
a tkinter callback and the button silently dead-ends.

Extracted the detach-for-batch-update optimisation into _bulk_update_treeview,
which wraps pack_info() in try/except tk.TclError and falls back to a plain
in-place loop when pack is not the active geometry manager.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Phase 7 — Integration: tag v2.10

### Task 7.1: Write release notes

**Files:**
- Modify: `RELEASE_NOTES.md`

Replace with:
```markdown
## v2.10 — Audit fixes

### Fixed
- **CSV data corruption** — CSV loads now preserve leading-zero IDs and date formatting (was silently coercing to numeric).
- **Fallback path date fields** — Excel-serial dates now convert in the auto-match generation path, not only when a template is analysed.
- **Silent row failures** — the completion dialog now lists which rows failed and why; full detail in app.log.
- **Preview thread safety** — canvas dimensions are no longer queried from the off-thread resize worker (Tcl is not thread-safe).
- **Treeview select-all crash** — guarded against non-pack geometry managers.

### Performance
- **~10–50× faster generation on large batches** — the PDF template is now parsed once per batch instead of once per student.

### Stability
- **Disk preview cache** capped at 200MB with automatic oldest-first eviction on startup.
- **New app.log** (1MB × 3 rotating) in the user data dir — provides diagnostics when the windowed .exe hits errors.
```

### Task 7.2: Run full suite one more time

Run: `venv/bin/python -m pytest tests/ -v`
Expected: all green (incl. the 17 existing performance tests).

### Task 7.3: Tag and push

```bash
git add RELEASE_NOTES.md
git commit -m "docs: release notes for v2.10"
git tag v2.10
git push origin main --tags
```

GitHub Actions will build Windows + macOS artifacts and publish the release automatically.

---

## Out of scope for this plan

The **Important** and **Minor** findings from the audit (checkbox/radio coercion, combed-overflow warnings wired to UI, atomic PDF write, Excel-locked friendly error, TemplateConfig missing-key defaults, update-check destroyed-widget guard, disk-cache write failure, etc.) are deliberately excluded — they belong in a v2.11 follow-up. The 7 Criticals are already a substantial PR.

## Testing strategy

- **Unit / structural tests** cover every fix — use `inspect.getsource()` for threading/UI invariants (mirrors the existing `tests/test_performance.py` pattern), real pandas round-trips for fidelity, and temp-dir filesystem tests for cache eviction.
- **No manual QA gate** between phases — structural tests are the gate. After all phases commit green, one manual smoke pass: load a CSV with leading-zero IDs + date column, generate 5 PDFs, confirm output visually.
- Run `venv/bin/python -m pytest tests/ -v` after each phase's commit.

## Rollback strategy

Each phase is one atomic commit on `main`. If any one breaks on test-channel builds, `git revert <sha>` is a clean, non-destructive rollback — the subsequent commits don't depend on earlier ones except Phase 1 (fidelity) → Phase 2 (perf), because Phase 2 touches code paths Phase 1 modified. Revert in reverse order if needed.
