# Reliability & Confidence Sweep — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate the silent-corruption and crash paths found in the July 2026 quality review, so that what a teacher sees in the app matches what lands in the generated PDFs.

**Architecture:** Work flows in dependency order — the PDF analyzer produces the field data that every downstream stage (audit dialog, spreadsheet export, mapping, generation) consumes, so analyzer correctness lands first. Each stage is independently testable and leaves the app working; no stage depends on a later one. Value-translation and export changes then build on the corrected field data, followed by import integrity, then the user-facing trust surfaces (preview and results panel).

**Tech Stack:** Python 3.10+, PyMuPDF (fitz) for analysis, pypdf for filling, pandas + openpyxl for spreadsheets, tkinter + ttkbootstrap for GUI, pytest for tests.

## Global Constraints

- **Run tests with:** `venv/bin/python -m pytest tests/ -v` — system `python3` lacks project deps.
- **Never instantiate `tk.Tk()` in automated tests** — CI (Linux) is headless. Guard GUI logic with `inspect.getsource` structural tests, following the existing pattern in `tests/test_performance.py`.
- **Headless method tests** use `BulkPDFGenerator.__new__(BulkPDFGenerator)` to skip `__init__`.
- **PyMuPDF thread safety:** `fitz.Document` is NOT thread-safe. Never move PyMuPDF calls off the main thread.
- **macOS modal rule:** `tkinter.messagebox.*` can open *behind* the main window on macOS — invisible but modal, freezing the app. `parent=` does not reliably fix it. Report post-action outcomes inline (status label / panel), never via messagebox.
- **`tests/test_data_fidelity.py` asserts `format_value_tab3(...)` and `data_type` sit on the SAME source line** via `inspect.getsource`. Do not split that call across lines.
- **Working branch:** `test`. Commit after every task. Do not merge to `main` without explicit user confirmation.
- **Minimum footprint:** touch only what each task names. Do not refactor adjacent code.

## Field type strings (PyMuPDF `widget.field_type_string`)

These exact strings are used throughout. Do not invent variants.

`Text` · `CheckBox` · `RadioButton` · `ComboBox` · `ListBox` · `Signature` · `Button` (push button)

The app additionally synthesises `Text-Combed` for comb/MaxLen text fields.

---

# Stage 1 — Extraction correctness

The analyzer is the source of truth for every later stage. Three defects live here: a crash on paired-option dropdowns, radio groups that decompose into duplicate broken fields, and comb-grouping that can swallow non-text widgets.

---

### Task 1: Test fixtures for radio groups and paired-option dropdowns

The existing fixture (`tests/_form_fixture.py`) cannot author radio groups, and its docstring says so. That gap is exactly why the radio bug shipped. A hand-authored PDF byte stream *can* express a radio group, and has been verified to round-trip through both PyMuPDF and pypdf.

**Files:**
- Modify: `tests/_form_fixture.py`
- Test: `tests/test_fixtures.py` (create)

**Interfaces:**
- Produces: `build_radio_form(path: str) -> None` — writes a PDF with one radio group named `Gender`, two kid widgets with on-states `Male` and `Female`.
- Produces: `build_paired_choice_form(path: str) -> None` — writes a PDF with one ComboBox named `State` whose `/Opt` array holds `(export, display)` pairs.

- [ ] **Step 1: Add both fixture builders to `tests/_form_fixture.py`**

Append to the file (keep `build_mixed_form` unchanged), and update the module docstring's claim that radio groups cannot be authored:

```python
def build_radio_form(path: str) -> None:
    """Author a PDF containing a real radio-button group.

    PyMuPDF's add_widget() cannot create a radio group (it needs a
    pre-existing parent/kids structure), so the PDF bytes are written directly.
    The group 'Gender' has two kid widgets whose on-states are 'Male' and
    'Female' — the shape that broke analysis: every kid reports the *group*
    field name but only its *own* export value from button_states().
    """
    objs = {
        1: "<< /Type /Catalog /Pages 2 0 R /AcroForm << /Fields [ 6 0 R ] "
           "/DA (/Helv 0 Tf 0 g) >> >>",
        2: "<< /Type /Pages /Kids [ 3 0 R ] /Count 1 >>",
        3: "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] "
           "/Resources << /Font << /Helv 5 0 R >> >> /Contents 4 0 R "
           "/Annots [ 7 0 R 8 0 R ] >>",
        5: "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        # /Ff 32768 = bit 16 (Radio)
        6: "<< /FT /Btn /Ff 32768 /T (Gender) /V /Off /Kids [ 7 0 R 8 0 R ] >>",
        7: "<< /Type /Annot /Subtype /Widget /Parent 6 0 R /Rect [50 120 70 140] "
           "/F 4 /AS /Off /AP << /N << /Male 9 0 R /Off 10 0 R >> >> >>",
        8: "<< /Type /Annot /Subtype /Widget /Parent 6 0 R /Rect [50 80 70 100] "
           "/F 4 /AS /Off /AP << /N << /Female 9 0 R /Off 10 0 R >> >> >>",
    }

    out = bytearray(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
    offsets = {}

    def add(num, body):
        offsets[num] = len(out)
        out.extend(f"{num} 0 obj\n{body}\nendobj\n".encode("latin-1"))

    def add_stream(num, dict_extra, stream: bytes):
        offsets[num] = len(out)
        out.extend(
            f"{num} 0 obj\n<< {dict_extra} /Length {len(stream)} >>\nstream\n".encode("latin-1")
        )
        out.extend(stream)
        out.extend(b"\nendstream\nendobj\n")

    for n in (1, 2, 3):
        add(n, objs[n])
    add_stream(4, "", b"BT /Helv 10 Tf 50 160 Td (Gender) Tj ET")
    for n in (5, 6, 7, 8):
        add(n, objs[n])
    add_stream(9, "/Type /XObject /Subtype /Form /BBox [0 0 20 20]",
               b"q 0 0 0 rg 5 5 10 10 re f Q")   # "on" appearance
    add_stream(10, "/Type /XObject /Subtype /Form /BBox [0 0 20 20]",
               b"q 1 1 1 rg 0 0 20 20 re f Q")   # "off" appearance

    xref_pos = len(out)
    max_num = 10
    out.extend(f"xref\n0 {max_num + 1}\n".encode("latin-1"))
    out.extend(b"0000000000 65535 f \n")
    for n in range(1, max_num + 1):
        out.extend(f"{offsets[n]:010d} 00000 n \n".encode("latin-1"))
    out.extend(
        f"trailer\n<< /Size {max_num + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n".encode("latin-1")
    )

    with open(path, "wb") as f:
        f.write(bytes(out))


def build_paired_choice_form(path: str) -> None:
    """Author a PDF with a dropdown whose /Opt holds (export, display) pairs.

    Government forms routinely do this — display 'Victoria', export 'VIC'.
    PyMuPDF then returns choice_values as a list of TUPLES, which crashed
    field analysis before the flattening fix.
    """
    doc = fitz.open()
    page = doc.new_page(width=400, height=300)

    w = fitz.Widget()
    w.field_name = "State"
    w.field_type = fitz.PDF_WIDGET_TYPE_COMBOBOX
    w.rect = fitz.Rect(50, 50, 250, 70)
    w.choice_values = ["VIC", "NSW"]
    annot = page.add_widget(w)

    doc.xref_set_key(
        annot.xref, "Opt",
        "[ [ (VIC) (Victoria) ] [ (NSW) (New South Wales) ] ]",
    )
    doc.save(path)
    doc.close()
```

- [ ] **Step 2: Write a test proving the fixtures have the shape we claim**

Create `tests/test_fixtures.py`:

```python
"""The fixtures must actually reproduce the broken shapes, or the
regression tests that use them prove nothing."""
import fitz
from pypdf import PdfReader

from tests._form_fixture import build_radio_form, build_paired_choice_form


def test_radio_fixture_has_one_group_with_two_kids(tmp_path):
    pdf = str(tmp_path / "radio.pdf")
    build_radio_form(pdf)

    doc = fitz.open(pdf)
    widgets = list(doc.load_page(0).widgets())
    doc.close()

    # Two widgets, SAME field name — the shape that produced duplicate fields.
    assert len(widgets) == 2
    assert [w.field_name for w in widgets] == ["Gender", "Gender"]
    assert all(w.field_type_string == "RadioButton" for w in widgets)

    # Each kid reports ONLY its own on-state.
    states = [
        [s for s in (w.button_states() or {}).get("normal", []) if s != "Off"]
        for w in widgets
    ]
    assert states == [["Male"], ["Female"]]


def test_radio_fixture_is_fillable_by_pypdf(tmp_path):
    pdf = str(tmp_path / "radio.pdf")
    build_radio_form(pdf)
    fields = PdfReader(pdf).get_fields()
    assert "Gender" in fields
    assert str(fields["Gender"]["/FT"]) == "/Btn"


def test_paired_choice_fixture_returns_tuples(tmp_path):
    pdf = str(tmp_path / "paired.pdf")
    build_paired_choice_form(pdf)

    doc = fitz.open(pdf)
    widget = next(iter(doc.load_page(0).widgets()))
    values = widget.choice_values
    doc.close()

    # PyMuPDF hands back (export, display) TUPLES — not strings.
    assert values == [("VIC", "Victoria"), ("NSW", "New South Wales")]
```

- [ ] **Step 3: Run the fixture tests**

Run: `venv/bin/python -m pytest tests/test_fixtures.py -v`
Expected: all 3 PASS. If `test_paired_choice_fixture_returns_tuples` fails with a list of plain strings, the installed PyMuPDF flattens pairs itself — stop and report, because Task 2's premise would then be wrong.

- [ ] **Step 4: Update the stale docstring in `tests/_form_fixture.py`**

Replace the module docstring's radio claim:

```python
"""Authors PDFs with fillable field types, for analyzer and end-to-end fill tests.

build_mixed_form   — text, checkbox, combobox, listbox (via PyMuPDF)
build_radio_form   — a real radio group (hand-written PDF; PyMuPDF's
                     add_widget cannot author the parent/kids structure)
build_paired_choice_form — dropdown with (export, display) option pairs
"""
```

- [ ] **Step 5: Commit**

```bash
git add tests/_form_fixture.py tests/test_fixtures.py
git commit -m "test: add radio-group and paired-option PDF fixtures"
```

---

### Task 2: Flatten choice options so paired-`/Opt` dropdowns stop crashing analysis

Any PDF whose dropdown uses export/display pairs currently fails analysis outright with `TypeError: sequence item 0: expected str instance, tuple found`, surfaced to the teacher as "Failed to analyze PDF". The export value is the one that must be written into the PDF.

**Files:**
- Modify: `pdf_analyzer.py:183-187`
- Test: `tests/test_field_types.py`

**Interfaces:**
- Produces: `PDFAnalyzer._read_options(widget) -> List[str]` — static, returns flat export-value strings.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_field_types.py`:

```python
def test_paired_option_dropdown_analyses_to_export_values(tmp_path):
    """A dropdown with (export, display) pairs must analyse to flat export
    strings. Before the fix, PyMuPDF's tuples reached PDFField.options and
    blew up the audit dialog's ", ".join(...) — killing the whole analysis."""
    from tests._form_fixture import build_paired_choice_form

    pdf = str(tmp_path / "paired.pdf")
    build_paired_choice_form(pdf)

    with PDFAnalyzer(pdf) as analyzer:
        fields = analyzer.analyze_fields()

    state = next(f for f in fields if f.field_name == "State")
    assert state.options == ["VIC", "NSW"]
    assert all(isinstance(o, str) for o in state.options)
    # The audit dialog does exactly this — it must not raise.
    assert ", ".join(state.options) == "VIC, NSW"
```

- [ ] **Step 2: Run it and watch it fail**

Run: `venv/bin/python -m pytest tests/test_field_types.py::test_paired_option_dropdown_analyses_to_export_values -v`
Expected: FAIL — `options` contains tuples, so the `isinstance(o, str)` assertion (or the join) fails.

- [ ] **Step 3: Add the flattening helper to `pdf_analyzer.py`**

Insert this method into `PDFAnalyzer`, directly above `_get_widget_maxlen`:

```python
    @staticmethod
    def _read_options(widget) -> List[str]:
        """Choice (dropdown/listbox) options as flat export-value strings.

        PyMuPDF returns a list of (export, display) TUPLES when the PDF's
        /Opt array holds pairs — routine in government forms (display
        "Victoria", export "VIC"). The export value is what must be written
        into the PDF, and a tuple here crashed every consumer downstream.
        """
        try:
            raw = widget.choice_values or []
        except (AttributeError, RuntimeError, TypeError):
            return []

        options = []
        for opt in raw:
            if isinstance(opt, (tuple, list)):
                options.append(str(opt[0]) if opt else "")
            else:
                options.append(str(opt))
        return options

    @staticmethod
    def _read_on_states(widget) -> List[str]:
        """Checkbox/radio 'on' appearance states for a single widget.

        A radio kid reports only its OWN export value here — the group's full
        set is assembled in _merge_widgets_by_name().
        """
        try:
            states = widget.button_states() or {}
            normal = states.get("normal", []) or []
            return [str(s) for s in normal if s != "Off"]
        except (AttributeError, RuntimeError, TypeError):
            return []
