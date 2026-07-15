#!/usr/bin/env python3
"""
PDF Field Analyzer for Bulk PDF Generator v2.0
Extracts form fields and detects combed (character-by-character) fields.
"""

import re
from collections import defaultdict
from typing import List, Dict, Tuple
import fitz  # PyMuPDF
from models import PDFField


class PDFPasswordProtected(Exception):
    """The PDF needs a password to open."""


class PDFAnalyzer:
    """Analyzes PDF forms to extract field information."""

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.doc = None

    def __enter__(self):
        """Open PDF document."""
        self.doc = fitz.open(self.pdf_path)
        if self.doc.needs_pass:
            self.doc.close()
            self.doc = None
            raise PDFPasswordProtected(self.pdf_path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close PDF document."""
        if self.doc:
            self.doc.close()

    def analyze_fields(self) -> List[PDFField]:
        """
        Extract all form fields from PDF and detect combed fields.

        Returns:
            List of PDFField objects (combed fields grouped as single entries)
        """
        if not self.doc:
            raise ValueError("PDF not opened. Use context manager.")

        # Collect all widgets from all pages. Read button/choice state HERE,
        # while `page` is still alive — button_states() dereferences the owning
        # page through a weakref, and a deferred read (after this loop moves on)
        # raises ReferenceError. This is why multi-page forms with a checkbox or
        # radio on any non-final page previously failed analysis outright.
        all_widgets = []
        for page_num in range(len(self.doc)):
            page = self.doc.load_page(page_num)
            widgets = page.widgets()
            if widgets:
                for widget in widgets:
                    ftype = widget.field_type_string or 'Text'
                    all_widgets.append({
                        'name': widget.field_name,
                        'widget': widget,
                        'page_num': page_num + 1,   # 1-indexed
                        'field_type': ftype,
                        'on_states': (self._read_on_states(widget)
                                      if ftype in ("CheckBox", "RadioButton") else []),
                        'options': (self._read_options(widget)
                                    if ftype in ("ComboBox", "ListBox") else []),
                    })

        # Collapse same-named widgets (radio groups, multi-page fields) first,
        # then group comb character-boxes.
        records = self._merge_widgets_by_name(all_widgets)
        fields = self._detect_combed_fields(records)

        return fields

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

        Consumes the on_states/options ALREADY read (eagerly, while each page
        was alive) by analyze_fields — it never touches the widget for button
        or choice state itself, because by now the owning pages are gone.

        The first widget for a name supplies the representative geometry
        (page, rect) used by the visual preview.
        """
        merged = {}
        order = []

        for item in all_widgets:
            name = item['name']
            if not name:
                continue

            record = merged.get(name)
            if record is None:
                record = {
                    'name': name,
                    'widget': item['widget'],       # first widget = geometry source
                    'page_num': item['page_num'],
                    'field_type': item['field_type'],
                    'on_states': [],
                    'options': [],
                }
                merged[name] = record
                order.append(name)

            if item['field_type'] in ("CheckBox", "RadioButton"):
                for state in item['on_states']:
                    if state not in record['on_states']:
                        record['on_states'].append(state)
            elif item['field_type'] in ("ComboBox", "ListBox") and not record['options']:
                record['options'] = list(item['options'])

        return [merged[name] for name in order]

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

    def _is_sequential(self, items: List[Tuple]) -> bool:
        """
        Check if items form a sequential pattern (0, 1, 2, ...).

        Args:
            items: List of (index, name, widget, page_num) tuples

        Returns:
            True if indices are sequential
        """
        if len(items) < 2:
            return False

        indices = [item[0] for item in items]
        indices.sort()

        # Check if indices form a contiguous sequence from any start value
        start = indices[0]
        expected = list(range(start, start + len(indices)))
        return indices == expected

    def _looks_like_comb_row(self, items: List[Tuple]) -> bool:
        """Geometric sanity check for loose suffix-pattern comb groups.

        True comb character-boxes share a baseline, so their widget
        rectangles sit at approximately the same vertical position. Fields
        like Address_1 / Address_2 are stacked on different lines and fail
        this check, so they are kept as separate fields instead of being
        merged into one character-by-character comb (which would truncate
        each value to a single character — silent data loss).

        If geometry can't be read for any reason, returns True so behaviour
        falls back to the previous (permissive) grouping — no regression.

        Args:
            items: List of (index, name, record, page_num) tuples.

        Returns:
            True if all widgets lie on roughly the same horizontal row.
        """
        try:
            widgets = [it[2]['widget'] for it in items]
            tops = [w.rect[1] for w in widgets]                  # y0 of each box
            heights = [abs(w.rect[3] - w.rect[1]) for w in widgets]
        except (AttributeError, IndexError, KeyError, TypeError):
            return True

        if not tops:
            return True

        # Tolerance scales with box height (handles minor baseline jitter)
        # but never drops below a few points. Stacked lines differ by far more.
        median_h = sorted(heights)[len(heights) // 2] if heights else 0
        tolerance = max(4.0, median_h * 0.6)
        return (max(tops) - min(tops)) <= tolerance

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
        except (AttributeError, RuntimeError, TypeError, ReferenceError):
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

        MUST be called while the widget's owning page is still referenced:
        button_states() dereferences page→doc through a weakref, so a deferred
        read after the collection loop has moved on raises ReferenceError. That
        is why analyze_fields() reads on-states eagerly, inside the page loop.
        """
        try:
            states = widget.button_states() or {}
            normal = states.get("normal", []) or []
            return [str(s) for s in normal if s != "Off"]
        except (AttributeError, RuntimeError, TypeError, ReferenceError):
            return []

    def _get_widget_maxlen(self, widget) -> int:
        """
        Read MaxLen from a PDF widget's field dictionary.

        PyMuPDF 1.27.x does not expose text_maxlen on Widget objects,
        so we read MaxLen directly from the field's xref dictionary.

        Args:
            widget: A fitz.Widget object

        Returns:
            MaxLen value as int, or None if not set
        """
        # Try the direct attribute first (future PyMuPDF versions)
        if hasattr(widget, 'text_maxlen') and widget.text_maxlen:
            return int(widget.text_maxlen)

        # Fallback: read MaxLen from the field's PDF dictionary via xref
        try:
            annot_xref = widget.xref
            field_entry = self.doc.xref_get_key(annot_xref, "MaxLen")
            if field_entry[0] != "null":
                return int(field_entry[1])
        except (AttributeError, TypeError, ValueError, RuntimeError):
            pass

        return None

    def get_field_statistics(self, fields: List[PDFField]) -> Dict[str, int]:
        """
        Calculate field type statistics.

        Returns:
            Dict with counts: {"text": N, "text_combed": M, ...}
        """
        stats = defaultdict(int)

        for field in fields:
            field_type_key = field.field_type.lower().replace('-', '_').replace(' ', '_')
            stats[field_type_key] += 1

        return dict(stats)

    def render_page_preview(self, page_num: int, dpi: int = 150) -> bytes:
        """
        Render a page as PNG image data.

        Args:
            page_num: 1-indexed page number
            dpi: Resolution (150 for preview, 300 for export)

        Returns:
            PNG image data as bytes
        """
        if not self.doc:
            raise ValueError("PDF not opened. Use context manager.")

        page = self.doc.load_page(page_num - 1)  # 0-indexed
        pix = page.get_pixmap(dpi=dpi)

        # Convert to PNG bytes
        png_data = pix.tobytes("png")
        return png_data


def auto_name_template(pdf_filename: str) -> str:
    """
    Generate a clean template name from PDF filename.

    Rules:
    - Remove .pdf extension
    - Replace underscores/hyphens with spaces
    - Title case
    - Keep numbers

    Examples:
        Evidence_Application_2026.pdf → Evidence Application 2026
        student-records.pdf → Student Records
    """
    import os

    # Remove extension
    name = os.path.splitext(pdf_filename)[0]

    # Replace separators with spaces
    name = name.replace('_', ' ').replace('-', ' ')

    # Title case
    name = name.title()

    return name
