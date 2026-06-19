# Reliable Filling of All PDF Field Types Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make batch generation reliably fill checkboxes, radio buttons, and choice fields (dropdowns/list boxes) — not just text — so the app lives up to "works with any PDF form with any field types."

**Architecture:** Extraction already detects every field type correctly; the gap is purely in *filling*. We capture two extra pieces of metadata during analysis (button on-states and choice options), persist them, and add a small pure helper module that maps a spreadsheet cell to the value each field type actually needs. `_generate_single_pdf` gains a checkbox/radio branch that writes a PDF `NameObject` (the only thing pypdf accepts to tick a box) and a choice-validation branch that warns instead of silently storing junk. Unfillable signature fields are detected and skipped with a message.

**Tech Stack:** Python 3.10+, PyMuPDF (`fitz`) for analysis, pypdf for filling, pytest.

---

## Why this is needed (empirically proven 2026-06-19)

Running the app's real `_generate_single_pdf` over a PDF with a checkbox, dropdown, and list box:

| Field | Spreadsheet value | Result today |
|---|---|---|
| Text | `Jane Smith` | ✅ filled |
| Checkbox | `X` | ❌ unchecked, **no error** |
| Checkbox | `Yes` (its exact on-state) | ❌ still unchecked, **no error** |
| Dropdown | `NSW` (valid option) | ✅ filled |
| Dropdown | `Victoria` (invalid) | ⚠️ stored out-of-list, viewer-dependent |
| List box | `English` (valid option) | ✅ filled |

Root cause, confirmed by isolating the pypdf call: a checkbox only ticks when the value is a PDF name matching the on-state (`/Yes` or `NameObject("/Yes")`). The current pipeline always sends a plain string, so **no checkbox or radio button ever fills, for any value.** The failure is silent — the worst kind for non-technical users.

```
value='Yes' (plain str)     -> stored 'Off'   ❌
value='/Yes' (slash name)   -> stored 'Yes'   ✅ CHECKED
value=NameObject('/Yes')    -> stored 'Yes'   ✅ CHECKED
value='X'                   -> stored 'Off'   ❌
```

---

## File Structure

- **Create `field_values.py`** — pure, GUI-free helpers that map a raw spreadsheet value to the value each field type needs (`normalize_button_value`, `normalize_choice_value`). Single responsibility: value→field-type translation. Pure functions so they are trivially unit-testable.
- **Create `tests/_form_fixture.py`** — one reusable helper, `build_mixed_form(path)`, that authors a PDF containing a text field, checkbox, dropdown, and list box. Shared by the analyzer and end-to-end tests.
- **Modify `models.py`** — add `on_states: List[str]` and `options: List[str]` to `PDFField` plus their (de)serialization. Backward-compatible (existing unknown-key filtering already protects old configs).
- **Modify `pdf_analyzer.py`** — populate `on_states` (from `widget.button_states()`) and `options` (from `widget.choice_values`) during extraction.
- **Modify `pdf_generator.py`** — in `_generate_single_pdf`, route checkbox/radio values through `normalize_button_value` into a dedicated NameObject bucket written with `auto_regenerate=True`; validate choice values; collect per-field warnings. Surface those warnings in the generation summary.
- **Create `tests/test_field_types.py`** — analyzer metadata, normalization units, and end-to-end fill assertions.

**Radio-button scope note:** PyMuPDF cannot author a radio group in a test fixture (it needs a pre-existing parent/kids structure — `page.add_widget` raises `bad xref`). Radio buttons use the *same* on-state-NameObject mechanism as checkboxes, so they are handled by the same code path and covered by `normalize_button_value` unit tests. End-to-end radio verification is a manual step against a real radio-bearing PDF (see "Manual verification" at the end) rather than a fabricated fixture.

---

## Task 1: Add field-type metadata to the data model

