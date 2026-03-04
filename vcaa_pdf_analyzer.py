#!/usr/bin/env python3
"""
PDF Field Analyzer for Bulk PDF Generator v2.0
Extracts form fields and detects combed (character-by-character) fields.
"""

import re
from collections import defaultdict
from typing import List, Dict, Tuple
import fitz  # PyMuPDF
from vcaa_models import PDFField


class PDFAnalyzer:
    """Analyzes PDF forms to extract field information."""

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.doc = None

    def __enter__(self):
        """Open PDF document."""
        self.doc = fitz.open(self.pdf_path)
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

        # Collect all widgets from all pages
        all_widgets = []
        for page_num in range(len(self.doc)):
            page = self.doc.load_page(page_num)
            widgets = page.widgets()
            if widgets:
                for widget in widgets:
                    # Store widget with page number
                    all_widgets.append({
                        'widget': widget,
                        'page_num': page_num + 1  # 1-indexed
                    })

        # Detect and group combed fields
        fields = self._detect_combed_fields(all_widgets)

        return fields

    def _detect_combed_fields(self, all_widgets: List[dict]) -> List[PDFField]:
        """
        Group combed fields by base name pattern.

        Supported patterns:
        - Field_Name[0], Field_Name[1], ... (bracketed)
        - FieldName_0, FieldName_1, ...     (underscore)
        - FieldName0, FieldName1, ...       (sequential)
        """
        # Group by base name
        groups = defaultdict(list)

        for item in all_widgets:
            widget = item['widget']
            page_num = item['page_num']
            name = widget.field_name

            if not name:
                continue

            # Try pattern 1: Field[N]
            match = re.match(r'^(.+?)\[(\d+)\]$', name)
            if match:
                base = match.group(1)
                index = int(match.group(2))
                groups[base].append((index, name, widget, page_num))
                continue

            # Try pattern 2: Field_N
            match = re.match(r'^(.+?)_(\d+)$', name)
            if match:
                # Only group if it ends with a digit
                potential_base = match.group(1)
                index = int(match.group(2))

                # Check if this looks like a sequence (multiple similar fields)
                # We'll do final grouping later
                groups[(potential_base, '_')].append((index, name, widget, page_num))
                continue

            # Try pattern 3: FieldN (no separator, e.g. StudentNumber0)
            # But NOT "Provision 1" — space before number means separate named fields
            match = re.match(r'^(.+?)(\d+)$', name)
            if match:
                potential_base = match.group(1)
                if potential_base.endswith(' '):
                    # "Provision 1", "Date implemented 3" — separate fields, not combed
                    groups[name].append((0, name, widget, page_num))
                    continue
                index = int(match.group(2))
                groups[(potential_base, '')].append((index, name, widget, page_num))
                continue

            # Not a pattern - single field
            groups[name].append((0, name, widget, page_num))

        # Process groups
        result = []
        for base_key, items in groups.items():
            # Handle tuple keys (from patterns 2 & 3)
            if isinstance(base_key, tuple):
                base_name, separator = base_key
            else:
                base_name = base_key
                separator = None

            # Sort by index
            items.sort(key=lambda x: x[0])

            # Determine if this is a true combed field (multiple sequential items)
            if len(items) > 1 and self._is_sequential(items):
                # Combed field - group them
                widget_0 = items[0][2]  # First widget for metadata

                result.append(PDFField(
                    field_name=base_name,
                    field_type='Text-Combed',
                    page=items[0][3],  # Page of first field
                    length=len(items),
                    is_combed=True,
                    combed_fields=[item[1] for item in items],  # All field names
                    rect=tuple(widget_0.rect),
                    current_value=widget_0.field_value or "",
                    is_critical=False,
                    excel_column=None
                ))
            else:
                # Single field(s) - treat each separately
                for index, name, widget, page_num in items:
                    ftype = widget.field_type_string or 'Text'
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
                        combed_fields=[],  # Single-field combed: no sub-fields
                        rect=tuple(widget.rect),
                        current_value=widget.field_value or "",
                        is_critical=False,
                        excel_column=None
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