```

- [ ] **Step 4: Use the helpers in `_detect_combed_fields`**

Replace the on_states/options block (currently `pdf_analyzer.py:174-187`):

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
```

with:

```python
                    on_states = []
                    options = []
                    if ftype in ("CheckBox", "RadioButton"):
                        on_states = self._read_on_states(widget)
                    elif ftype in ("ComboBox", "ListBox"):
                        options = self._read_options(widget)
```

- [ ] **Step 5: Run the test and the full suite**

Run: `venv/bin/python -m pytest tests/ -v`
Expected: the new test PASSES; all previously passing tests still pass (97+ passed).

- [ ] **Step 6: Commit**

```bash
git add pdf_analyzer.py tests/test_field_types.py
git commit -m "fix: flatten export/display option pairs so paired-Opt dropdowns analyse"
```

---

### Task 3: Merge same-named widgets — fixes radio groups and duplicate fields

`page.widgets()` yields one widget per radio *kid*, all carrying the group's field name. The analyzer emits one `PDFField` per kid, each with a single-element `on_states`, so `normalize_button_value` applies *checkbox* semantics: typing the option name ("Male") warns and fills nothing, while typing "Yes" makes an arbitrary option win. The same duplication hits any field whose widget appears on multiple pages.

The fix collapses widgets by field name *before* comb detection, pooling each group's on-states.

**Files:**
- Modify: `pdf_analyzer.py:41-57` (`analyze_fields`), `:59-204` (`_detect_combed_fields`), `:227-259` (`_looks_like_comb_row`)
- Test: `tests/test_field_types.py`

**Interfaces:**
- Consumes: `_read_on_states`, `_read_options` from Task 2.
- Produces: `PDFAnalyzer._merge_widgets_by_name(all_widgets: List[dict]) -> List[dict]` — one record per unique field name. Each record: `{'name': str, 'widget': fitz.Widget, 'page_num': int, 'field_type': str, 'on_states': List[str], 'options': List[str]}`.
- Produces: `_detect_combed_fields(records: List[dict]) -> List[PDFField]` — signature changes from widgets to records.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_field_types.py`:

```python
def test_radio_group_becomes_one_field_with_all_on_states(tmp_path):
    """A radio group must analyse to ONE field carrying EVERY option.

    Before the fix: two 'Gender' fields, each with on_states=['Male'] or
    ['Female']. len(on_states)<=1 meant normalize_button_value applied
    checkbox semantics — typing 'Male' filled nothing, typing 'Yes' let an
    arbitrary option win."""
    from tests._form_fixture import build_radio_form

    pdf = str(tmp_path / "radio.pdf")
    build_radio_form(pdf)

    with PDFAnalyzer(pdf) as analyzer:
        fields = analyzer.analyze_fields()

    genders = [f for f in fields if f.field_name == "Gender"]
    assert len(genders) == 1, "radio group must not fan out into one field per button"
    assert genders[0].field_type == "RadioButton"
    assert sorted(genders[0].on_states) == ["Female", "Male"]


def test_radio_group_fills_the_chosen_option_end_to_end(tmp_path):
    """The whole point: a teacher types 'Female' and that button is selected."""
    from pypdf import PdfReader
    from tests._form_fixture import build_radio_form
    from field_values import normalize_button_value

    pdf = str(tmp_path / "radio.pdf")
    build_radio_form(pdf)

    with PDFAnalyzer(pdf) as analyzer:
        field = next(f for f in analyzer.analyze_fields() if f.field_name == "Gender")

    name_val = normalize_button_value("Female", field.on_states)
    assert name_val is not None, "'Female' must resolve against the group's on-states"

    from pypdf import PdfWriter
    out = str(tmp_path / "filled.pdf")
    writer = PdfWriter(clone_from=pdf)
    for page in writer.pages:
        writer.update_page_form_field_values(
            page, {"Gender": name_val}, auto_regenerate=True)
    with open(out, "wb") as fh:
        writer.write(fh)

    assert str(PdfReader(out).get_fields()["Gender"]["/V"]) == "/Female"


def test_same_field_on_two_pages_yields_one_field(tmp_path):
    """A field whose widget repeats on several pages produced duplicate rows,
    duplicate spreadsheet columns, and a header pandas mangles to 'Name.1'."""
    import fitz

    pdf = str(tmp_path / "twopage.pdf")
    doc = fitz.open()
    for _ in range(2):
        page = doc.new_page(width=300, height=200)
        w = fitz.Widget()
        w.field_name = "Student_Name"
        w.field_type = fitz.PDF_WIDGET_TYPE_TEXT
        w.rect = fitz.Rect(50, 50, 250, 70)
        page.add_widget(w)
    doc.save(pdf)
    doc.close()

    with PDFAnalyzer(pdf) as analyzer:
        fields = analyzer.analyze_fields()

    assert [f.field_name for f in fields].count("Student_Name") == 1


def test_numbered_checkbox_row_is_not_merged_into_a_comb(tmp_path):
    """Checkboxes named Q1_1..Q1_4 on one line satisfy the comb heuristics by
    name and geometry. Merging them would write one CHARACTER per checkbox —
    they never tick, and the value is destroyed."""
    import fitz

    pdf = str(tmp_path / "checkrow.pdf")
    doc = fitz.open()
    page = doc.new_page(width=400, height=200)
    for i in range(1, 5):
        w = fitz.Widget()
        w.field_name = f"Q1_{i}"
        w.field_type = fitz.PDF_WIDGET_TYPE_CHECKBOX
        w.rect = fitz.Rect(50 + i * 30, 100, 70 + i * 30, 120)
        page.add_widget(w)
    doc.save(pdf)
    doc.close()

    with PDFAnalyzer(pdf) as analyzer:
        fields = analyzer.analyze_fields()

    assert not any(f.is_combed for f in fields)
    assert sorted(f.field_name for f in fields) == ["Q1_1", "Q1_2", "Q1_3", "Q1_4"]
    assert all(f.field_type == "CheckBox" for f in fields)
```

- [ ] **Step 2: Run them and watch them fail**

Run: `venv/bin/python -m pytest tests/test_field_types.py -v -k "radio or two_pages or checkbox_row"`
Expected: FAIL — two `Gender` fields; two `Student_Name` fields; the checkbox row merges into a `Text-Combed` field.

- [ ] **Step 3: Add `_merge_widgets_by_name` to `PDFAnalyzer`**

Insert directly above `_detect_combed_fields`:

```python
    def _merge_widgets_by_name(self, all_widgets: List[dict]) -> List[dict]:
        """Collapse widgets that share a field name into one record per field.

        A PDF radio group is authored as one widget per button, and every one
        of them reports the GROUP's field name — while button_states() reports
        only that button's own export value. Emitting a PDFField per widget
        therefore produced duplicate fields each holding a single on-state,
        which made a radio group behave like a broken checkbox. The same
        duplication hit any field repeated across pages (a signature on every
        page, a header field on each sheet).

        Pooling the on-states here is what lets normalize_button_value() see
        len(on_states) > 1 and apply radio semantics.

        The first widget for a name supplies the representative geometry
        (page, rect) used by the visual preview.
        """
        merged = {}
        order = []

        for item in all_widgets:
            widget = item['widget']
            name = widget.field_name
            if not name:
                continue

            ftype = widget.field_type_string or 'Text'

            record = merged.get(name)
            if record is None:
                record = {
                    'name': name,
                    'widget': widget,          # first widget = geometry source
                    'page_num': item['page_num'],
                    'field_type': ftype,
                    'on_states': [],
                    'options': [],
                }
                merged[name] = record
                order.append(name)

            if ftype in ("CheckBox", "RadioButton"):
                for state in self._read_on_states(widget):
                    if state not in record['on_states']:
                        record['on_states'].append(state)
            elif ftype in ("ComboBox", "ListBox") and not record['options']:
                record['options'] = self._read_options(widget)

        return [merged[name] for name in order]
```

- [ ] **Step 4: Feed records into `_detect_combed_fields` from `analyze_fields`**

In `analyze_fields`, replace:

```python
        # Detect and group combed fields
        fields = self._detect_combed_fields(all_widgets)

        return fields
```

with:

```python
        # Collapse same-named widgets (radio groups, multi-page fields) first,
        # then group comb character-boxes.
        records = self._merge_widgets_by_name(all_widgets)
        fields = self._detect_combed_fields(records)

        return fields
```

- [ ] **Step 5: Rewrite `_detect_combed_fields` to consume records**

Replace the whole method body (`pdf_analyzer.py:59-204`) with:

```python
    def _detect_combed_fields(self, records: List[dict]) -> List[PDFField]:
        """
        Group combed fields by base name pattern.

        Takes the deduplicated records from _merge_widgets_by_name().

        Supported patterns:
        - Field_Name[0], Field_Name[1], ... (bracketed)
        - FieldName_0, FieldName_1, ...     (underscore)
        - FieldName0, FieldName1, ...       (sequential)
        """
        groups = defaultdict(list)

        for record in records:
            name = record['name']
            page_num = record['page_num']

            # Try pattern 1: Field[N]
            match = re.match(r'^(.+?)\[(\d+)\]$', name)
            if match:
                groups[match.group(1)].append(
                    (int(match.group(2)), name, record, page_num))
                continue

            # Try pattern 2: Field_N
            match = re.match(r'^(.+?)_(\d+)$', name)
            if match:
                groups[(match.group(1), '_')].append(
                    (int(match.group(2)), name, record, page_num))
                continue

            # Try pattern 3: FieldN (no separator, e.g. StudentNumber0)
            # But NOT "Provision 1" — space before number means separate fields
            match = re.match(r'^(.+?)(\d+)$', name)
            if match:
                potential_base = match.group(1)
                if potential_base.endswith(' '):
                    groups[name].append((0, name, record, page_num))
                    continue
                groups[(potential_base, '')].append(
                    (int(match.group(2)), name, record, page_num))
                continue

            # Not a pattern - single field
            groups[name].append((0, name, record, page_num))

        result = []
        for base_key, items in groups.items():
            if isinstance(base_key, tuple):
                base_name, _separator = base_key
            else:
                base_name = base_key

            items.sort(key=lambda x: x[0])

            treat_as_combed = len(items) > 1 and self._is_sequential(items)

            # A comb is always made of plain Text boxes. A horizontal row of
            # numbered CHECKBOXES (Q1_1…Q1_4) passes both the name and the
            # geometry heuristics — merging it would write one character per
            # checkbox, which never ticks and destroys the value.
            if treat_as_combed:
                treat_as_combed = all(
                    item[2]['field_type'] == 'Text' for item in items)

            # Guard the loose suffix patterns ('Field_N', 'FieldN' — tuple keys)
            # against false grouping: real comb character-boxes sit on a single
            # horizontal line, whereas genuinely separate sequential fields
            # (e.g. Address_1 / Address_2 stacked on different lines) do not.
            # Bracketed 'Field[N]' fields (str key) are the canonical comb
            # naming and are always treated as comb — they skip this check.
            if treat_as_combed and isinstance(base_key, tuple):
                treat_as_combed = self._looks_like_comb_row(items)

            if treat_as_combed:
                widget_0 = items[0][2]['widget']

                result.append(PDFField(
                    field_name=base_name,
                    field_type='Text-Combed',
                    page=items[0][3],
                    length=len(items),
                    is_combed=True,
                    combed_fields=[item[1] for item in items],
                    rect=tuple(widget_0.rect),
                    current_value=widget_0.field_value or "",
                    is_critical=False,
                    excel_column=None,
                ))
            else:
                for _index, name, record, page_num in items:
                    widget = record['widget']
                    ftype = record['field_type']
                    max_len = None
                    is_combed = False

                    # Detect single-field combed: Text field with MaxLen set
                    if ftype == 'Text':
                        try:
                            max_len_val = self._get_widget_maxlen(widget)
                            if max_len_val and max_len_val > 1:
                                max_len = max_len_val
                                is_combed = True
                                ftype = 'Text-Combed'
                        except (AttributeError, TypeError, ValueError):
                            pass

                    result.append(PDFField(
                        field_name=name,
                        field_type=ftype,
                        page=page_num,
                        length=max_len,
                        is_combed=is_combed,
                        combed_fields=[],
                        rect=tuple(widget.rect),
                        current_value=widget.field_value or "",
                        is_critical=False,
                        excel_column=None,
                        on_states=list(record['on_states']),
                        options=list(record['options']),
                    ))

        return result
