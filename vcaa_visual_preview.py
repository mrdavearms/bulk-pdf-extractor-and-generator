#!/usr/bin/env python3
"""
Visual Field Preview Module for VCAA PDF Generator v2.0
Handles PDF page rendering and field highlighting for visual preview.
"""

import os
from collections import OrderedDict
from typing import Optional, Tuple
from PIL import Image, ImageDraw, ImageFont
import fitz  # PyMuPDF
from vcaa_models import PDFField

_MAX_CACHED_PAGES = 5  # Cap memory cache (~60 MB at 200 DPI)


class VisualPreviewGenerator:
    """Generates visual previews of PDF pages with field highlighting."""

    def __init__(self, pdf_path: str, cache_dir: Optional[str] = None):
        self.pdf_path = pdf_path
        self.cache_dir = cache_dir or os.path.join(
            os.path.dirname(pdf_path),
            '.preview_cache'
        )
        self.doc = None
        self._cached_pages = OrderedDict()  # LRU cache {cache_key: Image}

    def __enter__(self):
        """Open PDF document."""
        self.doc = fitz.open(self.pdf_path)
        # Ensure cache directory exists
        os.makedirs(self.cache_dir, exist_ok=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close PDF document."""
        if self.doc:
            self.doc.close()

    def generate_field_preview(
        self,
        field: PDFField,
        dpi: int = 150,
        highlight_color: str = 'red',
        label_bg_color: str = 'yellow'
    ) -> Image.Image:
        """
        Generate a preview image of a PDF page with a field highlighted.

        Args:
            field: The PDFField to highlight
            dpi: Resolution for rendering (150 for preview, 300 for export)
            highlight_color: Color for field outline
            label_bg_color: Background color for field label

        Returns:
            PIL Image with highlighted field
        """
        if not self.doc:
            raise ValueError("PDF not opened. Use context manager.")

        # Get or render the page
        page_img = self._get_page_image(field.page, dpi)

        # Create a copy to draw on
        preview_img = page_img.copy()
        draw = ImageDraw.Draw(preview_img)

        # Scale rect coordinates from PDF points to pixels
        scale = dpi / 72  # PDF uses 72 DPI
        x0, y0, x1, y1 = field.rect
        px0 = int(x0 * scale)
        py0 = int(y0 * scale)
        px1 = int(x1 * scale)
        py1 = int(y1 * scale)

        # Draw highlight rectangle
        draw.rectangle(
            [px0, py0, px1, py1],
            outline=highlight_color,
            width=3
        )

        # Prepare label text
        label_text = field.field_name
        if field.is_combed:
            label_text += f" ({field.length} chars)"

        # Draw label with background - try platform fonts with absolute paths
        font = None
        try:
            import platform
            if platform.system() == 'Windows':
                # Use absolute path to Windows font directory
                win_font = os.path.join(
                    os.environ.get('WINDIR', r'C:\Windows'),
                    'Fonts', 'segoeui.ttf'
                )
                font = ImageFont.truetype(win_font, 14)
            elif platform.system() == 'Darwin':
                for mac_font in (
                    '/System/Library/Fonts/Helvetica.ttc',
                    '/System/Library/Fonts/SFNSText.ttf',
                ):
                    if os.path.exists(mac_font):
                        font = ImageFont.truetype(mac_font, 14)
                        break
        except (IOError, OSError):
            pass
        if font is None:
            font = ImageFont.load_default()

        # Get text size for background
        bbox = draw.textbbox((0, 0), label_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Position label above field (or below if too close to top)
        label_x = px0
        label_y = py0 - text_height - 25

        if label_y < 10:  # Too close to top
            label_y = py1 + 5  # Put below instead

        # Draw label background
        draw.rectangle(
            [label_x - 5, label_y - 5, label_x + text_width + 5, label_y + text_height + 5],
            fill=label_bg_color,
            outline='black',
            width=1
        )

        # Draw label text
        draw.text((label_x, label_y), label_text, fill='black', font=font)

        return preview_img

    def _get_page_image(self, page_num: int, dpi: int) -> Image.Image:
        """
        Get or render a page as an image.

        Uses cache to avoid re-rendering.

        Args:
            page_num: 1-indexed page number
            dpi: Resolution for rendering

        Returns:
            PIL Image of the page
        """
        cache_key = f"{page_num}_{dpi}"

        # Check memory cache (LRU touch)
        if cache_key in self._cached_pages:
            self._cached_pages.move_to_end(cache_key)
            return self._cached_pages[cache_key]

        # Check disk cache
        cache_filename = f"page_{page_num}_dpi_{dpi}.png"
        cache_path = os.path.join(self.cache_dir, cache_filename)

        if os.path.exists(cache_path):
            img = Image.open(cache_path)
            img.load()  # Force full read into memory; releases file handle
            self._cached_pages[cache_key] = img
            return img

        # Render from PDF
        page = self.doc.load_page(page_num - 1)  # 0-indexed
        pix = page.get_pixmap(dpi=dpi)

        # Convert to PIL Image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # Save to disk cache
        img.save(cache_path, "PNG")

        # Save to memory cache with LRU eviction
        self._cached_pages[cache_key] = img
        while len(self._cached_pages) > _MAX_CACHED_PAGES:
            self._cached_pages.popitem(last=False)  # Evict oldest

        return img

    def clear_cache(self):
        """Clear both memory and disk cache."""
        self._cached_pages.clear()

        # Clear disk cache (only app-generated files, with error handling)
        if os.path.exists(self.cache_dir):
            for file in os.listdir(self.cache_dir):
                if file.startswith('page_') and file.endswith('.png'):
                    try:
                        os.remove(os.path.join(self.cache_dir, file))
                    except OSError:
                        pass  # File may be locked; skip silently

    def get_cache_size(self) -> int:
        """Get total size of disk cache in bytes."""
        if not os.path.exists(self.cache_dir):
            return 0

        total_size = 0
        for file in os.listdir(self.cache_dir):
            file_path = os.path.join(self.cache_dir, file)
            if os.path.isfile(file_path):
                total_size += os.path.getsize(file_path)

        return total_size


def format_cache_size(size_bytes: int) -> str:
    """Format cache size in human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