**Files:**
- Modify: `models.py:15-61` (the `PDFField` dataclass)
- Test: `tests/test_field_types.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_field_types.py
from models import PDFField


def _make(**kw):
    base = dict(
        field_name="Approved", field_type="CheckBox", page=1, length=None,
        is_combed=False, combed_fields=[], rect=(0, 0, 1, 1),
    )
    base.update(kw)
    return PDFField(**base)


def test_pdffield_has_button_and_choice_metadata_defaults():
    f = _make()
    assert f.on_states == []
    assert f.options == []


def test_pdffield_roundtrips_button_and_choice_metadata():
    f = _make(field_type="ComboBox", on_states=["Yes"], options=["VIC", "NSW"])
    restored = PDFField.from_dict(f.to_dict())
    assert restored.on_states == ["Yes"]
    assert restored.options == ["VIC", "NSW"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/python -m pytest tests/test_field_types.py -v`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'on_states'`

- [ ] **Step 3: Add the fields and serialization**

In `models.py`, add two fields to `PDFField` after `data_type` (line 28):

```python
    data_type: str = "text"  # "text", "number", or "date" (DD/MM/YYYY)
    on_states: List[str] = None   # Checkbox/radio "on" appearance states, e.g. ["Yes"]
    options: List[str] = None     # Choice (dropdown/listbox) valid option values

    def __post_init__(self):
        if self.on_states is None:
            self.on_states = []
        if self.options is None:
            self.options = []
```

In `to_dict` (after the `data_type` entry, line 43) add:

```python
            'data_type': self.data_type,
            'on_states': self.on_states,
            'options': self.options,
```

In `from_dict` (after the `data_type` line, line 60) add:

```python
            data_type=data.get('data_type', 'text'),
            on_states=data.get('on_states', []),
            options=data.get('options', []),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/bin/python -m pytest tests/test_field_types.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Run the full suite to confirm no regression**

Run: `venv/bin/python -m pytest tests/ -q`
Expected: all existing tests still pass (71 total).

- [ ] **Step 6: Commit**

```bash
git add models.py tests/test_field_types.py
git commit -m "feat: add on_states and options metadata to PDFField"
```

---

## Task 2: Reusable mixed-field test fixture

**Files:**
- Create: `tests/_form_fixture.py`

- [ ] **Step 1: Write the fixture helper**

```python
# tests/_form_fixture.py
"""Authors a PDF with one of each common fillable field type.

Used by analyzer and end-to-end fill tests. Radio buttons are intentionally
omitted — PyMuPDF cannot author a radio group (needs a pre-existing
parent/kids structure). Radio handling shares the checkbox code path and is
covered by unit tests on normalize_button_value.
"""
import fitz


def build_mixed_form(path: str) -> None:
    doc = fitz.open()
    page = doc.new_page(width=400, height=600)

    w = fitz.Widget()
    w.field_name = "Student_Name"
    w.field_type = fitz.PDF_WIDGET_TYPE_TEXT
    w.rect = fitz.Rect(150, 45, 350, 65)
    page.add_widget(w)

    w = fitz.Widget()
    w.field_name = "Approved"
    w.field_type = fitz.PDF_WIDGET_TYPE_CHECKBOX
    w.rect = fitz.Rect(150, 95, 170, 115)
    page.add_widget(w)

    w = fitz.Widget()
    w.field_name = "State"
    w.field_type = fitz.PDF_WIDGET_TYPE_COMBOBOX
    w.rect = fitz.Rect(150, 145, 300, 165)
    w.choice_values = ["VIC", "NSW", "QLD", "WA"]
    page.add_widget(w)

    w = fitz.Widget()
    w.field_name = "Subject"
    w.field_type = fitz.PDF_WIDGET_TYPE_LISTBOX
    w.rect = fitz.Rect(150, 195, 300, 265)
    w.choice_values = ["Maths", "English", "Science"]
    page.add_widget(w)

    doc.save(path)
    doc.close()
```

- [ ] **Step 2: Smoke-test the fixture**

Run: `venv/bin/python -c "import sys; sys.path.insert(0,'tests'); from _form_fixture import build_mixed_form; build_mixed_form('/tmp/_fx.pdf'); import fitz; d=fitz.open('/tmp/_fx.pdf'); print([w.field_name for w in d[0].widgets()])"`
Expected: `['Student_Name', 'Approved', 'State', 'Subject']`

- [ ] **Step 3: Commit**

```bash
git add tests/_form_fixture.py
git commit -m "test: add reusable mixed-field-type PDF fixture"
```

---

## Task 3: Capture on-states and options during analysis

**Files:**
- Modify: `pdf_analyzer.py:156-185` (the single-field branch in `_detect_combed_fields`)
- Test: `tests/test_field_types.py`

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_field_types.py
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from _form_fixture import build_mixed_form
from pdf_analyzer import PDFAnalyzer