```

- [ ] **Step 6: Fix `_looks_like_comb_row` — items now carry records, not widgets**

In `_looks_like_comb_row`, replace the geometry reads:

```python
        try:
            tops = [it[2].rect[1] for it in items]               # y0 of each box
            heights = [abs(it[2].rect[3] - it[2].rect[1]) for it in items]
        except (AttributeError, IndexError, TypeError):
            return True
```

with:

```python
        try:
            widgets = [it[2]['widget'] for it in items]
            tops = [w.rect[1] for w in widgets]                  # y0 of each box
            heights = [abs(w.rect[3] - w.rect[1]) for w in widgets]
        except (AttributeError, IndexError, KeyError, TypeError):
            return True
```

Also update its docstring arg line to: `items: List of (index, name, record, page_num) tuples.`

- [ ] **Step 7: Run the full suite**

Run: `venv/bin/python -m pytest tests/ -v`
Expected: the four new tests PASS. `tests/test_combed_detection.py` must still pass unchanged — if a comb test now fails, the type-gate is rejecting Text widgets and the `field_type` key is wrong; fix rather than weaken the test.

- [ ] **Step 8: Commit**

```bash
git add pdf_analyzer.py tests/test_field_types.py
git commit -m "fix: merge same-named widgets so radio groups pool their on-states"
```

---

### Task 4: Skip push buttons as data fields

A "Print Form" push button is currently extracted as a fillable field: it becomes an audit row, a spreadsheet column, and — if a teacher types in that column — goes down the text-fill path, where pypdf writes a `/V` into a push button. Signature fields are already skipped with a warning; `Button` deserves the same.

**Files:**
- Modify: `pdf_generator.py:3605-3610` (`_generate_single_pdf`)
- Test: `tests/test_field_types.py`

**Interfaces:**
- Consumes: `PDFField.field_type == 'Button'` from the analyzer (already produced — PyMuPDF's string for a push button).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_field_types.py`:

```python
def test_push_button_is_never_filled():
    """A 'Print Form' push button is not a data field. Writing a value into
    it can corrupt its appearance state — skip it like a signature."""
    from pdf_generator import BulkPDFGenerator

    app = BulkPDFGenerator.__new__(BulkPDFGenerator)
    src = inspect.getsource(app._generate_single_pdf)
    assert "'Button'" in src or '"Button"' in src, \
        "_generate_single_pdf must explicitly skip push-button fields"
```

Ensure `import inspect` is present at the top of `tests/test_field_types.py`.

- [ ] **Step 2: Run it and watch it fail**

Run: `venv/bin/python -m pytest tests/test_field_types.py::test_push_button_is_never_filled -v`
Expected: FAIL — no Button handling in the method.

- [ ] **Step 3: Skip Button in `_generate_single_pdf`**

Immediately after the `Signature` block, insert:

```python
                if ftype == 'Button':
                    # Push button (e.g. "Print Form") — an action control, not a
                    # data field. Writing a value can corrupt its /AS state.
                    continue
```

- [ ] **Step 4: Run the full suite**

Run: `venv/bin/python -m pytest tests/ -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add pdf_generator.py tests/test_field_types.py
git commit -m "fix: skip push-button fields during generation"
```

---

### Task 5: Anchor date-type guessing to word boundaries

`'date' in 'candidate number'` is true. A VCAA app meets "Candidate Number" constantly; if the teacher accepts the pre-selected "Date (DD/MM/YYYY)" in the audit dialog, candidate number `245` is silently converted to `01/09/1900` in every PDF. "Consolidated", "Updated" and "Mandated" trip it too.

**Files:**
- Modify: `pdf_generator.py:541-550`, `:3648-3650`
- Test: `tests/test_data_fidelity.py`

**Interfaces:**
- Produces: `_guess_data_type(field_name: str) -> str` — unchanged signature, corrected matching.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_data_fidelity.py`:

```python
def test_date_guess_ignores_words_that_merely_contain_date():
    """'candidate' contains 'date'. Mis-typing a candidate number as a Date
    converts 245 into 01/09/1900 in every generated PDF."""
    from pdf_generator import _guess_data_type

    for name in ["Candidate Number", "Candidate_No", "Consolidated Score",
                 "Updated By", "Mandated Hours"]:
        assert _guess_data_type(name) == "text", f"{name} must not be a Date"


def test_date_guess_still_catches_real_date_fields():
    from pdf_generator import _guess_data_type

    for name in ["Date of Birth", "DOB", "Birth_Date", "Birthdate",
                 "Expiry Date", "Date_Issued", "Due Date"]:
        assert _guess_data_type(name) == "date", f"{name} must be a Date"
```

- [ ] **Step 2: Run it and watch it fail**

Run: `venv/bin/python -m pytest tests/test_data_fidelity.py -v -k date_guess`
Expected: the first test FAILS ("Candidate Number" → `date`); the second PASSES.

- [ ] **Step 3: Anchor the match to a word boundary**

Replace `_guess_data_type` (`pdf_generator.py:544-550`):

```python
def _guess_data_type(field_name: str) -> str:
    """Guess a field's data type from its name. Returns 'text', 'number', or 'date'.

    The keyword must START at a word boundary. A plain substring test matched
    'date' inside 'candidate' (and 'updated', 'mandated', 'consolidated'),
    which silently converted candidate numbers into 1900s dates. No trailing
    boundary is required, so 'Birthdate' and 'DueDate' still match.
    """
    lower = field_name.lower().replace('_', ' ')
    pattern = r'\b(?:' + '|'.join(sorted(_DATE_KEYWORDS)) + r')'
    return 'date' if re.search(pattern, lower) else 'text'
```

`re` is already imported at the top of `pdf_generator.py`. `_DATE_KEYWORDS` stays as-is.

- [ ] **Step 4: Use the same rule in the no-analysis fallback path**

In `_generate_single_pdf`, replace (`pdf_generator.py:3648-3650`):

```python
                    inferred_type = "date" if any(
                        token in pdf_field_lower for token in _DATE_KEYWORDS
                    ) else "text"
```

with:

```python
                    inferred_type = _guess_data_type(pdf_field)
```

- [ ] **Step 5: Run the full suite**

Run: `venv/bin/python -m pytest tests/ -v`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add pdf_generator.py tests/test_data_fidelity.py
git commit -m "fix: anchor date-type guessing so 'Candidate Number' is not a date"
```

---

# Stage 2 — Generation integrity

The analyzer is now correct. These tasks stop generation from silently discarding or mis-filling data.

---

### Task 6: Warn when a comb field truncates a value

`combed_filler.fill_field` truncates over-long values with no signal. `validate_overflow` and `get_overflow_warnings` were written for exactly this and are **called from nowhere** in the app. "Papadopoulos-Nguyen" in a 12-box surname field becomes "Papadopoulo" and nobody finds out — a legal-name mismatch on exam paperwork.

**Files:**
- Modify: `pdf_generator.py:3637-3641` (`_generate_single_pdf`)
- Test: `tests/test_field_types.py`

**Interfaces:**
- Consumes: `CombedFieldFiller.validate_overflow(field, text) -> dict` with keys `is_valid`, `will_truncate`, `original_length`, `field_length`, `truncated_text`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_field_types.py`:

```python
def test_comb_truncation_produces_a_warning(tmp_path):
    """Silent truncation is data loss. The teacher must be told."""
    import pandas as pd
    from pypdf import PdfReader
    from pdf_generator import BulkPDFGenerator
    from models import PDFField

    # A 5-box comb field, given a 9-character value.
    field = PDFField(
        field_name="Surname",
        field_type="Text-Combed",
        page=1,
        length=5,
        is_combed=True,
        combed_fields=[f"Surname[{i}]" for i in range(5)],
        rect=(0, 0, 10, 10),
        excel_column="Surname",
    )

    pdf = str(tmp_path / "comb.pdf")
    import fitz
    doc = fitz.open()
    page = doc.new_page(width=300, height=200)
    for i in range(5):
        w = fitz.Widget()
        w.field_name = f"Surname[{i}]"
        w.field_type = fitz.PDF_WIDGET_TYPE_TEXT
        w.rect = fitz.Rect(20 + i * 20, 50, 38 + i * 20, 70)
        page.add_widget(w)
    doc.save(pdf)
    doc.close()

    app = BulkPDFGenerator.__new__(BulkPDFGenerator)
    reader = PdfReader(pdf)
    ctx = {
        '_reader': reader,
        'analyzed_fields': [field],
        'pdf_fields': [],
        'combed_padding': False,
        'combed_align': 'left',
    }
    row = pd.Series({"Surname": "Nguyenson"})   # 9 chars into 5 boxes
    warnings = app._generate_single_pdf(ctx, row, str(tmp_path / "out.pdf"))
    reader.close()

    assert warnings, "truncation must produce a warning"
    joined = " ".join(warnings)
    assert "Surname" in joined
    assert "Nguye" in joined      # what actually got written
```

- [ ] **Step 2: Run it and watch it fail**

Run: `venv/bin/python -m pytest tests/test_field_types.py::test_comb_truncation_produces_a_warning -v`
Expected: FAIL — `warnings` is empty.

- [ ] **Step 3: Wire the existing overflow check into the text branch**

In `_generate_single_pdf`, replace the text/combed branch (`pdf_generator.py:3637-3641`):

```python
                # Text / combed text (unchanged behaviour)
                value = self.format_value_tab3(raw_val, data_type=field.data_type)
                if not value:
                    continue
                field_values.update(combed_filler.fill_field(field, value))
```

with:

```python
                # Text / combed text
                value = self.format_value_tab3(raw_val, data_type=field.data_type)
                if not value:
                    continue
                if field.is_combed:
                    # fill_field() truncates over-long values silently — that is
                    # real data loss on a legal-name field, so say so.
                    check = combed_filler.validate_overflow(field, value)
                    if check['will_truncate']:
                        capacity = (len(field.combed_fields)
                                    if field.combed_fields else field.length)
                        warnings_out.append(
                            f"{field.field_name}: '{value}' is too long "
                            f"({check['original_length']} characters, room for "
                            f"{capacity}) — saved as '{check['truncated_text']}'")
                field_values.update(combed_filler.fill_field(field, value))
```

- [ ] **Step 4: Run the full suite**

Run: `venv/bin/python -m pytest tests/ -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add pdf_generator.py tests/test_field_types.py
git commit -m "fix: warn when a value is truncated to fit a combed field"
```

---

### Task 7: Stop erasing values that read as "nan"

`format_value_tab3` blanks any value whose lowercase is `"nan"`. Under `dtype=str`, genuine missing cells arrive as real `float('nan')` and are already caught by `pd.isna`. The string comparison only destroys legitimate data — and **Nan** is a real given name (Vietnamese, Thai).

**Files:**
- Modify: `pdf_generator.py:3749-3751`
- Test: `tests/test_data_fidelity.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_data_fidelity.py`:

```python
def test_a_student_named_nan_is_not_erased():
    """'Nan' is a real given name. pd.isna already handles genuine blanks."""
    import numpy as np
    from pdf_generator import BulkPDFGenerator

    assert BulkPDFGenerator.format_value_tab3("Nan") == "Nan"
    assert BulkPDFGenerator.format_value_tab3("nan") == "nan"
    # Genuine missing values must still come back empty.
    assert BulkPDFGenerator.format_value_tab3(np.nan) == ""
    assert BulkPDFGenerator.format_value_tab3(None) == ""
```

- [ ] **Step 2: Run it and watch it fail**

Run: `venv/bin/python -m pytest tests/test_data_fidelity.py::test_a_student_named_nan_is_not_erased -v`
Expected: FAIL — `format_value_tab3("Nan")` returns `""`.

- [ ] **Step 3: Drop the string comparison**

In `format_value_tab3`, replace:

```python
        # Convert to string and clean
        str_val = str(val).strip()
        if str_val.lower() == 'nan':
            return ""

        return str_val
```

with:

```python
        # Convert to string and clean. Note: no `== 'nan'` string check —
        # pd.isna() above already catches genuine missing values under
        # dtype=str, and 'Nan' is a real given name that this would erase.
        return str(val).strip()
