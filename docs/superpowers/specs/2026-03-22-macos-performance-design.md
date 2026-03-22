# macOS Performance Fix — Design Spec

**Date**: 2026-03-22
**Status**: Draft
**Problem**: App is nearly unusable on macOS — tab switches freeze, field selection lags, dialogs flicker. Root cause: synchronous rendering on the main thread, excessive widget churn, and unthrottled event handlers amplified by the macOS Aqua/AppKit backend.

---

## 1. PreviewRenderer Extraction (CRITICAL)

### Problem
`on_field_selected()` in `pdf_generator.py` synchronously renders a 200 DPI PDF page, draws overlays, and LANCZOS-resizes it — all on the main thread. This blocks the event loop for 100–500ms per click. macOS Aqua has zero tolerance for main-thread blocking.

### Solution
Create `preview_renderer.py` with a `PreviewRenderer` class:

```
PreviewRenderer
├── __init__(preview_generator, root, canvas, on_complete_callback)
├── request_preview(field, zoom_level)   # debounced, non-blocking
├── cancel()                             # cancel pending render
├── _debounce_timer: str | None          # after() ID
├── _worker_thread: threading.Thread
├── _current_photo: ImageTk.PhotoImage   # prevents GC
└── _font_path: str                      # cached at init
```

**Thread-safety design (CRITICAL):**
PyMuPDF's `fitz.Document` is NOT thread-safe. The threading boundary is drawn as follows:
- **Main thread only**: `_get_page_image()` (which calls `fitz.Document.load_page()` and `get_pixmap()`). This is fast on cache hits (returns cached PIL Image).
- **Worker thread**: `Image.copy()`, `ImageDraw` overlay drawing, `Image.resize()` — pure PIL operations, no PyMuPDF access.
- The main thread calls `_get_page_image()` synchronously (cheap on cache hit), then hands the PIL Image to the worker thread for the expensive overlay + resize work.

**Stale-result guard:**
A monotonic `self._request_id` counter increments on every `request_preview()` call. The worker thread captures the counter at spawn time. On completion, it checks `if self._request_id != my_id: return` before scheduling the callback. This prevents stale renders from overwriting newer results during rapid clicking.

**Lifecycle management:**
`PreviewRenderer.shutdown()` must be called before `_close_preview_generator()` closes the `fitz.Document`. `shutdown()` cancels any pending debounce timer and sets a `_shutdown` flag that the worker thread checks. The worker thread is a daemon thread so it won't block app exit, but the stale-result guard ensures it won't try to deliver results after shutdown.

**Behaviour:**
- `request_preview()` cancels any pending debounce timer, increments `_request_id`, starts a new 150ms `after()` timer
- When the timer fires: main thread calls `_get_page_image(field, dpi)` (cache hit = fast), then spawns a daemon thread with the PIL Image + field data + request_id
- **Fast pass**: worker thread does overlay + `BILINEAR` resize at the current DPI. On completion, checks `_request_id`, schedules `root.after(0, callback, photo_image)`
- **Quality pass**: a second `after(300ms)` re-renders at full 200 DPI + `LANCZOS` (only if no new request has arrived, checked via `_request_id`)
- `_current_photo` holds a reference to prevent tkinter GC flicker
- Font path is resolved once in `__init__` via `platform.system()` + `os.path.exists()`, cached as `self._font_path`

**Integration with pdf_generator.py:**
- `on_field_selected()` calls `self.preview_renderer.request_preview(field, self.zoom_level)` — returns immediately
- `_zoom_preview()` calls the same method — returns immediately
- The callback updates `self.preview_canvas` with the new image
- Remove direct calls to `self.preview_generator.generate_field_preview()` and `_render_preview_at_zoom()` from the main thread

**Existing `visual_preview.py` unchanged** — `PreviewGenerator` remains the low-level engine. `PreviewRenderer` wraps it with threading/debouncing.

---

## 2. Treeview Batch Updates (HIGH)

### Problem
`select_all_tab3()` and `deselect_all_tab3()` call `tree.item(item_id, values=...)` once per row — each call is a synchronous Tcl round-trip with a redraw. For 200 students: 200 round-trips, ~300–500ms freeze. Also auto-called after every data load.

### Solution
- Suppress visual updates during bulk operations by temporarily detaching the treeview from its parent (or using a batch wrapper)
- Pattern: `tree.pack_forget()` → loop → `tree.pack()` (forces single redraw on reattach)
- Alternative: use `tree.tag_configure()` for selection state instead of modifying `values` per row — tags are cheaper than value writes
- Defer `select_all_tab3()` after data load with `root.after_idle()` so the treeview renders first

**Apply same pattern to:** `show_preview_tab3()` row insertion loop.

---

## 3. Tab 2 In-Place Updates (HIGH)

### Problem
`_refresh_tab2_mappings()` destroys all child widgets of `_tab2_mapping_frame` then recreates them from scratch. For 50 fields = 250 widget creates. Triggered by analysis, template load, Excel load, auto-map, clear-all. Each widget creation invokes AppKit on macOS.

### Solution
- Track mapping row widgets in a list: `self._mapping_rows: list[dict]` where each dict holds `{frame, label, combobox, status_label, hint_label}`
- On refresh: if field count matches, update existing widgets in-place (combobox values, status text, hint text)
- Only destroy and rebuild if the field count has changed OR field names differ (same count but different PDF = full rebuild)
- When rebuilding, batch-create all widgets with the scrollable frame's `<Configure>` binding temporarily suppressed (see Section 4)

