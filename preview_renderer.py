#!/usr/bin/env python3
"""
Threaded Preview Renderer for Bulk PDF Generator

Wraps VisualPreviewGenerator with:
- Background threading for PIL operations (copy, draw, resize)
- Debounced render requests (prevents flooding on rapid clicks)
- Stale-result guard via monotonic request counter
- Dual-pass rendering: fast BILINEAR first, then LANCZOS on settle
- Font path caching (resolved once at init)
- PhotoImage reference retention (prevents tkinter GC flicker)

Thread-safety: Only PIL operations run off-thread. PyMuPDF access
(_get_page_image) stays on the main thread since fitz.Document is
not thread-safe.
"""

import os
import platform
import threading
import tkinter as tk
from typing import Optional, Callable

from PIL import Image, ImageDraw, ImageFont, ImageTk

from models import PDFField
from visual_preview import VisualPreviewGenerator


class PreviewRenderer:
    """Manages threaded, debounced preview rendering."""

    def __init__(
        self,
        preview_generator: VisualPreviewGenerator,
        root: tk.Tk,
        canvas: tk.Canvas,
        on_complete: Callable[[ImageTk.PhotoImage], None],
    ):
        self._gen = preview_generator
        self._root = root
        self._canvas = canvas
        self._on_complete = on_complete

        # State
        self._request_id = 0
        self._debounce_timer: Optional[str] = None
        self._quality_timer: Optional[str] = None
        self._current_photo: Optional[ImageTk.PhotoImage] = None
        self._shutdown = False

        # Store the current raw image for zoom re-renders
        self.current_raw_image: Optional[Image.Image] = None

        # Cache font path once at init
        self._font: ImageFont.FreeTypeFont = self._resolve_font()

    def _resolve_font(self) -> ImageFont.FreeTypeFont:
        """Resolve platform font once, cache for all future renders."""
        try:
            system = platform.system()
            if system == 'Windows':
                win_font = os.path.join(
                    os.environ.get('WINDIR', r'C:\Windows'),
                    'Fonts', 'segoeui.ttf'
                )
                return ImageFont.truetype(win_font, 14)
            elif system == 'Darwin':
                for mac_font in (
                    '/System/Library/Fonts/Helvetica.ttc',
                    '/System/Library/Fonts/SFNSText.ttf',
                ):
                    if os.path.exists(mac_font):
                        return ImageFont.truetype(mac_font, 14)
        except (IOError, OSError):
            pass
        return ImageFont.load_default()

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

    def request_preview(self, field: PDFField, zoom_level: float, dpi: int = 200):
        """Request a debounced preview render. Non-blocking, returns immediately.

        Args:
            field: The PDF field to highlight.
            zoom_level: Current zoom multiplier (1.0 = fit to canvas).
            dpi: Render resolution for the PDF page.
        """
        if self._shutdown:
            return

        # Cancel any pending debounce/quality timers
        self._cancel_timers()

        # Increment request counter (stale-result guard)
        self._request_id += 1
        my_id = self._request_id

        # Schedule debounced render (150ms settle time)
        self._debounce_timer = self._root.after(
            150,
            self._on_debounce_fire, field, zoom_level, dpi, my_id,
        )

    def request_zoom(self, zoom_level: float):
        """Re-render the current raw image at a new zoom level. Non-blocking.

        Skips the PDF page fetch (reuses cached raw image).
        """
        if self._shutdown or self.current_raw_image is None:
            return

        self._cancel_timers()
        self._request_id += 1
        my_id = self._request_id

        # Zoom re-renders don't need debounce — fire immediately but off-thread
        self._debounce_timer = self._root.after(
            50,
            self._do_resize, self.current_raw_image, zoom_level, my_id, False,
        )

    def _cancel_timers(self):
        """Cancel pending debounce and quality timers."""
        if self._debounce_timer is not None:
            self._root.after_cancel(self._debounce_timer)
            self._debounce_timer = None
        if self._quality_timer is not None:
            self._root.after_cancel(self._quality_timer)
            self._quality_timer = None

    def _on_debounce_fire(
        self, field: PDFField, zoom_level: float, dpi: int, my_id: int
    ):
        """Called on main thread when debounce timer fires."""
        self._debounce_timer = None

        if self._shutdown or my_id != self._request_id:
            return

        # Main-thread work: get cached page image (PyMuPDF access)
        if not self._gen or not self._gen.doc:
            return

        try:
            page_img = self._gen._get_page_image(field.page, dpi)
        except Exception:
            return

        # Spawn worker thread for the expensive PIL work
        t = threading.Thread(
            target=self._worker_render,
            args=(page_img, field, zoom_level, dpi, my_id),
            daemon=True,
        )
        t.start()

    def _worker_render(
        self,
        page_img: Image.Image,
        field: PDFField,
        zoom_level: float,
        dpi: int,
        my_id: int,
    ):
        """Worker thread: copy image, draw overlays, resize. No PyMuPDF access."""
        if self._shutdown or my_id != self._request_id:
            return

        try:
            # Copy and draw overlays
            preview_img = page_img.copy()
            draw = ImageDraw.Draw(preview_img)

            scale = dpi / 72
            x0, y0, x1, y1 = field.rect
            px0, py0 = int(x0 * scale), int(y0 * scale)
            px1, py1 = int(x1 * scale), int(y1 * scale)

            draw.rectangle([px0, py0, px1, py1], outline='red', width=3)

            # Label
            label_text = field.field_name
            if field.is_combed:
                label_text += f" ({field.length} chars)"

            bbox = draw.textbbox((0, 0), label_text, font=self._font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]

            label_x = px0
            label_y = py0 - text_h - 25
            if label_y < 10:
                label_y = py1 + 5

            draw.rectangle(
                [label_x - 5, label_y - 5, label_x + text_w + 5, label_y + text_h + 5],
                fill='yellow', outline='black', width=1,
            )
            draw.text((label_x, label_y), label_text, fill='black', font=self._font)

            # Store raw image for zoom re-renders
            self.current_raw_image = preview_img

        except Exception:
            return

        if self._shutdown or my_id != self._request_id:
            return

        # Hand back to main thread: it captures canvas dims (Tcl is not
        # thread-safe) and spawns the resize worker. Quality (LANCZOS)
        # pass is chained from within _do_resize. (C4)
        if self._shutdown or my_id != self._request_id:
            return
        self._root.after(
            0, self._do_resize, preview_img, zoom_level, my_id, False,
        )

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

        if self._shutdown or my_id != self._request_id:
            return

        # Deliver to main thread
        self._root.after(0, self._deliver, resized, zoom_level, my_id)

    def _deliver(self, resized: Image.Image, zoom_level: float, my_id: int):
        """Main thread: update canvas with rendered image."""
        if self._shutdown or my_id != self._request_id:
            return

        try:
            photo = ImageTk.PhotoImage(resized)
            self._current_photo = photo  # prevent GC

            self._canvas.delete("all")

            canvas_w = self._canvas.winfo_width()
            canvas_h = self._canvas.winfo_height()
            img_w, img_h = resized.size

            if zoom_level > 1.0:
                self._canvas.config(scrollregion=(0, 0, img_w, img_h))
                self._canvas.create_image(img_w // 2, img_h // 2,
                                          image=photo, anchor=tk.CENTER)
            else:
                self._canvas.config(scrollregion=(0, 0, canvas_w, canvas_h))
                self._canvas.create_image(canvas_w // 2, canvas_h // 2,
                                          image=photo, anchor=tk.CENTER)

            self._on_complete(photo)

        except Exception:
            pass

    def shutdown(self):
        """Cancel all pending work. Call before closing the preview generator."""
        self._shutdown = True
        self._cancel_timers()

    def update_generator(self, preview_generator: VisualPreviewGenerator):
        """Update the underlying preview generator (e.g. after loading a new PDF)."""
        self.shutdown()
        self._gen = preview_generator
        self._shutdown = False
        self._request_id = 0
        self.current_raw_image = None
        self._current_photo = None