```

- [ ] **Step 4: Run the full suite**

Run: `venv/bin/python -m pytest tests/ -v`
Expected: all PASS. If a test asserts the old `'nan'`-blanking behaviour, update it — the behaviour is the bug.

- [ ] **Step 5: Commit**

```bash
git add pdf_generator.py tests/test_data_fidelity.py
git commit -m "fix: stop blanking the legitimate name 'Nan'"
```

---

### Task 8: Prove non-ASCII names survive a fill

Vietnamese and Chinese names are routine in Victorian schools. Nothing currently tests that pypdf's appearance generation preserves them.

**Files:**
- Test: `tests/test_field_types.py`

- [ ] **Step 1: Write the test**

Append to `tests/test_field_types.py`:

```python
def test_non_ascii_names_survive_a_fill(tmp_path):
    """Vietnamese/Chinese names are routine in Victorian schools."""
    import pandas as pd
    from pypdf import PdfReader
    from pdf_generator import BulkPDFGenerator
    from models import PDFField
    from tests._form_fixture import build_mixed_form

    pdf = str(tmp_path / "form.pdf")
    build_mixed_form(pdf)

    field = PDFField(
        field_name="Student_Name", field_type="Text", page=1, length=None,
        is_combed=False, combed_fields=[], rect=(0, 0, 10, 10),
        excel_column="Student_Name",
    )

    app = BulkPDFGenerator.__new__(BulkPDFGenerator)
    reader = PdfReader(pdf)
    ctx = {
        '_reader': reader,
        'analyzed_fields': [field],
        'pdf_fields': [],
        'combed_padding': False,
        'combed_align': 'left',
    }
    out = str(tmp_path / "out.pdf")
    app._generate_single_pdf(ctx, pd.Series({"Student_Name": "Nguyễn Thị Hương"}), out)
    reader.close()

    assert PdfReader(out).get_fields()["Student_Name"]["/V"] == "Nguyễn Thị Hương"
```

- [ ] **Step 2: Run it**

Run: `venv/bin/python -m pytest tests/test_field_types.py::test_non_ascii_names_survive_a_fill -v`
Expected: PASS. **If it FAILS**, do not paper over it — the value is being mangled at write time. Stop, record the actual output in the commit message, and raise it with the user; a font/encoding fix is out of scope for this plan and belongs in the deferred list.

- [ ] **Step 3: Commit**

```bash
git add tests/test_field_types.py
git commit -m "test: verify non-ASCII names survive PDF filling"
```

---

# Stage 3 — Spreadsheet export

With the analyzer producing correct on-states and options, the export can finally tell teachers what to type — and stop guessing mappings the app then ignores.

---

### Task 9: Export allowed values, real mappings, and dropdown validation

Four defects in one file region, all in the same code path:
1. The sheet never says what to type for a checkbox, radio, or dropdown, though generation validates strictly against those values.
2. Export ignores `field.excel_column`, so a teacher's Tab 2 mappings don't match the headers they're given.
3. Two field names can collapse to the same header (`First_Name` and `First Name` both → `First Name`), which pandas mangles to `First Name.1` on re-import — silently unmapping a field.
4. The `'@'` text format stops at row 501, so student IDs and dates degrade from row 502 on.

**Files:**
- Modify: `pdf_generator.py:2091-2318` (`export_mapping_file`, `generate_field_notes`)
- Test: `tests/test_export_mapping.py` (create)

**Interfaces:**
- Produces: `BulkPDFGenerator.field_allowed_values(field: PDFField) -> str` — the human-readable "what to type" string.
- Produces: `BulkPDFGenerator.assign_export_columns() -> list` — assigns `field.excel_column` for every data field, uniquified, and returns the data-entry column names in order. Signature and Button fields get `excel_column = None` and no column.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_export_mapping.py`:

```python
"""The exported workbook is the artifact teachers actually type into.
If it doesn't tell them what's valid, the app's strict validation is a trap."""
import pandas as pd
import pytest

from models import PDFField
from pdf_generator import BulkPDFGenerator


def _app(fields):
    app = BulkPDFGenerator.__new__(BulkPDFGenerator)
    app.analyzed_fields = fields
    return app


def _field(name, ftype="Text", **kw):
    return PDFField(
        field_name=name, field_type=ftype, page=1,
        length=kw.pop("length", None), is_combed=kw.pop("is_combed", False),
        combed_fields=kw.pop("combed_fields", []), rect=(0, 0, 10, 10), **kw
    )


def test_allowed_values_spell_out_radio_options():
    app = _app([])
    f = _field("Session", "RadioButton", on_states=["Morning", "Afternoon"])
    assert "Morning" in app.field_allowed_values(f)
    assert "Afternoon" in app.field_allowed_values(f)


def test_allowed_values_spell_out_dropdown_options():
    app = _app([])
    f = _field("State", "ComboBox", options=["VIC", "NSW"])
    assert "VIC" in app.field_allowed_values(f)


def test_allowed_values_explain_checkboxes_and_signatures():
    app = _app([])
    assert "Yes" in app.field_allowed_values(_field("Approved", "CheckBox"))
    sig = app.field_allowed_values(_field("Sign_Here", "Signature"))
    assert "leave blank" in sig.lower()


def test_export_columns_reuse_explicit_mappings():
    """A teacher's Tab 2 mapping must survive into the sheet they're handed."""
    f = _field("Name")
    f.excel_column = "Preferred Name"
    app = _app([f])
    cols = app.assign_export_columns()
    assert cols == ["Preferred Name"]


def test_export_columns_are_uniquified():
    """'First_Name' and 'First Name' both smart-guess to 'First Name'.
    Duplicate headers get mangled to 'First Name.1' by pandas on re-import,
    silently unmapping one of the fields."""
    app = _app([_field("First_Name"), _field("First Name")])
    cols = app.assign_export_columns()
    assert len(set(cols)) == 2, f"headers must be unique, got {cols}"
    # And the fields now carry the exact headers, so mapping round-trips.
    assert [f.excel_column for f in app.analyzed_fields] == cols


def test_signature_and_button_get_no_data_column():
    app = _app([_field("Name"), _field("Sign", "Signature"), _field("Print", "Button")])
    cols = app.assign_export_columns()
    assert cols == ["Name"]
    assert app.analyzed_fields[1].excel_column is None
    assert app.analyzed_fields[2].excel_column is None
```

- [ ] **Step 2: Run them and watch them fail**

Run: `venv/bin/python -m pytest tests/test_export_mapping.py -v`
Expected: all FAIL — `field_allowed_values` and `assign_export_columns` don't exist.

- [ ] **Step 3: Add both methods, directly above `export_mapping_file`**

```python
    def field_allowed_values(self, field: PDFField) -> str:
        """Plain-English 'what do I type in this column?' for a field.

        Generation validates strictly — a checkbox needs a truthy token, a
        radio needs an exact export value, a dropdown must match an option.
        Without this, a teacher only discovers the rules from a warning
        AFTER generating 200 PDFs.
        """
        ftype = field.field_type

        if ftype == 'Signature':
            return 'Cannot be auto-filled — leave blank'
        if ftype == 'Button':
            return 'Not a data field — leave blank'
        if ftype == 'CheckBox':
            return 'Yes or No  (also accepts Y/N, X, 1/0, TRUE/FALSE)'
        if ftype == 'RadioButton':
            if field.on_states:
                return 'One of: ' + ', '.join(field.on_states)
            return 'Yes or No'
        if ftype in ('ComboBox', 'ListBox'):
            if field.options:
                return 'One of: ' + ', '.join(field.options)
            return 'Any text'
        if field.data_type == 'date':
            return 'A date, e.g. 25/12/2010'
        if field.data_type == 'number':
            return 'A number, e.g. 12'
        if field.is_combed:
            capacity = len(field.combed_fields) if field.combed_fields else field.length
            if capacity:
                return f'Any text, up to {capacity} characters'
        return 'Any text'

    def assign_export_columns(self) -> list:
        """Give every data field a unique Excel column name, and remember it.

        Writing the chosen name back onto field.excel_column is what makes the
        exported sheet and the app's mapping agree: previously the export
        guessed a header while Tab 2 held a different (possibly explicit)
        mapping, and generation used the mapping — so a teacher could fill the
        column they were given and still get a blank PDF.

        Signature/Button fields are not data — they get no column.
        """
        columns = []
        used = {}

        for field in self.analyzed_fields:
            if field.field_type in ('Signature', 'Button'):
                field.excel_column = None
                continue

            name = field.excel_column or self.smart_guess_excel_column(field.field_name)
            key = name.lower()
            if key in used:
                used[key] += 1
                name = f"{name} ({used[key]})"
            else:
                used[key] = 1

            field.excel_column = name
            columns.append(name)

        return columns
```

- [ ] **Step 4: Run the new tests**

Run: `venv/bin/python -m pytest tests/test_export_mapping.py -v`
Expected: all 6 PASS.

- [ ] **Step 5: Use them in `export_mapping_file`**

Replace the field-data build block (`pdf_generator.py:2121-2139`):

```python
            # Build field data
            data = []
            for field in self.analyzed_fields:
                excel_col = self.smart_guess_excel_column(field.field_name)
                data.append({
                    'PDF_Field_Name': field.field_name,
                    'Excel_Column_Name': excel_col,
                    'Field_Type': field.field_type,
                    'Page': field.page,
                    'Required': 'Yes' if field.is_critical else 'No',
                    'Length': f"{field.length} chars" if field.is_combed else '-',
                    'Notes': self.generate_field_notes(field),
                })

            df = pd.DataFrame(data)

            # Data Entry columns: use the Excel column names as headers
            data_entry_cols = [d['Excel_Column_Name'] for d in data if d['Excel_Column_Name']]
            df_data_entry = pd.DataFrame(columns=data_entry_cols)
```

with:

```python
            # Assign (and remember) a unique column per data field, so the sheet
            # the teacher fills in is exactly the sheet the app maps back.
            data_entry_cols = self.assign_export_columns()

            data = []
            for field in self.analyzed_fields:
                data.append({
                    'PDF_Field_Name': field.field_name,
                    'Excel_Column_Name': field.excel_column or '',
                    'Field_Type': field.field_type,
                    'What to type': self.field_allowed_values(field),
                    'Page': field.page,
                    'Required': 'Yes' if field.is_critical else 'No',
                    'Length': f"{field.length} chars" if field.is_combed else '-',
                    'Notes': self.generate_field_notes(field),
                })

            df = pd.DataFrame(data)
            df_data_entry = pd.DataFrame(columns=data_entry_cols)
```

- [ ] **Step 6: Add dropdown validation and full-column text format to the Data Entry sheet**

In the "Format: Data Entry sheet" block, replace the `'@'` loop (`pdf_generator.py:2196-2201`):

```python
                # Format all columns as Text so numbers stay as strings
                from openpyxl.utils import get_column_letter
                for c in range(1, len(data_entry_cols) + 1):
                    col_letter = get_column_letter(c)
                    for row_num in range(2, 502):  # rows 2-501 for data
                        ws_entry.cell(row=row_num, column=c).number_format = '@'
```

with:

```python
                # Format columns as Text so leading zeros (student IDs) survive
                # and typed dates aren't converted to Excel serials. Set it on
                # the COLUMN as well as the cells — the old row-2..501 loop left
                # cohorts larger than 500 unprotected.
                from openpyxl.utils import get_column_letter
                from openpyxl.worksheet.datavalidation import DataValidation

                for c in range(1, len(data_entry_cols) + 1):
                    col_letter = get_column_letter(c)
                    ws_entry.column_dimensions[col_letter].number_format = '@'
                    for row_num in range(2, 1002):
                        ws_entry.cell(row=row_num, column=c).number_format = '@'

                # Dropdowns for fields with a fixed set of valid values, so an
                # invalid entry cannot be typed in the first place.
                data_fields = [f for f in self.analyzed_fields if f.excel_column]
                for idx, field in enumerate(data_fields, start=1):
                    if field.field_type == 'CheckBox':
                        choices = ['Yes', 'No']
                    elif field.field_type == 'RadioButton' and field.on_states:
                        choices = list(field.on_states)
                    elif field.field_type in ('ComboBox', 'ListBox') and field.options:
                        choices = list(field.options)
                    else:
                        continue

                    # Excel's inline list is comma-separated and capped at 255
                    # chars; an option containing a comma would split in two.
                    joined = ",".join(choices)
                    if len(joined) > 250 or any(',' in c for c in choices):
                        continue

                    letter = get_column_letter(idx)
                    dv = DataValidation(
                        type='list', formula1=f'"{joined}"', allow_blank=True,
                        showDropDown=False,
                    )
                    dv.error = f"Please choose one of: {', '.join(choices)}"
                    dv.errorTitle = "Not a valid value for this field"
                    ws_entry.add_data_validation(dv)
                    dv.add(f"{letter}2:{letter}1001")
```

- [ ] **Step 7: Correct the Instructions sheet — it currently describes behaviour the app does not have**

The sheet tells teachers to rename `Excel_Column_Name` values, but the app never reads that sheet back. Replace the `instructions` list (`pdf_generator.py:2147-2165`) with:

```python
                instructions = pd.DataFrame({
                    'Bulk PDF Generator - Field Mapping Guide': [
                        '',
                        'HOW TO USE THIS FILE:',
                        '1. Type your data into the "Data Entry" sheet — one row per person.',
                        '2. The "Field Mapping" sheet is a read-only reference. Its',
                        '   "What to type" column tells you the valid values for each field.',
                        '3. Save this file.',
                        '4. In the app, go to "3 Generate PDFs" and load this file.',
                        '   When asked which sheet to use, choose "Data Entry".',
                        '',
                        'IMPORTANT NOTES:',
                        '- Editing column names in "Field Mapping" does NOT change anything.',
                        '  To change how a column maps to a PDF field, use the app\'s',
                        '  "2 Map Fields" tab.',
                        '- Tick boxes: type Yes or No.',
                        '- Dropdowns and option buttons: use one of the listed values',
                        '  (cells with a dropdown arrow will offer them to you).',
                        '- Signature fields cannot be filled automatically — leave blank.',
                        '- Combed fields auto-split text into boxes (e.g. "John" -> J-o-h-n).',
                        '',
                        'For help: See the Getting Started tab in the app',
                    ]
                })
```

- [ ] **Step 8: Refresh Tab 2 after export, since mappings were just assigned**

Replace the success line (`pdf_generator.py:2295`):

```python
            messagebox.showinfo("Export Successful", f"Mapping file saved to:\n{filepath}")
```

with:

```python
            # assign_export_columns() wrote the chosen headers onto the fields —
            # show them in the mapping tab so the two never disagree.
            self._refresh_tab2_mappings()
            self.update_status(f"Mapping file saved: {os.path.basename(filepath)}", 'success')
            messagebox.showinfo("Export Successful", f"Mapping file saved to:\n{filepath}")
```

- [ ] **Step 9: Update `generate_field_notes` to stop duplicating the new column**

Replace `generate_field_notes` (`pdf_generator.py:2308-2318`):

```python
    def generate_field_notes(self, field: PDFField) -> str:
        """Generate helpful notes for a field."""
        notes = []

        if field.is_critical:
            notes.append('Critical field')
        if field.field_type == 'Text-Combed' and field.is_combed:
            notes.append('Splits into character boxes')

        return ', '.join(notes) if notes else ''
```

- [ ] **Step 10: Verify a real exported workbook by hand**

Run the app from source, analyse a PDF that has a checkbox and a dropdown, export the mapping file, then open it and confirm:
- "Field Mapping" has a **What to type** column with real option values.
- "Data Entry" cells for the checkbox/dropdown columns show a **dropdown arrow** and reject an invalid value.
- Signature fields appear on Field Mapping but have **no** Data Entry column.

```bash
venv/bin/python pdf_generator.py
```

- [ ] **Step 11: Run the full suite and commit**

Run: `venv/bin/python -m pytest tests/ -v`
Expected: all PASS.

```bash
git add pdf_generator.py tests/test_export_mapping.py
git commit -m "feat: export allowed values, real mappings and dropdown validation"
```

---

# Stage 4 — Import integrity

The workbook is now correct on the way out. These tasks fix the way back in.

---

### Task 10: Stop auto-map from destroying manual mappings, and default to the Data Entry sheet

Two traps, both hit in the ordinary workflow:
1. After **every** data load, if any field is unmapped (a Signature guarantees this), `_auto_map_fields` runs and — per its own docstring — overwrites *existing* mappings. A teacher who maps `Name` → `Preferred Name`, then fixes a typo in Excel and re-loads, silently gets `Name` → `Name` back.
2. The app's own exported workbook has "Field Mapping" as sheet 0, but the sheet picker defaults to sheet 0. Pressing Enter loads the reference sheet as data.

**Files:**
- Modify: `pdf_generator.py:2756-2778` (`_auto_map_fields`), `:3032-3095` (`_pick_excel_sheet`), `:3138-3176` (`load_data_tab3`)
- Test: `tests/test_mapping_integrity.py` (create)

**Interfaces:**
- Produces: `_auto_map_fields(overwrite: bool = False)` — by default only fills fields whose `excel_column` is `None`.
- Produces: `_pick_excel_sheet(sheet_names: list, preferred: str = 'Data Entry') -> Optional[str]`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_mapping_integrity.py`:

```python
"""Re-loading a corrected spreadsheet is the single most common action a
teacher takes. It must not silently rewrite their field mappings."""
import inspect

import pandas as pd

from models import PDFField
from pdf_generator import BulkPDFGenerator


def _field(name, excel_column=None):
    return PDFField(
        field_name=name, field_type="Text", page=1, length=None,
        is_combed=False, combed_fields=[], rect=(0, 0, 10, 10),
        excel_column=excel_column,
    )


def test_auto_map_preserves_an_explicit_mapping():
    app = BulkPDFGenerator.__new__(BulkPDFGenerator)
    app.df = pd.DataFrame(columns=["Name", "Preferred Name"])
    app.analyzed_fields = [_field("Name", excel_column="Preferred Name")]
    app._refresh_tab2_mappings = lambda: None

    app._auto_map_fields()

    assert app.analyzed_fields[0].excel_column == "Preferred Name", \
        "a mapping the teacher set by hand must survive a data reload"


def test_auto_map_still_fills_unmapped_fields():
    app = BulkPDFGenerator.__new__(BulkPDFGenerator)
    app.df = pd.DataFrame(columns=["Name"])
    app.analyzed_fields = [_field("Name")]
    app._refresh_tab2_mappings = lambda: None

    app._auto_map_fields()

    assert app.analyzed_fields[0].excel_column == "Name"


def test_auto_map_can_still_overwrite_when_explicitly_asked():
    app = BulkPDFGenerator.__new__(BulkPDFGenerator)
    app.df = pd.DataFrame(columns=["Name"])
    app.analyzed_fields = [_field("Name", excel_column="Something Else")]
    app._refresh_tab2_mappings = lambda: None

    app._auto_map_fields(overwrite=True)

    assert app.analyzed_fields[0].excel_column == "Name"


def test_sheet_picker_prefers_the_data_entry_sheet():
    """The app's own workbook lists 'Field Mapping' first. Defaulting to
    sheet 0 loaded the reference sheet as data."""
    src = inspect.getsource(BulkPDFGenerator._pick_excel_sheet)
    assert "Data Entry" in src, "picker must prefer the Data Entry sheet"
    assert "combo.current(0)" not in src, "picker must not hard-default to sheet 0"
```

- [ ] **Step 2: Run them and watch them fail**

Run: `venv/bin/python -m pytest tests/test_mapping_integrity.py -v`
Expected: `test_auto_map_preserves_an_explicit_mapping`, `test_auto_map_can_still_overwrite_when_explicitly_asked` and `test_sheet_picker_prefers_the_data_entry_sheet` FAIL.

- [ ] **Step 3: Make `_auto_map_fields` non-destructive by default**

Replace `_auto_map_fields` (`pdf_generator.py:2756-2778`):

```python
    def _auto_map_fields(self, overwrite: bool = False):
        """Fill in field→column mappings by matching names.

        By default this only fills fields that have NO mapping yet. It used to
        overwrite every field on every data load, so a teacher who set a
        mapping by hand in Tab 2 lost it the moment they re-loaded a corrected
        spreadsheet — and every PDF was then filled from the wrong column.

        Pass overwrite=True only from an explicit user action (the Auto-Map
        button), never from a load.
        """
        if self.df is None or not self.analyzed_fields:
            return

        column_lower = {col.lower(): col for col in self.df.columns}

        for field in self.analyzed_fields:
            if field.excel_column and not overwrite:
                continue  # the user (or a saved template) already decided this

            matched = False
            # Try smart-guess name first, then underscore-stripped field name, then direct
            guess = self.smart_guess_excel_column(field.field_name)
            if guess.lower() in column_lower:
                field.excel_column = column_lower[guess.lower()]
                matched = True
            elif field.field_name.replace('_', ' ').lower() in column_lower:
                field.excel_column = column_lower[field.field_name.replace('_', ' ').lower()]
                matched = True
            elif field.field_name.lower() in column_lower:
                field.excel_column = column_lower[field.field_name.lower()]
                matched = True

            if matched:
                field._auto_mapped = True

        self._refresh_tab2_mappings()
```

- [ ] **Step 4: Simplify the call site in `load_data_tab3`**

Replace (`pdf_generator.py:3172-3176`):

```python
            # Refresh Tab 2 mapping dropdowns with the new column list;
            # auto-map any fields that don't yet have an explicit mapping
            if not self.analyzed_fields or any(f.excel_column is None for f in self.analyzed_fields):
                self._auto_map_fields()
            self._refresh_tab2_mappings()
```

with:

```python
            # Fill in any fields that have no mapping yet. Explicit mappings
            # (set in Tab 2, or restored from a template) are left alone.
            self._auto_map_fields()
            self._refresh_tab2_mappings()
```

- [ ] **Step 5: Make the "Auto-Map All" button the one place that overwrites**

The Tab 2 "Auto-Map All" button (`pdf_generator.py:2481-2484`) is an explicit user action — there, re-matching everything is exactly what the teacher asked for. Change its command:

```python
        self._tab2_auto_btn = ttk.Button(
            btn_frame,
            text="Auto-Map All",
            command=lambda: self._auto_map_fields(overwrite=True),
            state=tk.DISABLED,
        )
```

Leave the calls in `analyze_pdf_fields` (`:1912`) and `load_data_tab3` (`:3175`) as the plain, non-overwriting form.

- [ ] **Step 6: Default the sheet picker to Data Entry**

In `_pick_excel_sheet`, change the signature and the default selection.

Signature (`pdf_generator.py:3032`):

```python
    def _pick_excel_sheet(self, sheet_names: list,
                          preferred: str = 'Data Entry') -> Optional[str]:
        """Show a modal sheet-picker dialog and return the chosen sheet name.

        Preselects the app's own 'Data Entry' sheet when present. The exported
        workbook lists 'Field Mapping' first, so defaulting to sheet 0 loaded
        the reference sheet as data — no columns matched, and the preview
        filled with header text.

        Returns None if the user cancels.
        """
```

Replace `combo.current(0)` (`pdf_generator.py:3067`) with:

```python
        default_idx = 0
        for i, name in enumerate(sheet_names):
            if str(name).strip().lower() == preferred.strip().lower():
                default_idx = i
                break
        combo.current(default_idx)

        if sheet_names[default_idx].strip().lower() == preferred.strip().lower():
            tk.Label(inner,
                text='"Data Entry" is the sheet this app created for your data.',
                font=(ff, 9), fg=C['text_tertiary'], bg=C['bg_base'],
            ).pack(anchor=tk.W, pady=(6, 0))
```

- [ ] **Step 7: Run the full suite**

Run: `venv/bin/python -m pytest tests/ -v`
Expected: all PASS.

- [ ] **Step 8: Verify by hand — this is the workflow that was broken**

```bash
venv/bin/python pdf_generator.py
```
Analyse a PDF → export the mapping file → type two rows into Data Entry → load that file in Tab 3. Confirm the sheet picker **preselects "Data Entry"**, the preview shows your rows (not header text), and a mapping you change in Tab 2 **survives** clicking "Load & Preview Data" again.

- [ ] **Step 9: Commit**

```bash
git add pdf_generator.py tests/test_mapping_integrity.py
git commit -m "fix: preserve manual mappings on reload; default sheet picker to Data Entry"
```

---

### Task 11: Warn when the data or the template no longer matches the PDF

Two silent-blank paths: the teacher can analyse PDF A and then browse to PDF B on Tab 3 (the analysed field names describe A), and a saved template can be loaded against a re-issued form whose fields were renamed. pypdf silently ignores field names it can't find, so generation "succeeds" with blank fields and no error.

Duplicate spreadsheet headers are the third silent path: pandas renames the second `Name` to `Name.1`, which matches nothing.

**Files:**
- Modify: `pdf_generator.py:1787-1918` (`analyze_pdf_fields` — record the analysed path), `:3181-3248` (`validate_data_tab3`), `:3138-3153` (`load_data_tab3`)
- Test: `tests/test_mapping_integrity.py`

**Interfaces:**
- Consumes: `self.pdf_fields` (live field names, already read in `load_data_tab3`), `self.analyzed_fields`.
- Produces: `self._analyzed_pdf_path: Optional[str]` — set in `analyze_pdf_fields`.
- Produces: `BulkPDFGenerator.find_missing_fields(analyzed_fields, pdf_field_names) -> List[str]` — static, pure.
- Produces: `BulkPDFGenerator.find_duplicate_headers(raw_headers) -> List[str]` — static, pure.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_mapping_integrity.py`:

```python
def test_find_missing_fields_spots_a_renamed_form():
    """A template saved against last year's form must not generate 200 blank
    PDFs in silence when the fields have been renamed."""
    fields = [_field("Student_Name"), _field("Candidate_No")]
    live = ["Student_Name", "CandidateNumber"]   # form was re-issued

    missing = BulkPDFGenerator.find_missing_fields(fields, live)

    assert missing == ["Candidate_No"]


def test_find_missing_fields_understands_combed_fields():
    combed = PDFField(
        field_name="Surname", field_type="Text-Combed", page=1, length=3,
        is_combed=True, combed_fields=["Surname[0]", "Surname[1]", "Surname[2]"],
        rect=(0, 0, 10, 10),
    )
    live = ["Surname[0]", "Surname[1]", "Surname[2]"]
    assert BulkPDFGenerator.find_missing_fields([combed], live) == []


def test_find_missing_fields_ignores_unfillable_types():
    sig = _field("Sign")
    sig.field_type = "Signature"
    assert BulkPDFGenerator.find_missing_fields([sig], []) == []


def test_find_duplicate_headers():
    """pandas silently renames the second 'Name' to 'Name.1', which then
    matches no field at all."""
    assert BulkPDFGenerator.find_duplicate_headers(
        ["Name", "DOB", "name", "Class"]) == ["Name"]
    assert BulkPDFGenerator.find_duplicate_headers(["Name", "DOB"]) == []
```

- [ ] **Step 2: Run them and watch them fail**

Run: `venv/bin/python -m pytest tests/test_mapping_integrity.py -v -k "missing or duplicate"`
Expected: FAIL — neither helper exists.

- [ ] **Step 3: Add both pure helpers to `BulkPDFGenerator`, above `validate_data_tab3`**

```python
    @staticmethod
    def find_missing_fields(analyzed_fields, pdf_field_names) -> list:
        """Analysed fields that do not exist in the PDF being filled.

        pypdf silently ignores field names it cannot find, so a stale template
        (or a PDF swapped on Tab 3 after analysis) produces blank PDFs that
        report success. Signature/Button fields are never written, so their
        absence is not a problem.
        """
        live = {str(name) for name in (pdf_field_names or [])}
        if not live:
            return []

        missing = []
        for field in analyzed_fields or []:
            if field.field_type in ('Signature', 'Button'):
                continue
            names = field.combed_fields or [field.field_name]
            if not any(name in live for name in names):
                missing.append(field.field_name)
        return missing

    @staticmethod
    def find_duplicate_headers(raw_headers) -> list:
        """Column headers that appear more than once (case-insensitively).

        pandas mangles the second occurrence to 'Name.1', which then matches no
        PDF field — the column looks present but silently fills nothing.
        """
        seen = {}
        duplicates = []
        for header in raw_headers or []:
            key = str(header).strip().lower()
            if not key or key == 'nan':
                continue
            if key in seen:
                if seen[key] not in duplicates:
                    duplicates.append(seen[key])
            else:
                seen[key] = str(header).strip()
        return duplicates
```

- [ ] **Step 4: Record the analysed PDF path**

In `analyze_pdf_fields`, immediately after the `with PDFAnalyzer(...)` block (just after `field_stats = analyzer.get_field_statistics(...)`), add:

```python
            # Remember which PDF these fields describe — Tab 3 has its own
            # PDF browser, so the two can drift apart.
            self._analyzed_pdf_path = pdf_path
```

In `__init__`, immediately after `self.analyzed_fields: List[PDFField] = []` (`pdf_generator.py:873`), add:

```python
        self._analyzed_pdf_path = None
        self._duplicate_headers = []
```

- [ ] **Step 5: Capture the raw headers on load and warn about duplicates**

In `load_data_tab3`, after the column-cleaning line (`pdf_generator.py:3150`), add:

```python
            # pandas has already de-duplicated the headers by now ('Name.1'), so
            # re-read the raw header row to see what the teacher actually typed.
            try:
                if excel_path.lower().endswith('.csv'):
                    raw_header = pd.read_csv(excel_path, dtype=str, header=None,
                                             nrows=1, encoding='utf-8-sig')
                else:
                    raw_header = pd.read_excel(excel_path, sheet_name=chosen_sheet,
                                               dtype=str, header=None, nrows=1)
                self._duplicate_headers = self.find_duplicate_headers(
                    list(raw_header.iloc[0]) if not raw_header.empty else [])
            except Exception:
                self._duplicate_headers = []   # never block a load over a warning
```

`chosen_sheet` is only defined on the Excel branch — hoist it by initialising `chosen_sheet = None` immediately before the `if excel_path.lower().endswith('.csv'):` branch. (`self._duplicate_headers` was already initialised in `__init__` in Step 4.)

- [ ] **Step 6: Surface all three warnings in the validation panel**

At the end of `validate_data_tab3`, immediately **before** the final `self.validation_text_tab3.config(state=tk.DISABLED)`, insert:

```python
        # ── Template / PDF drift ──────────────────────────────────────────
        notes = []

        analysed = getattr(self, '_analyzed_pdf_path', None)
        current_pdf = self.pdf_template_path.get()
        if analysed and current_pdf and os.path.abspath(analysed) != os.path.abspath(current_pdf):
            notes.append(
                f"\n\n⚠ The PDF selected here is not the one you analysed.\n"
                f"Analysed: {os.path.basename(analysed)}\n"
                f"Selected: {os.path.basename(current_pdf)}\n"
                f"Re-analyse on Tab 1, or the fields may not fill."
            )

        missing = self.find_missing_fields(
            self.analyzed_fields, getattr(self, 'pdf_fields', []))
        if missing:
            shown = ", ".join(missing[:5])
            if len(missing) > 5:
                shown += f" (+{len(missing) - 5} more)"
            notes.append(
                f"\n\n⚠ {len(missing)} field(s) from your template no longer exist "
                f"in this PDF — they will be blank:\n{shown}\n"
                f"Re-analyse the PDF on Tab 1 to fix this."
            )

        dupes = getattr(self, '_duplicate_headers', [])
        if dupes:
            notes.append(
                f"\n\n⚠ Your spreadsheet has duplicate column headings: "
                f"{', '.join(dupes)}.\n"
                f"Only the first of each will be used — rename them so each "
                f"heading is unique."
            )

        if notes:
            self.validation_text_tab3.config(state=tk.NORMAL)
            for note in notes:
                self.validation_text_tab3.insert(tk.END, note)
            self.validation_text_tab3.config(fg=COLORS['warning'])
```

- [ ] **Step 7: Run the full suite**

Run: `venv/bin/python -m pytest tests/ -v`
Expected: all PASS.

- [ ] **Step 8: Commit**

```bash
git add pdf_generator.py tests/test_mapping_integrity.py
git commit -m "feat: warn on template/PDF drift and duplicate spreadsheet headers"
```

---

# Stage 5 — Trust surfaces

The data is right. Now make sure the teacher can see it.

---

### Task 12: Stop the Record Preview from hiding students

A row whose **first preview column** is blank is skipped entirely — a student missing only their surname vanishes from the table and cannot be selected or generated, while the validation panel (which iterates every row) still counts them. On exam paperwork, a silently absent student is the worst failure the app can have.

**Files:**
- Modify: `pdf_generator.py:3250-3323` (`show_preview_tab3`), `:3181-3210` (`validate_data_tab3`)
- Test: `tests/test_preview_rows.py` (create)

**Interfaces:**
- Produces: `BulkPDFGenerator.row_is_blank(row) -> bool` — static; True only when *every* cell in the row is empty.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_preview_rows.py`:

```python
"""A student who is missing one field must still appear in the preview — with
a warning. Dropping the row hides them from selection entirely."""
import inspect

import numpy as np
import pandas as pd

from pdf_generator import BulkPDFGenerator


def test_row_is_blank_only_when_every_cell_is_empty():
    assert BulkPDFGenerator.row_is_blank(pd.Series({"a": "", "b": np.nan}))
    assert BulkPDFGenerator.row_is_blank(pd.Series({"a": "   ", "b": None}))
    # A student with no surname is NOT a blank row.
    assert not BulkPDFGenerator.row_is_blank(pd.Series({"Surname": "", "DOB": "1/1/2010"}))


def test_preview_does_not_skip_on_the_first_column_alone():
    src = inspect.getsource(BulkPDFGenerator.show_preview_tab3)
    assert "row_is_blank" in src, \
        "preview must skip only fully-blank rows, not rows missing their first value"
    assert "if self._preview_columns and not first_val" not in src, \
        "the first-column skip drops students who are missing that one field"


def test_validation_uses_the_same_blank_rule_as_the_preview():
    """Otherwise validation shouts about 70 bad records while the table shows 30."""
    src = inspect.getsource(BulkPDFGenerator.validate_data_tab3)
    assert "row_is_blank" in src
```

- [ ] **Step 2: Run them and watch them fail**

Run: `venv/bin/python -m pytest tests/test_preview_rows.py -v`
Expected: all 3 FAIL.

- [ ] **Step 3: Add the shared blank-row rule**

Add to `BulkPDFGenerator`, directly above `validate_data_tab3`:

```python
    @staticmethod
    def row_is_blank(row) -> bool:
        """True only when EVERY cell in the row is empty.

        The preview used to drop any row whose first preview column was blank,
        so a student missing only their surname disappeared from the table —
        unselectable, ungeneratable — while validation still counted them. The
        two disagreed, and the missing student was invisible.
        """
        for value in row.values:
            if pd.isna(value):
                continue
            if str(value).strip() != '':
                return False
        return True
```

- [ ] **Step 4: Use it in `show_preview_tab3`**

Replace the skip block (`pdf_generator.py:3284-3287`):

```python
            # Skip completely empty rows (check first dynamic column).
            # If no preview columns exist, treat every row as non-empty.
            if self._preview_columns and not first_val:
                continue
```

with:

```python
            # Skip only rows that are completely empty (trailing formatted rows
            # in Excel). A row missing one value is a student who needs fixing —
            # they must stay visible and selectable.
            if self.row_is_blank(row):
                continue
```

`first_val` is now unused in this method — remove its initialisation (`first_val = None`) and the `if first_val is None: first_val = val` assignment inside the column loop.

- [ ] **Step 5: Use the same rule in `validate_data_tab3`**

In the row loop of `validate_data_tab3`, immediately after `for idx, row in self.df.iterrows():`, insert:

```python
            if self.row_is_blank(row):
                continue   # same rule as the preview, so the counts agree
```

- [ ] **Step 6: Run the full suite**

Run: `venv/bin/python -m pytest tests/ -v`
Expected: all PASS.

- [ ] **Step 7: Verify by hand**

```bash
venv/bin/python pdf_generator.py
```
Load a spreadsheet where one student has a blank surname and several trailing rows are empty. Confirm the student **appears** with a "Missing: …" status, the empty rows do **not** appear, and the validation count matches the number of warning rows in the table.

- [ ] **Step 8: Commit**

```bash
git add pdf_generator.py tests/test_preview_rows.py
git commit -m "fix: keep partially-filled records visible in the preview"
```

---

### Task 13: Replace the completion dialogs with an inline results panel

The highest-stakes moment in the app — a batch has just finished — fires up to **three** stacked `messagebox` calls, the exact pattern CLAUDE.md documents as opening *behind* the main window on macOS and silently freezing the app. The results also vanish once dismissed, the >20-warning overflow says "see app.log" while warnings are **never logged**, and there's no lasting record of what was produced.

**Files:**
- Modify: `pdf_generator.py:2930-2945` (Tab 3 UI — add the panel), `:3520-3531` (log warnings), `:3558-3561` (worker error path), `:3760-3807` (`generation_complete_tab3`)
- Test: `tests/test_performance.py`

**Interfaces:**
- Produces: `self.results_frame_tab3`, `self.results_summary_tab3`, `self.results_detail_tab3`, `self.results_open_btn_tab3` — created hidden in `setup_tab3`.
- Produces: `generation_complete_tab3(message, output_folder, error_details, warning_details)` — same signature, no messageboxes.
- Produces: `_show_generation_error(msg: str)` — inline error, replaces the worker's `messagebox.showerror`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_performance.py`:

```python
def test_generation_completion_uses_no_messagebox():
    """CLAUDE.md: on macOS a messagebox can open BEHIND the main window —
    invisible but modal — freezing the app. The end of a 200-PDF batch is the
    worst possible place for that."""
    import inspect
    from pdf_generator import BulkPDFGenerator

    src = inspect.getsource(BulkPDFGenerator.generation_complete_tab3)
    assert "messagebox" not in src, \
        "completion must report inline, not via a modal dialog"

    worker = inspect.getsource(BulkPDFGenerator.run_generation_tab3)
    assert "messagebox" not in worker, \
        "the generation worker must not raise a modal from a background thread"


def test_generation_warnings_are_logged():
    """Both dialogs claimed '(see app.log)' while warnings were never logged."""
    import inspect
    from pdf_generator import BulkPDFGenerator

    src = inspect.getsource(BulkPDFGenerator.run_generation_tab3)
    assert "self.logger.warning" in src, \
        "per-field warnings must reach app.log, as the UI claims they do"
```