---

## 4. ScrollableFrame `<Configure>` Debouncing (HIGH)

### Problem
`<Configure>` fires on every child widget add/remove/resize. During Tab 2 rebuild, this fires hundreds of times, each calling `canvas.configure(scrollregion=canvas.bbox("all"))`.

### Solution
Replace direct binding with `after_idle()` debounce:

```python
def __init__(self, ...):
    self._config_pending = False
    self.scrollable_frame.bind("<Configure>", self._on_configure)

def _on_configure(self, event):
    if not self._config_pending:
        self._config_pending = True
        self.canvas.after_idle(self._update_scrollregion)

def _update_scrollregion(self):
    self._config_pending = False
    self.canvas.configure(scrollregion=self.canvas.bbox("all"))
```

Multiple `<Configure>` events within the same idle cycle collapse into one `bbox()` call.

Apply the same pattern to `FieldTypeAuditDialog`'s configure binding (the lambda at line 581 inside `__init__` — this dialog creates its own canvas/scrollbar locally, does not use `ScrollableFrame`).

---

## 5. Event Throttling (MEDIUM)

### 5a. Treeview Hover
**Problem**: `<Motion>` in `theme.py:bind_treeview_hover()` fires at 60Hz on macOS trackpad. Each event calls `identify_row()` (Tcl query).

**Solution**: Add a 50ms `after()` guard — ignore `<Motion>` events that arrive within 50ms of the last processed event.

```python
def on_motion(event):
    nonlocal _throttle_id
    if _throttle_id is not None:
        return
    _throttle_id = tree.after(50, _process_motion, event.y)
```

### 5b. Generation Progress
**Problem**: `after(0, update_progress)` called per record floods the Core Foundation timer.

**Solution**: Throttle inside the worker loop, *before* the `root.after(0, ...)` call:
```python
import time
_last_progress = 0
for i, record in enumerate(records):
    # ... generate PDF ...
    now = time.monotonic()
    if i % 10 == 0 or (now - _last_progress) >= 0.2:
        _last_progress = now
        self.root.after(0, self.update_progress_tab3, i, total)
# Always dispatch final 100% state after loop
self.root.after(0, self.update_progress_tab3, total, total)
```

### 5c. FieldTypeAuditDialog Mousewheel
**Problem**: Mousewheel bound to ~250 individual widgets instead of once on the canvas.

**Solution**: Bind once on the canvas using the same `<Enter>`/`<Leave>` scoping pattern that `ScrollableFrame` already uses.

---

## 6. Dialog & Zoom Polish (MEDIUM)

### 6a. Zoom Debouncing
Zoom button clicks already route through `PreviewRenderer.request_preview()` (Section 1), which debounces. No additional work needed — the extraction solves this.

### 6b. Dialog Geometry
**Problem**: `update_idletasks()` in dialog `__init__` flushes the AppKit layout queue.

**Solution**: Replace with `self.after(10, self._position_and_show)` — defer geometry calculation until after the window is fully constructed. This avoids flushing the event queue mid-construction while still getting accurate `winfo_reqwidth()` values.

**Timer ordering**: The existing dialogs already defer `grab_set` to `self.after(50, _grab_and_focus)`. The geometry deferral (10ms) must fire before the grab (50ms). Consolidate both into `_position_and_show()` which does: calculate geometry → `deiconify()` → `grab_set()` → `focus_set()`. Remove the separate `_grab_and_focus` timer.

---

## Files Changed

| File | Change |
|------|--------|
| `preview_renderer.py` | **NEW** — PreviewRenderer class (threading, debounce, caching) |
| `pdf_generator.py` | Integrate PreviewRenderer; batch treeview updates; Tab 2 in-place updates; ScrollableFrame debounce; dialog geometry deferral; progress throttling |
| `theme.py` | Throttle treeview hover `<Motion>` handler |
| `visual_preview.py` | No changes (remains low-level engine) |

## Files NOT Changed
- `models.py` — pure data, no UI
- `pdf_analyzer.py` — runs on user trigger, no performance issue
- `combed_filler.py` — PDF writing only, no UI
- `markdown_renderer.py` — runs once at startup, cached
- `theme.py` — only the hover binding changes

## Testing Strategy
- Existing test suite must pass unchanged (no behavioral changes, only performance)
- Manual verification on macOS: field selection, tab switching, zoom, select all, data load
- Key metric: field selection should feel instant (<50ms perceived latency)

## Risk Assessment
- **PreviewRenderer threading**: Low risk — only PIL operations run off-thread (no PyMuPDF access). Stale-result guard via monotonic `_request_id` counter. Follows same `root.after()` callback pattern as existing `generate_pdfs_worker`.
- **Treeview batch updates**: Low risk — visual-only change, selection state logic unchanged
- **Tab 2 in-place**: Medium risk — must handle edge cases where field names/count change between refreshes. Condition: same count AND same field names = in-place update; otherwise full rebuild.
- **Configure debounce**: Very low risk — `after_idle()` is the standard tkinter pattern for this
- **PreviewRenderer lifecycle**: Must call `shutdown()` before closing `fitz.Document` in `_close_preview_generator()`. Daemon thread + stale-result guard ensures no crash on exit.
