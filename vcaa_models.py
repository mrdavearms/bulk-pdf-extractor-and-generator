#!/usr/bin/env python3
"""
Data models for Bulk PDF Generator v2.0
Defines data structures for templates, fields, and configurations.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import json
import os
import tempfile


@dataclass
class PDFField:
    """Represents a single field (or grouped combed field) in a PDF form."""
    field_name: str          # Base name (e.g., "First_Name")
    field_type: str          # "Text", "Text-Combed", "Checkbox", "Signature"
    page: int                # 1-indexed page number
    length: Optional[int]    # For combed: character count, else None
    is_combed: bool          # True if field is combed
    combed_fields: List[str] # For combed: ["First_Name[0]", ...], else []
    rect: Tuple[float, float, float, float]  # (x0, y0, x1, y1) for visual preview
    current_value: str = ""  # Current value in PDF (usually blank)
    is_critical: bool = False  # Marked as critical field
    excel_column: Optional[str] = None  # Mapped Excel column name
    data_type: str = "text"  # "text", "number", or "date" (DD/MM/YYYY)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'field_name': self.field_name,
            'field_type': self.field_type,
            'page': self.page,
            'length': self.length,
            'is_combed': self.is_combed,
            'combed_fields': self.combed_fields,
            'rect': list(self.rect),
            'current_value': self.current_value,
            'is_critical': self.is_critical,
            'excel_column': self.excel_column,
            'data_type': self.data_type
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'PDFField':
        """Create from dictionary."""
        return cls(
            field_name=data['field_name'],
            field_type=data['field_type'],
            page=data['page'],
            length=data.get('length'),
            is_combed=data['is_combed'],
            combed_fields=data.get('combed_fields', []),
            rect=tuple(data['rect']),
            current_value=data.get('current_value', ''),
            is_critical=data.get('is_critical', False),
            excel_column=data.get('excel_column'),
            data_type=data.get('data_type', 'text')
        )


@dataclass
class TemplateConfig:
    """Configuration for a PDF template."""
    template_name: str
    pdf_filename: str
    pdf_path: str
    created_date: str  # ISO format
    last_used: str     # ISO format
    total_fields: int
    field_types: Dict[str, int]  # {"text": 42, "text_combed": 3, ...}
    mapping_file: str  # Filename of .xlsx mapping file
    use_auto_matching: bool = True
    critical_fields: List[str] = None
    field_data_types: Dict[str, str] = None  # {field_name: "text"|"number"|"date"}
    notes: str = ""
    version: str = "2.0"

    def __post_init__(self):
        if self.critical_fields is None:
            self.critical_fields = []
        if self.field_data_types is None:
            self.field_data_types = {}

    def to_json(self) -> str:
        """Serialize to JSON string."""
        data = asdict(self)
        return json.dumps(data, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'TemplateConfig':
        """Deserialize from JSON string.

        Handles extra keys gracefully so that config files saved by a
        newer version of the app still load without error.
        """
        data = json.loads(json_str)
        import dataclasses
        valid_keys = {f.name for f in dataclasses.fields(cls)}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

    @classmethod
    def from_file(cls, filepath: str) -> 'TemplateConfig':
        """Load from JSON file. Raises ValueError on bad data."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return cls.from_json(f.read())
        except json.JSONDecodeError as e:
            raise ValueError(f"Template file is not valid JSON: {filepath}") from e
        except (TypeError, KeyError) as e:
            raise ValueError(f"Template file has missing or invalid fields: {filepath}") from e

    def save_to_file(self, filepath: str):
        """Save to JSON file atomically to prevent corruption on crash."""
        dir_name = os.path.dirname(os.path.abspath(filepath))
        os.makedirs(dir_name, exist_ok=True)
        with tempfile.NamedTemporaryFile('w', dir=dir_name,
                                         suffix='.tmp', delete=False,
                                         encoding='utf-8') as tmp:
            tmp.write(self.to_json())
            tmp_path = tmp.name
        os.replace(tmp_path, filepath)


@dataclass
class AppSettings:
    """Application settings."""
    templates_directory: str
    show_welcome: bool = True
    auto_load_last_template: bool = True
    last_template: Optional[str] = None
    combed_field_padding: bool = False
    combed_field_align: str = "left"  # "left" or "right"
    school_name: str = ""
    school_year: str = ""

    @property
    def school_configured(self) -> bool:
        """True if school name has been set by the user."""
        return bool(self.school_name.strip())

    def to_json(self) -> str:
        """Serialize to JSON string."""
        data = asdict(self)
        return json.dumps(data, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'AppSettings':
        """Deserialize from JSON string.

        Handles missing keys gracefully so that older settings files
        (saved before new fields were added) still load without error.
        """
        data = json.loads(json_str)
        # Build kwargs using only keys the dataclass actually accepts,
        # letting missing keys fall back to their field defaults.
        import dataclasses
        valid_keys = {f.name for f in dataclasses.fields(cls)}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

    @classmethod
    def from_file(cls, filepath: str) -> 'AppSettings':
        """Load from JSON file."""
        try:
            with open(filepath, 'r') as f:
                return cls.from_json(f.read())
        except (FileNotFoundError, PermissionError, OSError,
                json.JSONDecodeError, TypeError, KeyError):
            return cls.get_defaults()

    def save_to_file(self, filepath: str):
        """Save to JSON file atomically to prevent corruption on crash."""
        dir_name = os.path.dirname(os.path.abspath(filepath))
        os.makedirs(dir_name, exist_ok=True)
        with tempfile.NamedTemporaryFile('w', dir=dir_name,
                                         suffix='.tmp', delete=False,
                                         encoding='utf-8') as tmp:
            tmp.write(self.to_json())
            tmp_path = tmp.name
        os.replace(tmp_path, filepath)

    @classmethod
    def get_defaults(cls) -> 'AppSettings':
        """Get default settings."""
        import os
        default_dir = os.path.expanduser("~/Documents/BulkPDFGenerator/templates")
        return cls(templates_directory=default_dir)