- [ ] **Step 2: Run them and watch them fail**

Run: `venv/bin/python -m pytest tests/test_performance.py -v -k generation`
Expected: both FAIL.

- [ ] **Step 3: Build the results panel in `setup_tab3`**

In `setup_tab3`, immediately **after** the progress frame block (after `self.progress_label_tab3.pack()`) and **before** the Generate button, insert:

```python
        # ── Results panel (hidden until a batch finishes) ──
        # Deliberately NOT a messagebox: on macOS a modal can open behind the
        # main window — invisible but blocking — and this fires right after a
        # long batch. It also gives teachers a record that survives a click.
        self.results_frame_tab3 = tk.Frame(container, bg=COLORS['bg_surface'])

        results_inner = tk.Frame(self.results_frame_tab3, bg=COLORS['bg_surface'],
                                 padx=14, pady=12)
        results_inner.pack(fill=tk.BOTH, expand=True)

        self.results_summary_tab3 = tk.Label(
            results_inner, text="", font=font(12, 'bold'),
            fg=COLORS['text_primary'], bg=COLORS['bg_surface'],
            anchor=tk.W, justify=tk.LEFT,
        )
        self.results_summary_tab3.pack(fill=tk.X)

        self.results_detail_tab3 = tk.Text(
            results_inner, height=6, wrap=tk.WORD, state=tk.DISABLED,
            bg=COLORS['bg_input'], fg=COLORS['text_primary'],
            relief='flat', borderwidth=0, padx=10, pady=8,
            font=font(10), autostyle=False,
        )
        self.results_detail_tab3.pack(fill=tk.X, pady=(8, 8))

        self.results_open_btn_tab3 = ttk.Button(
            results_inner, text="Open Output Folder",
            command=self._open_last_output_folder,
        )
        self.results_open_btn_tab3.pack(anchor=tk.W)

        self._last_output_folder = None
```

- [ ] **Step 4: Add the folder-opening helper and the inline error reporter**

Add both methods directly above `generation_complete_tab3`:

```python
    def _open_last_output_folder(self):
        """Open the folder the last batch was written to."""
        folder = getattr(self, '_last_output_folder', None)
        if not folder or not os.path.isdir(folder):
            return
        try:
            if sys.platform == 'darwin':
                subprocess.run(['open', folder], check=False)
            elif sys.platform == 'win32':
                os.startfile(folder)
            else:
                subprocess.run(['xdg-open', folder], check=False)
        except Exception:
            pass  # failing to open the folder is non-critical

    def _show_generation_error(self, msg: str):
        """Report a whole-batch failure inline (never a modal — see CLAUDE.md)."""
        self.results_frame_tab3.pack(fill=tk.X, pady=(0, SPACING['element_gap']))
        self.results_summary_tab3.config(
            text="❌ Generation failed — no PDFs were created",
            fg=COLORS['error'],
        )
        self.results_detail_tab3.config(state=tk.NORMAL)
        self.results_detail_tab3.delete(1.0, tk.END)
        self.results_detail_tab3.insert(1.0, msg)
        self.results_detail_tab3.config(state=tk.DISABLED)
        self.results_open_btn_tab3.pack_forget()
        self.update_status("Generation failed", 'error')
        self.generate_btn_tab3.config(state=tk.NORMAL)
```

`subprocess` is **not** currently imported at module level (the old code imported it inline inside the handler). Add `import subprocess` alongside the other stdlib imports near the top of `pdf_generator.py`.

- [ ] **Step 5: Pass the real counts to the completion handler**

The old handler received a pre-formatted `final_message` string. The panel needs the numbers, not prose — parsing them back out of the sentence would be brittle.

In `run_generation_tab3`, replace the final-message block (`pdf_generator.py:3544-3553`):

```python
                # Final message
                final_message = f"Complete! {success_count} PDFs created"
                if error_count > 0:
                    final_message += f", {error_count} errors"
                final_message += f"\n\nOutput folder: {output_folder}"

                self.root.after(
                    0, self.generation_complete_tab3,
                    final_message, output_folder, error_details, warning_details,
                )
```

with:

```python
                self.root.after(
                    0, self.generation_complete_tab3,
                    success_count, output_folder, error_details, warning_details,
                )
```

- [ ] **Step 6: Rewrite `generation_complete_tab3` with no dialogs**

Replace the whole method (`pdf_generator.py:3760-3807`):

```python
    def generation_complete_tab3(self, success_count, output_folder,
                                 error_details=None, warning_details=None):
        """Show the batch result inline on Tab 3.

        Deliberately dialog-free. Three stacked messageboxes used to fire here,
        any of which could open behind the main window on macOS and freeze the
        app (CLAUDE.md). An inline panel also leaves a record the teacher can
        re-read, and has no 20-item cap.
        """
        error_details = error_details or []
        warning_details = warning_details or []

        self.progress_label_tab3.config(text="Generation complete!")
        self.update_selection_count_tab3()   # re-enable button with correct state
        self._last_output_folder = output_folder

        parts = [f"✅ {success_count} PDF(s) created"]
        if warning_details:
            parts.append(f"⚠ {len(warning_details)} to check")
        if error_details:
            parts.append(f"❌ {len(error_details)} failed")

        summary_colour = COLORS['success']
        if error_details:
            summary_colour = COLORS['error']
        elif warning_details:
            summary_colour = COLORS['warning']

        self.results_summary_tab3.config(
            text="   ·   ".join(parts), fg=summary_colour)

        detail_lines = [f"Output folder: {output_folder}", ""]
        if error_details:
            detail_lines.append("These rows could not be generated:")
            detail_lines.extend(f"  • {d}" for d in error_details)
            detail_lines.append("")
        if warning_details:
            detail_lines.append(
                "These files WERE created, but some values need a quick check:")
            detail_lines.extend(f"  • {w}" for w in warning_details)
            detail_lines.append("")
        if not error_details and not warning_details:
            detail_lines.append("All records generated cleanly.")

        self.results_detail_tab3.config(state=tk.NORMAL)
        self.results_detail_tab3.delete(1.0, tk.END)
        self.results_detail_tab3.insert(1.0, "\n".join(detail_lines))
        self.results_detail_tab3.config(state=tk.DISABLED)

        self.results_open_btn_tab3.pack(anchor=tk.W)
        self.results_frame_tab3.pack(fill=tk.X, pady=(0, SPACING['element_gap']))

        if error_details:
            self.update_status(
                f"Generation finished with {len(error_details)} error(s)", 'error')
        elif warning_details:
            self.update_status(
                f"Generation complete — {len(warning_details)} value(s) to check",
                'warning')
        else:
            self.update_status("Generation complete!", 'success')
```

`update_status` accepts a level string; confirm `'warning'` is a valid level with `grep -n "def update_status" -A 12 pdf_generator.py` and fall back to `'info'` if it is not.

- [ ] **Step 7: Log the warnings, so "see app.log" is finally true**

In `run_generation_tab3`, inside the per-row success branch, replace:

```python
                        for w in (row_warnings or []):
                            warning_details.append(f"{'_'.join(name_parts)}: {w}")
```

with:

```python
                        for w in (row_warnings or []):
                            detail = f"{'_'.join(name_parts)}: {w}"
                            warning_details.append(detail)
                            # The UI tells teachers the full list is in app.log —
                            # it never was until now.
                            self.logger.warning("Generation warning: %s", detail)
```

- [ ] **Step 8: Route the worker's failure path through the inline reporter**

Replace the outer handler (`pdf_generator.py:3558-3561`):

```python
        except Exception as e:
            err_msg = str(e)  # Capture before 'e' goes out of scope (PEP 3110)
            self.root.after(0, lambda msg=err_msg: messagebox.showerror("Error", f"Generation failed:\n{msg}"))
            self.root.after(0, lambda: self.generate_btn_tab3.config(state=tk.NORMAL))
```

with:

```python
        except Exception as e:
            err_msg = str(e)  # Capture before 'e' goes out of scope (PEP 3110)
            self.logger.exception("Generation batch failed")
            self.root.after(0, self._show_generation_error, err_msg)
```

- [ ] **Step 9: Hide the panel when a new batch starts**

In `start_generation_tab3`, immediately after `self.progress_var_tab3.set(0)`, add:

```python
        self.results_frame_tab3.pack_forget()   # clear the previous run's result
```

- [ ] **Step 10: Run the full suite**

Run: `venv/bin/python -m pytest tests/ -v`
Expected: all PASS, including the two new structural tests.

- [ ] **Step 11: Verify on macOS — this is the bug's home turf**

```bash
venv/bin/python pdf_generator.py
```
Generate a small batch including one row that triggers a warning (e.g. an invalid dropdown value). Confirm: **no dialog appears**, the results panel shows counts and details, "Open Output Folder" works, and the app never freezes. Then check `~/Documents/BulkPDFGenerator/app.log` contains the warning lines.

- [ ] **Step 12: Commit**

```bash
git add pdf_generator.py tests/test_performance.py
git commit -m "fix: replace completion dialogs with an inline results panel"
```

---

### Task 14: Remove the redundant "Analysis Complete" dialog and handle zero-field PDFs

Analysis currently pops a modal that repeats what the stats label already says, then immediately opens the audit dialog — two modals back to back. And a flat or scanned PDF cheerfully reports "Found 0 fields", opens an **empty** audit dialog, and enables Tab 2, with no hint that the PDF has no form fields at all.

**Files:**
- Modify: `pdf_generator.py:1836-1913` (`analyze_pdf_fields`)
- Test: `tests/test_performance.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_performance.py`:

```python
def test_analysis_does_not_stack_modals_and_handles_empty_pdfs():
    import inspect
    from pdf_generator import BulkPDFGenerator

    src = inspect.getsource(BulkPDFGenerator.analyze_pdf_fields)
    assert 'showinfo("Analysis Complete"' not in src, \
        "the success modal duplicates the stats label and stacks with the audit dialog"
    assert "no fillable form fields" in src, \
        "a flat/scanned PDF must say so instead of opening an empty audit dialog"
```

- [ ] **Step 2: Run it and watch it fail**

Run: `venv/bin/python -m pytest tests/test_performance.py::test_analysis_does_not_stack_modals_and_handles_empty_pdfs -v`
Expected: FAIL.

- [ ] **Step 3: Drop the modal and add the empty-PDF guard**

In `analyze_pdf_fields`, replace the success-modal line (`pdf_generator.py:1849`):

```python
            messagebox.showinfo("Analysis Complete", f"Found {total} fields ({combed} combed fields)")
```

with:

```python
            # No success modal here: the stats label and status bar already say
            # this, and a second modal stacks with the audit dialog below.
            if total == 0:
                self.stats_label.config(
                    text="No fillable form fields found in this PDF."
                )
                self.update_status(
                    "This PDF has no fillable form fields — it may be a scanned "
                    "or flattened form", 'warning')
                messagebox.showwarning(
                    "No Fillable Fields",
                    "This PDF has no fillable form fields.\n\n"
                    "It may be a scanned or 'flattened' form. You'll need a "
                    "version with real form fields — try asking whoever issued "
                    "it for a fillable copy.",
                )
                return
```

Returning early leaves Tab 2 disabled, which is correct — there is nothing to map.

- [ ] **Step 4: Run the full suite**

Run: `venv/bin/python -m pytest tests/ -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add pdf_generator.py tests/test_performance.py
git commit -m "fix: drop redundant analysis modal; explain PDFs with no form fields"
```

---

# Stage 6 — Robustness and polish

---

### Task 15: Handle encrypted PDFs properly

