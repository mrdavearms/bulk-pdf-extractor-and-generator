#!/usr/bin/env python3
"""
Data models for VCAA PDF Generator v2.0
Defines data structures for templates, fields, and configurations.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import json


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
            'excel_column': self.excel_column
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
            excel_column=data.get('excel_column')
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
    notes: str = ""
    version: str = "2.0"

    def __post_init__(self):
        if self.critical_fields is None:
            self.critical_fields = []

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
        """Load from JSON file."""
        with open(filepath, 'r') as f:
            return cls.from_json(f.read())

    def save_to_file(self, filepath: str):
        """Save to JSON file."""
        with open(filepath, 'w') as f:
            f.write(self.to_json())


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
        except (FileNotFoundError, json.JSONDecodeError):
            return cls.get_defaults()

    def save_to_file(self, filepath: str):
        """Save to JSON file."""
        with open(filepath, 'w') as f:
            f.write(self.to_json())

    @classmethod
    def get_defaults(cls) -> 'AppSettings':
        """Get default settings."""
        import os
        default_dir = os.path.expanduser("~/Documents/VCAA_App/templates")
        return cls(templates_directory=default_dir)