def test_analysis_captures_button_and_choice_metadata(tmp_path):
    pdf = str(tmp_path / "form.pdf")
    build_mixed_form(pdf)
    with PDFAnalyzer(pdf) as az:
        fields = {f.field_name: f for f in az.analyze_fields()}

    assert fields["Approved"].field_type == "CheckBox"
    assert "Yes" in fields["Approved"].on_states

    assert fields["State"].field_type == "ComboBox"
    assert fields["State"].options == ["VIC", "NSW", "QLD", "WA"]

    assert fields["Subject"].field_type == "ListBox"
    assert fields["Subject"].options == ["Maths", "English", "Science"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/python -m pytest tests/test_field_types.py::test_analysis_captures_button_and_choice_metadata -v`
Expected: FAIL — `assert 'Yes' in []` (on_states empty).

- [ ] **Step 3: Populate the metadata during extraction**

In `pdf_analyzer.py`, inside the `else:` single-field branch, replace the `PDFField(...)` construction (lines 174-185) so it reads button/choice metadata first:

```python
                    on_states = []
                    options = []
                    if ftype in ("CheckBox", "RadioButton"):
                        try:
                            states = widget.button_states() or {}
                            normal = states.get("normal", []) or []
                            on_states = [s for s in normal if s != "Off"]
                        except (AttributeError, RuntimeError, TypeError):
                            on_states = []
                    elif ftype in ("ComboBox", "ListBox"):
                        try:
                            options = list(widget.choice_values or [])
                        except (AttributeError, RuntimeError, TypeError):
                            options = []

                    result.append(PDFField(
                        field_name=name,
                        field_type=ftype,
                        page=page_num,
                        length=max_len,
                        is_combed=is_combed,
                        combed_fields=[],  # Single-field combed: no sub-fields
                        rect=tuple(widget.rect),
                        current_value=widget.field_value or "",
                        is_critical=False,
                        excel_column=None,
                        on_states=on_states,
                        options=options,
                    ))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/bin/python -m pytest tests/test_field_types.py -v`
Expected: PASS (all field-type tests).

- [ ] **Step 5: Commit**

```bash
git add pdf_analyzer.py tests/test_field_types.py
git commit -m "feat: capture checkbox/radio on-states and choice options during analysis"
```

---

## Task 4: Pure value-normalization helpers

**Files:**
- Create: `field_values.py`
- Test: `tests/test_field_types.py`

- [ ] **Step 1: Write the failing tests**

```python
# add to tests/test_field_types.py
from pypdf.generic import NameObject
from field_values import normalize_button_value, normalize_choice_value


def test_checkbox_truthy_maps_to_on_state_nameobject():
    assert normalize_button_value("X", ["Yes"]) == NameObject("/Yes")
    assert normalize_button_value("yes", ["Yes"]) == NameObject("/Yes")
    assert normalize_button_value("TRUE", ["Yes"]) == NameObject("/Yes")
    assert normalize_button_value("1", ["Yes"]) == NameObject("/Yes")


def test_checkbox_falsey_maps_to_off():
    assert normalize_button_value("No", ["Yes"]) == NameObject("/Off")
    assert normalize_button_value("0", ["Yes"]) == NameObject("/Off")
    assert normalize_button_value("", ["Yes"]) == NameObject("/Off")


def test_checkbox_unrecognised_returns_none():
    assert normalize_button_value("maybe", ["Yes"]) is None


def test_radio_value_matches_one_of_several_states_case_insensitively():
    assert normalize_button_value("male", ["Male", "Female"]) == NameObject("/Male")
    assert normalize_button_value("FEMALE", ["Male", "Female"]) == NameObject("/Female")
    assert normalize_button_value("other", ["Male", "Female"]) is None


def test_choice_validates_against_options_case_insensitively():
    assert normalize_choice_value("nsw", ["VIC", "NSW"]) == ("NSW", True)
    assert normalize_choice_value(" VIC ", ["VIC", "NSW"]) == ("VIC", True)
    assert normalize_choice_value("Victoria", ["VIC", "NSW"]) == ("Victoria", False)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/bin/python -m pytest tests/test_field_types.py -k "checkbox or radio or choice" -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'field_values'`

- [ ] **Step 3: Implement the helpers**

```python
# field_values.py
"""Pure value→field-type translation for PDF form filling.

Checkboxes and radio buttons only fill when given a PDF name matching their
"on" appearance state (proven: a plain string never ticks a box). Choice
fields must match one of their defined options. These helpers translate a raw
spreadsheet cell into the right value, with no GUI or PDF-library state.
"""
from typing import List, Optional, Tuple
from pypdf.generic import NameObject

# Spreadsheet values that mean "ticked" / "not ticked" (lowercased, stripped).
TRUTHY = {"yes", "y", "true", "t", "1", "x", "✓", "✔", "on", "checked"}
FALSEY = {"no", "n", "false", "f", "0", "", "off", "unchecked", "nan"}


def normalize_button_value(raw, on_states: List[str]) -> Optional[NameObject]:
    """Map a spreadsheet value to a checkbox/radio appearance state.

    Single on-state (checkbox): truthy -> /<state>, falsey -> /Off.
    Multiple on-states (radio): value must match a state (case-insensitive)
        -> /<matched state>.
    Returns None when the value cannot be resolved; the caller should warn and
    leave the field untouched rather than guess.
    """
    s = str(raw).strip().lower()
    states = on_states or []

    if len(states) <= 1:
        # Checkbox semantics (default on-state "Yes" if none was detected).
        if s in TRUTHY:
            return NameObject("/" + (states[0] if states else "Yes"))
        if s in FALSEY:
            return NameObject("/Off")
        return None

    # Radio semantics: match the chosen option by export value.
    for state in states:
        if s == state.strip().lower():
            return NameObject("/" + state)
    return None


def normalize_choice_value(raw, options: List[str]) -> Tuple[str, bool]:
    """Resolve a dropdown/listbox value against its options.

    Returns (value_to_write, matched). On a case-insensitive/whitespace match
    the canonical option text is returned with matched=True. Otherwise the raw
    string is returned with matched=False so the caller can warn the user that
    the value is not one of the field's allowed options.
    """
    s = str(raw).strip()
    for opt in (options or []):
        if s.lower() == opt.strip().lower():
            return (opt, True)
    return (s, False)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/bin/python -m pytest tests/test_field_types.py -k "checkbox or radio or choice" -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add field_values.py tests/test_field_types.py
git commit -m "feat: add pure value-normalization helpers for buttons and choices"
```

---

## Task 5: Fill checkboxes/radios/choices in the generation pipeline

**Files:**
- Modify: `pdf_generator.py:3460-3563` (`_generate_single_pdf`)
- Test: `tests/test_field_types.py`

- [ ] **Step 1: Write the failing end-to-end test**

```python
# add to tests/test_field_types.py
import warnings
import pandas as pd
from pypdf import PdfReader
import fitz
from pdf_generator import BulkPDFGenerator


def _generate(pdf_path, out_path, fields, row_values):
    ctx = {
        "analyzed_fields": fields,
        "combed_padding": False,
        "combed_align": "left",
        "pdf_fields": [f.field_name for f in fields],
        "_reader": PdfReader(pdf_path),
    }
    app = BulkPDFGenerator.__new__(BulkPDFGenerator)  # real method, no GUI
    warnings_out = app._generate_single_pdf(ctx, pd.Series(row_values), out_path)
    ctx["_reader"].close()
    return warnings_out


def test_checkbox_fills_with_natural_value(tmp_path):
    pdf = str(tmp_path / "form.pdf"); out = str(tmp_path / "out.pdf")
    build_mixed_form(pdf)
    with PDFAnalyzer(pdf) as az:
        fields = az.analyze_fields()
    _generate(pdf, out, fields, {
        "Student_Name": "Jane Smith", "Approved": "X",
        "State": "NSW", "Subject": "English",
    })
    doc = fitz.open(out)
    vals = {w.field_name: w.field_value for w in doc[0].widgets()}
    doc.close()
    assert vals["Approved"] == "Yes"        # ticked, not "Off"
    assert vals["Student_Name"] == "Jane Smith"
    assert vals["State"] == "NSW"
    assert vals["Subject"] == "English"


def test_invalid_choice_value_is_reported(tmp_path):
    pdf = str(tmp_path / "form.pdf"); out = str(tmp_path / "out.pdf")
    build_mixed_form(pdf)
    with PDFAnalyzer(pdf) as az:
        fields = az.analyze_fields()
    warns = _generate(pdf, out, fields, {
        "Student_Name": "X", "Approved": "no",
        "State": "Victoria",  # not a valid option
        "Subject": "Maths",
    })
    assert any("State" in w and "Victoria" in w for w in warns)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/bin/python -m pytest tests/test_field_types.py -k "fills_with_natural or invalid_choice" -v`
Expected: FAIL — `assert 'Off' == 'Yes'` (checkbox not filled) and `_generate_single_pdf` returns `None` (no warnings list).

- [ ] **Step 3: Rework `_generate_single_pdf` to branch by field type and return warnings**

In `pdf_generator.py`, add the import near the other module imports (after line 178):

```python
from field_values import normalize_button_value, normalize_choice_value
```

Replace the value-collection-and-write portion of `_generate_single_pdf` (the body from `field_values = {}` through the page-write loop, lines 3484-3559) with the version below. It keeps the existing text/comb handling and adds button and choice handling, returning a list of human-readable warnings:

```python
        field_values = {}      # text + valid choice values (plain strings)
        button_values = {}     # checkbox/radio values (NameObject)
        warnings_out = []      # per-field problems to report to the user

        if ctx['analyzed_fields']:
            combed_filler = CombedFieldFiller(settings={
                'padding': ctx['combed_padding'],
                'align': ctx['combed_align'],
            })
            row_raw_lower = {str(col).lower(): val for col, val in row_data.items()}

            for field in ctx['analyzed_fields']:
                key = (field.excel_column or field.field_name).lower()
                raw_val = row_raw_lower.get(key)
                if raw_val is None:
                    continue

                ftype = field.field_type

                if ftype == 'Signature':
                    if str(raw_val).strip():
                        warnings_out.append(
                            f"{field.field_name}: signature fields cannot be "
                            f"auto-filled (skipped)")
                    continue

                if ftype in ('CheckBox', 'RadioButton'):
                    name_val = normalize_button_value(raw_val, field.on_states)
                    if name_val is None:
                        if str(raw_val).strip().lower() not in ('', 'nan'):
                            warnings_out.append(
                                f"{field.field_name}: could not interpret "
                                f"'{raw_val}' as a tick value (left unchanged)")
                        continue
                    button_values[field.field_name] = name_val
                    continue

                if ftype in ('ComboBox', 'ListBox'):
                    value, matched = normalize_choice_value(raw_val, field.options)
                    if not value:
                        continue
                    if not matched and field.options:
                        warnings_out.append(
                            f"{field.field_name}: '{value}' is not one of the "
                            f"allowed options {field.options}")
                    field_values[field.field_name] = value
                    continue

                # Text / combed text (unchanged behaviour)
                value = self.format_value_tab3(raw_val, data_type=field.data_type)
                if not value:
                    continue
                field_values.update(combed_filler.fill_field(field, value))

        else:
            row_dict_lower = {str(col).lower(): val for col, val in row_data.items()}
            for pdf_field in ctx['pdf_fields']:
                pdf_field_lower = pdf_field.lower()
                if pdf_field_lower in row_dict_lower:
                    inferred_type = "date" if any(
                        token in pdf_field_lower for token in _DATE_KEYWORDS
                    ) else "text"
                    val = self.format_value_tab3(
                        row_dict_lower[pdf_field_lower], data_type=inferred_type)
                    field_values[pdf_field] = val

        # Split comb single-fields out of the text bucket (unchanged logic).
        comb_field_names = set()
        if ctx['analyzed_fields']:
            for f in ctx['analyzed_fields']:
                if f.is_combed and not f.combed_fields:
                    comb_field_names.add(f.field_name)

        regular_values = {k: v for k, v in field_values.items()
                          if k not in comb_field_names}
        comb_values = {k: v for k, v in field_values.items()
                       if k in comb_field_names}

        for page in writer.pages:
            if regular_values:
                writer.update_page_form_field_values(
                    page, regular_values, auto_regenerate=False)
            if comb_values:
                writer.update_page_form_field_values(
                    page, comb_values, auto_regenerate=True)
            if button_values:
                # NameObject + auto_regenerate=True is the only combination that
                # actually ticks a checkbox/radio (proven 2026-06-19).
                writer.update_page_form_field_values(
                    page, button_values, auto_regenerate=True)

        with open(output_path, 'wb') as f:
            writer.write(f)

        return warnings_out
```

- [ ] **Step 4: Run the end-to-end tests to verify they pass**

Run: `venv/bin/python -m pytest tests/test_field_types.py -k "fills_with_natural or invalid_choice" -v`
Expected: PASS — `Approved == 'Yes'`, and the invalid-choice warning is returned.

- [ ] **Step 5: Run the full suite**

Run: `venv/bin/python -m pytest tests/ -q`
Expected: all pass (no regression in text/comb/date behaviour).

- [ ] **Step 6: Commit**

```bash
git add pdf_generator.py tests/test_field_types.py
git commit -m "feat: reliably fill checkbox, radio, and choice fields during generation"
```

---

## Task 6: Surface fill warnings in the generation summary

**Files:**
- Modify: `pdf_generator.py:3419-3450` (the per-row loop in `run_generation_tab3`)
- Test: covered by Task 5's `test_invalid_choice_value_is_reported` (unit level); this task wires the return value into the existing summary that the user sees.

- [ ] **Step 1: Collect warnings from each row**

In `run_generation_tab3`, change the success path (around line 3420) so the warnings returned by `_generate_single_pdf` are gathered into the existing `error_details` list (which `generation_complete_tab3` already shows):

```python
                    try:
                        row_warnings = self._generate_single_pdf(ctx, row, output_path)
                        success_count += 1
                        status_text = f"Created: {filename}"
                        for w in (row_warnings or []):
                            error_details.append(f"{'_'.join(name_parts)}: {w}")
                    except Exception as e:
```

- [ ] **Step 2: Verify the existing generation flow still runs**

Run: `venv/bin/python -m pytest tests/ -q`
Expected: all pass. (`run_generation_tab3` is exercised indirectly; the change only appends strings to an existing list.)

- [ ] **Step 3: Manual smoke check (GUI logic, no clicking)**

Run from source: `venv/bin/python pdf_generator.py`, analyze a PDF that has a checkbox, load a sheet with a checkbox column, generate, and confirm the completion dialog lists any unfillable/invalid values. Confirm no macOS modal freeze (per project rule, verify GUI dialog live on macOS).

- [ ] **Step 4: Commit**

```bash
git add pdf_generator.py
git commit -m "feat: report unfillable and invalid field values in generation summary"
```

---

## Task 7: Show field type and options in the audit dialog

**Files:**
- Modify: `pdf_generator.py:660-699` (`FieldTypeAuditDialog` row builder)

- [ ] **Step 1: Display the real type and options for non-text fields**

The audit dialog already shows a read-only label for non-editable types (lines 671-676). Extend that label so choice fields show their options and buttons show they are tick fields, giving the user the information needed to map their spreadsheet correctly:

```python
            else:
                ftype_var = tk.StringVar(value=field.field_type)
                detail = field.field_type
                if field.options:
                    detail += f"  ({', '.join(field.options[:4])}{'…' if len(field.options) > 4 else ''})"
                elif field.on_states:
                    detail += "  (tick: Yes/No, X, 1/0)"
                lbl_ftype = tk.Label(row, text=detail, font=(ff, 10),
                                     fg=C['text_secondary'], bg=bg, width=28,
                                     anchor=tk.W, autostyle=False)
                lbl_ftype.pack(side=tk.LEFT, padx=(2, 0))
            self.ftype_vars.append(ftype_var)
```

- [ ] **Step 2: Manual verification (no clicking)**

Per project rule, instantiate `BulkPDFGenerator(tk.Tk())` with `root.withdraw()`, open the audit dialog on a mixed-field PDF, and assert the label text for `State` includes its options. Confirm no modal blocks.

- [ ] **Step 3: Commit**

```bash
git add pdf_generator.py
git commit -m "feat: show choice options and tick hints in field audit dialog"
```

---

## Self-Review

**1. Spec coverage:**
- Checkbox/radio reliable fill → Tasks 1, 3, 4, 5. ✅
- Choice validation → Tasks 4, 5. ✅
- Signature detection/skip → Task 5. ✅
- Surface problems to the user → Tasks 5, 6. ✅
- Make field types/options visible for mapping → Task 7. ✅
- Tests guarding all of it → Tasks 1–5. ✅

**2. Placeholder scan:** No TODO/TBD/"implement later" placeholders; every code step contains the real content. All strings are ASCII.

**3. Type consistency:** `on_states` / `options` names match across `models.py`, `pdf_analyzer.py`, `field_values.py`, and `pdf_generator.py`. `normalize_button_value(raw, on_states)` and `normalize_choice_value(raw, options) -> (value, matched)` signatures are used consistently. `_generate_single_pdf` now returns `list[str]`; Task 6 consumes that return value (the previous version returned `None` — no other caller depends on the old return).

---

## Manual verification (post-implementation)

1. **Radio buttons:** obtain a real PDF with a radio group (e.g. a government form). Analyze it, confirm `on_states` lists the export values, map a spreadsheet column to it, generate, and confirm the correct option is selected in Acrobat/Preview. This is the one path no automated fixture covers.
2. **Editable vs non-editable dropdowns & multi-select list boxes:** confirm valid values fill and invalid values produce the warning rather than silent junk.
3. **Real VCAA form regression:** re-run an existing VCAA template end-to-end to confirm text and combed fields are unchanged.