An owner-password-protected PDF (Acrobat's default "protect") analyses fine under PyMuPDF, then dies at generation with `cryptography>=3.1 is required for AES algorithm` — because `cryptography` is in neither `requirements.txt` nor the PyInstaller specs. A user-password PDF fails analysis with a raw MuPDF error.

**Files:**
- Modify: `requirements.txt`, `BulkPDFGenerator.spec`, `BulkPDFGenerator_mac.spec`, `pdf_analyzer.py:21-24`, `pdf_generator.py:1915-1918`
- Test: `tests/test_lifecycle_robustness.py`

**Interfaces:**
- Produces: `pdf_analyzer.PDFPasswordProtected(Exception)`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_lifecycle_robustness.py`:

```python
def test_cryptography_is_available_for_aes_encrypted_pdfs():
    """pypdf needs `cryptography` to fill an AES-encrypted PDF. Without it,
    analysis succeeds and generation dies — the worst possible ordering."""
    import cryptography  # noqa: F401


def test_password_protected_pdf_raises_a_friendly_error(tmp_path):
    import fitz
    import pytest
    from pdf_analyzer import PDFAnalyzer, PDFPasswordProtected

    pdf = str(tmp_path / "locked.pdf")
    doc = fitz.open()
    doc.new_page(width=200, height=200)
    doc.save(pdf, encryption=fitz.PDF_ENCRYPT_AES_256,
             user_pw="secret", owner_pw="secret")
    doc.close()

    with pytest.raises(PDFPasswordProtected):
        with PDFAnalyzer(pdf):
            pass
```

- [ ] **Step 2: Run it and watch it fail**

Run: `venv/bin/python -m pytest tests/test_lifecycle_robustness.py -v -k "cryptography or password"`
Expected: both FAIL (`cryptography` not installed; `PDFPasswordProtected` does not exist).

- [ ] **Step 3: Add the dependency**

Append to `requirements.txt`:

```
cryptography>=42.0.0
```

Install it: `venv/bin/pip install "cryptography>=42.0.0"`

- [ ] **Step 4: Add it to both PyInstaller specs**

In `BulkPDFGenerator.spec` and `BulkPDFGenerator_mac.spec`, find the `hiddenimports=[...]` list and add `'cryptography'`. Without this the frozen `.exe`/`.app` still can't open AES PDFs even though the dev venv can.

- [ ] **Step 5: Raise a typed error for password-protected PDFs**

In `pdf_analyzer.py`, add above `class PDFAnalyzer`:

```python
class PDFPasswordProtected(Exception):
    """The PDF needs a password to open."""
```

Replace `PDFAnalyzer.__enter__`:

```python
    def __enter__(self):
        """Open PDF document."""
        self.doc = fitz.open(self.pdf_path)
        if self.doc.needs_pass:
            self.doc.close()
            self.doc = None
            raise PDFPasswordProtected(self.pdf_path)
        return self
```

- [ ] **Step 6: Give the teacher a plain-English message**

In `pdf_generator.py`, import the new exception alongside the existing analyzer import (`grep -n "from pdf_analyzer import" pdf_generator.py`):

```python
from pdf_analyzer import PDFAnalyzer, auto_name_template, PDFPasswordProtected
```

In `analyze_pdf_fields`, add a handler **before** the generic `except Exception`:

```python
        except PDFPasswordProtected:
            self._close_preview_generator()
            self.update_status("PDF is password-protected", 'error')
            messagebox.showerror(
                "Password-Protected PDF",
                "This PDF is protected with a password and can't be opened.\n\n"
                "Open it in Acrobat, save an unprotected copy, and try again.",
            )
            return
```

- [ ] **Step 7: Run the full suite**

Run: `venv/bin/python -m pytest tests/ -v`
Expected: all PASS.

- [ ] **Step 8: Commit**

```bash
git add requirements.txt BulkPDFGenerator.spec BulkPDFGenerator_mac.spec pdf_analyzer.py pdf_generator.py tests/test_lifecycle_robustness.py
git commit -m "fix: support AES-encrypted PDFs and explain password-protected ones"
```

---

### Task 16: Fit small school laptops, and fix misleading labels

The window opens at 1000×800 with a 900×700 minimum — taller than a 1366×768 school laptop's usable height, pushing the Generate button off-screen. Three labels also actively mislead: "Analyze & Save" doesn't save, "Skip (all Text)" doesn't set anything to Text, and Tab 3's status label always claims "Auto-matching enabled".

**Files:**
- Modify: `pdf_generator.py:847-848` (window geometry), `:508` (dialog button), `:734` (audit button), `:2831-2832` (Tab 3 label)
- Test: `tests/test_performance.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_performance.py`:

```python
def test_window_is_clamped_to_the_screen():
    """1000x800 with a 900x700 minimum overflows a 1366x768 school laptop and
    pushes the Generate button off-screen."""
    import inspect
    from pdf_generator import BulkPDFGenerator

    src = inspect.getsource(BulkPDFGenerator.__init__)
    assert "winfo_screenheight" in src, \
        "window size must be clamped to the actual screen"


def test_no_misleading_button_labels():
    import inspect
    import pdf_generator

    src = inspect.getsource(pdf_generator)
    assert "Analyze & Save" not in src, \
        "that button analyses but does not save the template config"
    assert "Skip (all Text)" not in src, \
        "Skip leaves types untouched — it does not set them all to Text"
```

- [ ] **Step 2: Run it and watch it fail**

Run: `venv/bin/python -m pytest tests/test_performance.py -v -k "clamped or misleading"`
Expected: both FAIL.

- [ ] **Step 3: Clamp the window to the screen**

In `__init__`, replace the geometry lines (`pdf_generator.py:847-848`):

```python
        self.root.geometry("1000x800")
        self.root.minsize(900, 700)
```

with:

```python
        # Clamp to the actual screen — a 1366x768 school laptop cannot show an
        # 800px-tall window plus chrome, and the Generate button ends up below
        # the bottom edge.
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        win_w = min(1000, screen_w - 40)
        win_h = min(800, screen_h - 120)
        self.root.geometry(f"{win_w}x{win_h}")
        self.root.minsize(min(900, win_w), min(700, win_h))
```

- [ ] **Step 4: Fix the three misleading labels**

`pdf_generator.py:508` — the button analyses; saving the config is a separate button:

```python
            text="Analyze",
```

`pdf_generator.py:734` — `on_skip` sets `result = None`, which leaves prior/restored types untouched:

```python
        ttk.Button(btn_frame, text="Skip — keep current types",
                   command=self.on_skip).pack(side=tk.LEFT)
```

`pdf_generator.py:2831-2832` — replace the permanently-true "Auto-matching enabled" text with something honest. Read the surrounding lines first (`sed -n '2825,2835p' pdf_generator.py`), then set the label's initial text to:

```python
            text="Columns are matched to PDF fields automatically — check Tab 2 to adjust.",
```

- [ ] **Step 5: Run the full suite**

Run: `venv/bin/python -m pytest tests/ -v`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add pdf_generator.py tests/test_performance.py
git commit -m "fix: clamp window to screen size; correct misleading button labels"
```

---

### Task 17: Update the documentation to match reality

Several documented facts are now wrong — including one this plan disproved: CLAUDE.md states PyMuPDF can't author radio-button groups and that radio logic can only be unit-tested. Task 1 authored a real radio-group fixture, and Task 3 tests it end-to-end.

**Files:**
- Modify: `CLAUDE.md`, `ARCHITECTURE.md`, `getting_started.md`

- [ ] **Step 1: Correct CLAUDE.md**

Replace the radio-fixture bullet under "Dev Environment":

```markdown
- **Radio-button groups CAN be tested end-to-end.** `page.widgets()` yields one widget per radio *kid*, each reporting the group's field name but only its own on-state — `PDFAnalyzer._merge_widgets_by_name()` pools them into a single `PDFField` whose `on_states` holds every option (this is what makes `normalize_button_value` apply radio rather than checkbox semantics). PyMuPDF's `add_widget` cannot author a radio group, so `tests/_form_fixture.build_radio_form()` writes the PDF bytes directly.
```

Add to "Key Architecture Decisions":

```markdown
- **Widget merging (CRITICAL)**: `PDFAnalyzer._merge_widgets_by_name()` runs before comb detection and collapses widgets sharing a field name (radio kids, fields repeated across pages) into one record, pooling `on_states`. Emitting one `PDFField` per widget produced duplicate spreadsheet columns (which pandas mangles to `Name.1`) and broke radio filling.
- **Choice options are flattened to export values**: PyMuPDF returns `(export, display)` tuples when `/Opt` holds pairs. `PDFAnalyzer._read_options()` keeps the export value — the one the PDF stores. Unflattened tuples used to crash analysis outright.
- **Comb grouping is type-gated**: only `Text` widgets can form a comb. A horizontal row of numbered checkboxes passes the name and geometry heuristics and would otherwise be merged, writing one character per checkbox.
- **Mapping is never silently overwritten**: `_auto_map_fields()` only fills fields with no `excel_column`; `overwrite=True` is reserved for an explicit user action. `export_mapping_file()` assigns and *persists* the column names it writes, so the sheet and the app's mapping cannot disagree.
- **Generation results are reported inline** (`results_frame_tab3`), never via messagebox — see the macOS modal rule above.
```

- [ ] **Step 2: Correct ARCHITECTURE.md**

- Remove the `WelcomeDialog` entry (the class no longer exists — verify with `grep -rn "WelcomeDialog" .`).
- Correct the preview mouse-wheel description: the canvas handler **pans**; it does not zoom.
- Correct the theme description: the app uses ttkbootstrap (litera), not a clam-based theme with three button variants.

- [ ] **Step 3: Extend getting_started.md with the actual in-app workflow**

The guide currently covers only Acrobat preparation and never mentions the app's own Tab 1 → 2 → 3 flow or the Map Fields step. Add a section after the existing content:

```markdown
## Using the app

1. **Analyse Template** (Tab 1) — choose your PDF and click Analyze. The app finds
   the form fields and asks you to confirm each field's type.
2. **Export the spreadsheet** — click "Export Mapping File". You get a workbook with
   a **Data Entry** sheet to type into, and a **Field Mapping** sheet that tells you
   what each column accepts (tick boxes, dropdown options, dates).
3. **Map Fields** (Tab 2) — check that each PDF field is matched to the right column.
   Anything unmatched is flagged; unmatched fields come out blank.
4. **Generate PDFs** (Tab 3) — load your filled spreadsheet, review the records
   (rows missing required values are flagged), select who to generate, and click
   Generate. The results panel then tells you what was created, what needs a check,
   and where the files are.
```

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md ARCHITECTURE.md getting_started.md
git commit -m "docs: correct radio-fixture claim, theme/preview drift, and app workflow"
```

---

### Task 18: Full regression pass

- [ ] **Step 1: Run the whole suite**

Run: `venv/bin/python -m pytest tests/ -v`
Expected: every test passes. Record the count.

- [ ] **Step 2: End-to-end run against a real VCAA form**

```bash
venv/bin/python pdf_generator.py
```

Use a **real** VCAA Special Examination Arrangements PDF (the app's original purpose) and walk the whole path:

1. Analyse it. Confirm radio groups appear **once each**, with their real options shown in the audit dialog.
2. Export the mapping file. Confirm the "What to type" column names the real radio/dropdown values, and the Data Entry dropdowns work.
3. Fill two rows — one clean, one deliberately broken (over-long name in a combed field, an invalid dropdown value, a blank required field).
4. Load it. Confirm the sheet picker preselects Data Entry, the broken row is **visible** with a warning, and no template-drift warnings appear.
5. Generate both. Confirm the inline results panel reports 2 created with the truncation and dropdown warnings named.
6. **Open the generated PDFs in Adobe Reader** (not just Preview) and confirm: text is visible, the right radio button is selected, checkboxes are ticked.

Step 6 is the one that matters — a filled value that pypdf writes but Adobe won't render is the failure mode no unit test catches.

- [ ] **Step 3: Push**

```bash
git push origin test
```

Do **not** merge to `main` — per the project's branch policy, confirm with the user first.

---

## Deferred — a second plan

These came out of the review but do not belong in this sweep. Each is either a larger surface, or lower risk, or would fight with the changes above if done concurrently.

| Item | Why deferred |
|---|---|
| **Use PDF tooltips (`/TU`) as spreadsheet headers** | Genuinely valuable — government forms are full of `Text1`/`Check Box3` fields whose real label lives in the tooltip. But it changes header names, which touches mapping, saved templates, and every existing teacher spreadsheet. It needs its own migration story. |
| **Read the Required flag to seed `is_critical`** | Pairs naturally with the tooltip work; same field-flags read. |
| **Move analysis off the UI thread; add a Cancel button to generation** | A performance/threading surface of its own. Analysis freezes the UI on big PDFs, and a batch cannot be cancelled — real, but neither corrupts data. |
| **Full messagebox sweep** | This plan removes the dangerous post-batch dialogs and the redundant analysis one. The ~15 remaining are pre-action validations ("select a PDF first"), which are lower-frequency and far less costly if they misbehave. Worth doing as one deliberate pass. |
| **Sort export columns into page reading order** | A real usability win, but it changes the column order of every exported sheet — best done as its own change teachers can be told about, not smuggled in with correctness fixes. |
| **Preview canvas: horizontal pan, scrollbars, page navigation** | Self-contained UI work in `visual_preview.py` / the canvas handlers. |
| **Formula-injection and control-character sanitising of headers** | Needs a maliciously- or bizarrely-named PDF field to trigger. Real but remote, and a naive fix (prefixing `'`) breaks the mapping round-trip, so it needs thought. |
| **XFA / hybrid form detection** | Rare, hard to test, and the failure (values invisible in Acrobat) needs a real XFA form to validate against. |
| **Keyboard navigation and theme consistency** (Escape bindings on all dialogs, spacebar row-toggle, the undefined `Secondary.TButton`) | Pure polish; no correctness impact. |
