#!/usr/bin/env python3
"""
Combed Field Filler Module for Bulk PDF Generator v2.0
Handles splitting text into character-by-character fields.
"""

from typing import Dict, List
from models import PDFField


class CombedFieldFiller:
    """Fills combed (character-by-character) PDF fields."""

    def __init__(self, settings: Dict = None):
        """
        Initialize with optional settings.

        Settings:
            padding: bool - Pad fields with spaces (default: False)
            align: str - 'left' or 'right' alignment (default: 'left')
        """
        self.settings = settings or {}
        self.padding = self.settings.get('padding', False)
        self.align = self.settings.get('align', 'left')

    def fill_field(
        self,
        field: PDFField,
        text_value: str
    ) -> Dict[str, str]:
        """
        Fill a combed field by splitting text into individual characters.

        Args:
            field: PDFField object with combed metadata
            text_value: String to split (e.g., "John")

        Returns:
            Dict mapping field names to character values
            Example: {'First_Name[0]': 'J', 'First_Name[1]': 'o', ...}
        """
        if not field.is_combed:
            # Regular field - return as single value
            return {field.field_name: str(text_value)}

        if not field.combed_fields:
            # Single-field combed (PDF has comb property on one field).
            # Truncate to length and write to the original field name.
            text = str(text_value).strip()
            if field.length and len(text) > field.length:
                text = text[:field.length]
            return {field.field_name: text}

        # Clean and prepare text
        text = str(text_value).strip()

        # Truncate if too long
        if len(text) > field.length:
            text = text[:field.length]

        # Determine alignment
        if self.align == 'right' and len(text) < field.length:
            # Right-align by padding left
            text = text.rjust(field.length)
        elif self.padding and len(text) < field.length:
            # Pad with spaces to fill all boxes
            text = text.ljust(field.length)

        # Create field mapping
        field_values = {}

        # Fill each character box
        for idx, char in enumerate(text):
            if idx < len(field.combed_fields):
                field_name = field.combed_fields[idx]
                field_values[field_name] = char

        # Fill remaining boxes with empty string (or spaces if padding)
        for idx in range(len(text), field.length):
            if idx < len(field.combed_fields):
                field_name = field.combed_fields[idx]
                field_values[field_name] = ' ' if self.padding else ''

        return field_values

    def fill_multiple_fields(
        self,
        fields: List[PDFField],
        data_row: Dict[str, str]
    ) -> Dict[str, str]:
        """
        Fill multiple fields (both combed and regular) from a data row.

        Args:
            fields: List of PDFField objects
            data_row: Dict mapping field names to values (from Excel)

        Returns:
            Dict mapping PDF field names to values (expanded for combed fields)
        """
        all_field_values = {}

        for field in fields:
            # Get value from data row (case-insensitive matching)
            field_name_lower = field.field_name.lower()
            value = None

            # Try to find matching column
            for col_name, col_value in data_row.items():
                if col_name.lower() == field_name_lower:
                    value = col_value
                    break

            if value is None:
                # No matching data - skip this field
                continue

            # Fill the field (handles both combed and regular)
            field_values = self.fill_field(field, value)
            all_field_values.update(field_values)

        return all_field_values

    def validate_overflow(
        self,
        field: PDFField,
        text_value: str
    ) -> Dict[str, object]:
        """
        Check if text will overflow a combed field.

        Args:
            field: PDFField object
            text_value: String to check

        Returns:
            Dict with validation info:
            {
                'is_valid': bool,
                'will_truncate': bool,
                'original_length': int,
                'field_length': int,
                'truncated_text': str (if applicable)
            }
        """
        text = str(text_value).strip()

        result = {
            'is_valid': True,
            'will_truncate': False,
            'original_length': len(text),
            'field_length': field.length if field.is_combed else None,
            'truncated_text': None
        }

        if not field.is_combed:
            # Not a combed field - no overflow possible
            return result

        if len(text) > field.length:
            result['is_valid'] = False
            result['will_truncate'] = True
            result['truncated_text'] = text[:field.length]

        return result

    def get_overflow_warnings(
        self,
        fields: List[PDFField],
        data_rows: List[Dict[str, str]]
    ) -> List[Dict]:
        """
        Check all data for potential overflow issues.

        Args:
            fields: List of PDFField objects
            data_rows: List of data dicts (from Excel)

        Returns:
            List of warning dicts:
            [{
                'row_index': int,
                'field_name': str,
                'original_text': str,
                'truncated_text': str
            }, ...]
        """
        warnings = []

        for row_idx, data_row in enumerate(data_rows):
            for field in fields:
                if not field.is_combed:
                    continue

                # Get value from data row
                field_name_lower = field.field_name.lower()
                value = None

                for col_name, col_value in data_row.items():
                    if col_name.lower() == field_name_lower:
                        value = col_value
                        break

                if value is None:
                    continue

                # Check for overflow
                validation = self.validate_overflow(field, value)

                if validation['will_truncate']:
                    warnings.append({
                        'row_index': row_idx,
                        'field_name': field.field_name,
                        'original_text': str(value),
                        'truncated_text': validation['truncated_text']
                    })

        return warnings


def split_date_combed(date_str: str, day_field: PDFField, month_field: PDFField, year_field: PDFField) -> Dict[str, str]:
    """
    Helper function to split a date into combed day/month/year fields.

    Args:
        date_str: Date string in DD/MM/YYYY format
        day_field: PDFField for day (2-char combed)
        month_field: PDFField for month (2-char combed)
        year_field: PDFField for year (4-char combed)

    Returns:
        Dict mapping all combed fields to characters

    Example:
        "25/12/2026" → {'DOB_Day[0]': '2', 'DOB_Day[1]': '5', ...}
    """
    from datetime import datetime
    import pandas as pd

    # Parse date
    if isinstance(date_str, (datetime, pd.Timestamp)):
        date_obj = date_str
    else:
        try:
            # Try DD/MM/YYYY format
            date_obj = datetime.strptime(str(date_str), '%d/%m/%Y')
        except ValueError:
            try:
                # Try YYYY-MM-DD format
                date_obj = datetime.strptime(str(date_str), '%Y-%m-%d')
            except ValueError:
                # Can't parse - return empty
                return {}

    # Format components with zero-padding
    day = date_obj.strftime('%d')    # 01-31
    month = date_obj.strftime('%m')  # 01-12
    year = date_obj.strftime('%Y')   # 2026

    # Fill combed fields
    filler = CombedFieldFiller()

    result = {}
    result.update(filler.fill_field(day_field, day))
    result.update(filler.fill_field(month_field, month))
    result.update(filler.fill_field(year_field, year))

    return result
