# Automatic Update Check on Startup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the app automatically check for a newer release once per day on startup and surface it as a non-intrusive inline banner, so teachers actually receive updates instead of having to find and click the manual "Check for Updates" button.

**Architecture:** Reuse the existing, already-correct `check_for_update()` module function and daemon-thread + `root.after()` pattern. Add a once-per-day throttle backed by a new `AppSettings.last_update_check` field (a pure, unit-tested decision function decides whether a check is due). On startup, after the window paints, run the check in the background; if — and only if — a newer version exists, reveal a dismissible banner in the header with a Download button. Up-to-date and error results are silent. No modal pop-ups (macOS freeze rule).

**Tech Stack:** Python 3.10+, tkinter/ttkbootstrap, pytest. No new dependencies.

---

## Why this is needed

The update mechanism is correct and CI bakes the version properly, but the check only runs when the user clicks "Check for Updates" on the About tab (Tab 4) — a tab teachers rarely open. In practice the install base never learns an update exists, so shipped improvements don't reach users. This plan converts the working-but-dormant feature into an automatic one.

## Design constraints (load-bearing — do not violate)

- **No modal pop-ups on the startup path.** Per `CLAUDE.md`, `tkinter.messagebox.*` can open behind the main window on macOS and silently freeze the app. The startup result MUST be shown inline (a banner), never via `messagebox`. This is guarded by a test.
- **Silent unless actionable.** Up-to-date and network-error results must not interrupt the user at startup — only an available update shows UI.
- **Don't block startup.** The check runs on a daemon thread, scheduled via `root.after` so the window paints first.
- **Don't nag.** At most one check per calendar day, persisted across launches; the attempt date is recorded *before* the network call so an offline launch doesn't retry every time.
- **Source/dev runs skip the check** (no installed version to update) — consistent with `check_for_update()` already short-circuiting non-`v` versions.

## File Structure

- **Modify `models.py`** — add `last_update_check: str = ""` to `AppSettings`. Backward-compatible (the existing `from_json` key-filtering already drops/defaults unknown keys).
- **Modify `pdf_generator.py`** — add a pure module-level `_should_check_for_update(last, today)` helper; add the header banner widget to `setup_ui`; add `_maybe_auto_check_update()` and `_show_startup_update_result()` methods; schedule the check at the end of `__init__`.
- **Create `tests/test_auto_update.py`** — unit tests for the settings field and the throttle decision, plus a CI-safe structural test asserting the startup path is non-modal and threaded.

The manual update button, `check_for_update()`, `_run_update_check`, `_show_update_result`, and `_open_update_url` are reused unchanged.

---

## Task 1: Persist the last-check date in settings

**Files:**
- Modify: `models.py` (the `AppSettings` dataclass, around lines 144-152)
- Test: `tests/test_auto_update.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_auto_update.py
from models import AppSettings


def test_appsettings_has_last_update_check_default():
    s = AppSettings(templates_directory="/tmp/x")
    assert s.last_update_check == ""


def test_appsettings_roundtrips_last_update_check():
    s = AppSettings(templates_directory="/tmp/x", last_update_check="2026-06-20")
    restored = AppSettings.from_json(s.to_json())
    assert restored.last_update_check == "2026-06-20"


def test_appsettings_loads_old_json_without_last_update_check():
    # Settings files written before this field existed must still load.
    old = '{"templates_directory": "/tmp/x", "school_name": "WHS"}'
    s = AppSettings.from_json(old)
    assert s.last_update_check == ""
    assert s.school_name == "WHS"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/python -m pytest tests/test_auto_update.py -v`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'last_update_check'`

- [ ] **Step 3: Add the field**

In `models.py`, add the field to `AppSettings` after `school_year` (line 152):

```python
    school_name: str = ""
    school_year: str = ""
    last_update_check: str = ""  # ISO date (YYYY-MM-DD) of last auto update check
```

No `to_json`/`from_json` changes are needed: `AppSettings.to_json` uses `asdict(self)` (emits all fields automatically) and `from_json` already filters to valid dataclass fields with defaults, so old files without the key load fine.

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/bin/python -m pytest tests/test_auto_update.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Run the full suite**

Run: `venv/bin/python -m pytest tests/ -q`
Expected: all pass (existing total + 3 new).

- [ ] **Step 6: Commit**

```bash
git add models.py tests/test_auto_update.py
git commit -m "feat: persist last_update_check date in AppSettings"
```

---

## Task 2: Pure "is a check due today?" helper

**Files:**
- Modify: `pdf_generator.py` (add a module-level function near the other module helpers, e.g. just below `check_for_update`, around line 144)
- Test: `tests/test_auto_update.py`

- [ ] **Step 1: Write the failing tests (APPEND to tests/test_auto_update.py)**

Add near the top of the file:
```python
from pdf_generator import _should_check_for_update
```

Append:
```python
def test_check_due_when_never_checked():
    assert _should_check_for_update("", "2026-06-20") is True


def test_check_not_due_when_already_checked_today():
    assert _should_check_for_update("2026-06-20", "2026-06-20") is False


def test_check_due_when_last_check_was_a_previous_day():
    assert _should_check_for_update("2026-06-19", "2026-06-20") is True


def test_check_due_when_stored_value_is_malformed():
    # A corrupt stored value should not silently disable checking forever.
    assert _should_check_for_update("garbage", "2026-06-20") is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/bin/python -m pytest tests/test_auto_update.py -k "due or checked" -v`
Expected: FAIL — `ImportError: cannot import name '_should_check_for_update'`

- [ ] **Step 3: Implement the helper**

In `pdf_generator.py`, add this module-level function directly after the `check_for_update` function (it ends around line 143, before `def _resolve_data_dir`):

```python
def _should_check_for_update(last_check_iso: str, today_iso: str) -> bool:
    """Return True if an automatic update check is due today.

    Checks at most once per calendar day. An empty value (never checked) or a
    malformed stored value is treated as due, rather than silently disabling
    checks forever. ``today_iso`` is the caller's current date as YYYY-MM-DD.
    """
    return (last_check_iso or "").strip() != today_iso
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/bin/python -m pytest tests/test_auto_update.py -k "due or checked" -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Run the full suite**

Run: `venv/bin/python -m pytest tests/ -q`
Expected: all pass (+4).

- [ ] **Step 6: Commit**

```bash
git add pdf_generator.py tests/test_auto_update.py
git commit -m "feat: add once-per-day update-check throttle helper"
```

---

## Task 3: Startup auto-check + non-modal banner

**Files:**
- Modify: `pdf_generator.py` — `setup_ui` (header area, around lines 1066-1069), `__init__` (after `self.setup_ui()`, line 891), and two new methods near the existing `_open_update_url` (around line 1391)
- Test: `tests/test_auto_update.py`

- [ ] **Step 1: Write the failing structural test (APPEND to tests/test_auto_update.py)**

This test is CI-safe (no tkinter instantiation — it inspects source, mirroring `tests/test_performance.py`). It enforces the non-modal + threaded design.

Add near the top of the file:
```python
import inspect
from pdf_generator import BulkPDFGenerator
```

Append:
```python
def test_startup_update_path_is_nonmodal():
    # A startup check must never use a modal pop-up (macOS freeze risk).
    src = (inspect.getsource(BulkPDFGenerator._maybe_auto_check_update)
           + inspect.getsource(BulkPDFGenerator._show_startup_update_result))
    assert "messagebox" not in src


def test_startup_update_check_is_backgrounded():
    src = inspect.getsource(BulkPDFGenerator._maybe_auto_check_update)
    assert "daemon=True" in src        # runs off the UI thread
    assert "root.after" in src         # result dispatched back to UI thread


def test_startup_update_respects_daily_throttle():
    src = inspect.getsource(BulkPDFGenerator._maybe_auto_check_update)
    assert "_should_check_for_update" in src
    assert "last_update_check" in src
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/bin/python -m pytest tests/test_auto_update.py -k startup -v`
Expected: FAIL — `AttributeError: type object 'BulkPDFGenerator' has no attribute '_maybe_auto_check_update'`

- [ ] **Step 3: Add the banner widget to `setup_ui`**

In `pdf_generator.py`, find the accent-stripe divider line in `setup_ui`:

```python
        # Accent stripe divider
        tk.Frame(main_frame, bg=C['accent'], height=3, autostyle=False).pack(fill=tk.X)

        # ── Content area ──
        content_frame = ttk.Frame(main_frame, padding=str(SPACING['page_padding']))
        content_frame.pack(fill=tk.BOTH, expand=True)
```

Replace that block with (adds a hidden banner and stores `content_frame` on `self` so the banner can be packed above it later):

```python
        # Accent stripe divider
        tk.Frame(main_frame, bg=C['accent'], height=3, autostyle=False).pack(fill=tk.X)

        # ── Update banner (hidden until a startup check finds a newer version) ──
        # Inline and non-modal by design: on macOS a messagebox can open behind
        # the main window and silently freeze the app, so update news is shown
        # here, never via a pop-up. Revealed by _show_startup_update_result.
        self._update_banner = tk.Frame(main_frame, bg=C['bg_surface'], autostyle=False)
        self._update_banner_lbl = tk.Label(
            self._update_banner, text="", font=(ff, 10, 'bold'),
            fg=C['accent'], bg=C['bg_surface'], autostyle=False,
        )
        self._update_banner_lbl.pack(side=tk.LEFT, padx=(16, 8), pady=6)
        ttk.Button(
            self._update_banner, text="Download", bootstyle='success',
            width=12, command=self._open_update_url,
        ).pack(side=tk.LEFT, padx=4, pady=6)
        _dismiss = tk.Label(
            self._update_banner, text="✕", font=(ff, 11),
            fg=C['text_secondary'], bg=C['bg_surface'], cursor="hand2",
            autostyle=False,
        )
        _dismiss.pack(side=tk.RIGHT, padx=12)
        _dismiss.bind("<Button-1>", lambda e: self._update_banner.pack_forget())

        # ── Content area ──
        content_frame = ttk.Frame(main_frame, padding=str(SPACING['page_padding']))
        content_frame.pack(fill=tk.BOTH, expand=True)
        self._content_frame = content_frame  # banner packs above this when shown
```

Note: `self._open_update_url` is defined later in the class and is only invoked on a button click (long after `setup_ui`), so referencing it here is safe. The COLORS keys used (`bg_surface`, `accent`, `text_secondary`) all already exist and are used elsewhere in `setup_ui`.

- [ ] **Step 4: Add the two methods**

In `pdf_generator.py`, add both methods immediately after `_open_update_url` (around line 1391). `datetime` and `threading` are already imported at module top; `check_for_update` and `_should_check_for_update` are module-level functions.

```python
    def _maybe_auto_check_update(self):
        """Once-per-day background update check, surfaced as an inline banner.

        Skips source/dev runs (no installed version). Records the attempt date
        BEFORE the network call so an offline launch doesn't retry every time.
        The result is dispatched to _show_startup_update_result via root.after.
        Never shows a modal pop-up (macOS freeze rule).
        """
        if getattr(self, "_closing", False):
            return
        _commit, _date, current_version = self._build_info
        if not current_version.startswith("v"):
            return  # dev/source run — nothing to update
        today = datetime.now().date().isoformat()
        if not _should_check_for_update(self.settings.last_update_check, today):
            return
        self.settings.last_update_check = today
        try:
            self.settings.save_to_file(self.settings_file)
        except OSError:
            pass  # non-fatal; we'll just retry on the next eligible launch

        def _worker():
            result = check_for_update(current_version)
            self.root.after(0, lambda: self._show_startup_update_result(result))

        threading.Thread(target=_worker, daemon=True).start()

    def _show_startup_update_result(self, result):
        """Reveal the update banner only when a newer version exists.

        Runs on the main thread (dispatched via root.after). Silent on
        up-to-date or error — a startup check must never interrupt the user.
        """
        if getattr(self, "_closing", False):
            return
        if result.get("status") != "update_available":
            return
        self._update_url = result.get("html_url", "")
        latest = result.get("latest", "")
        self._update_banner_lbl.config(
            text=f"A new version ({latest}) is available.")
        self._update_banner.pack(fill=tk.X, before=self._content_frame)
```

- [ ] **Step 5: Schedule the check in `__init__`**

In `pdf_generator.py`, find `self.setup_ui()` (line 891) in `__init__`. Immediately after it, add:

```python
        self.setup_ui()

        # Non-intrusive once-per-day update check, deferred so the window paints
        # first. Result surfaces as an inline banner (never a modal pop-up).
        self.root.after(2000, self._maybe_auto_check_update)
```

- [ ] **Step 6: Run the structural tests to verify they pass**

Run: `venv/bin/python -m pytest tests/test_auto_update.py -k startup -v`
Expected: PASS (3 tests)

- [ ] **Step 7: Run the full suite**

Run: `venv/bin/python -m pytest tests/ -q`
Expected: all pass (+3). Confirm no regression in existing GUI-structural tests (`test_performance.py`).

- [ ] **Step 8: Manual verification on macOS (no clicking, per project rule)**

Per `CLAUDE.md`'s documented pattern, verify the banner logic live without a real network update:

```bash
venv/bin/python - <<'PY'
import tkinter as tk
from pdf_generator import BulkPDFGenerator
root = tk.Tk(); root.withdraw()
app = BulkPDFGenerator(root)
# Simulate an available update and confirm the banner becomes visible.
app._show_startup_update_result({"status": "update_available",
                                 "latest": "v9.9", "html_url": "https://example/x"})
print("banner manager:", app._update_banner.winfo_manager())   # expect 'pack'
print("banner text:", app._update_banner_lbl.cget("text"))
# Simulate up-to-date and confirm it stays hidden after a fresh pack_forget.
app._update_banner.pack_forget()
app._show_startup_update_result({"status": "up_to_date", "latest": "v9.9"})
print("after up_to_date manager:", app._update_banner.winfo_manager())  # expect ''
root.destroy()
PY
```

Expected: banner manager `pack` and text `A new version (v9.9) is available.` after the update result; manager empty (`''`) after the up-to-date result. Then run the real app (`venv/bin/python pdf_generator.py`) once and confirm it launches normally and does not freeze. (A genuine end-to-end update banner requires the installed version to be older than the latest GitHub release; the simulation above is the reliable local check.)

- [ ] **Step 9: Commit**

```bash
git add pdf_generator.py tests/test_auto_update.py
git commit -m "feat: automatic once-per-day update check with non-modal startup banner"
```

---

## Self-Review

**1. Spec coverage:**
- Once-per-day throttle → Tasks 1 (storage) + 2 (decision) + 3 (use). ✅
- Background, non-blocking, dispatched to UI thread → Task 3 (`daemon=True` + `root.after`). ✅
- Non-modal inline banner, silent unless actionable → Task 3 (`_show_startup_update_result` only acts on `update_available`; structural test forbids `messagebox`). ✅
- Skip dev/source runs → Task 3 (`current_version.startswith("v")` guard). ✅
- Don't retry on offline launches → Task 3 (date saved before the network call). ✅
- Backward-compatible settings → Task 1 (relies on existing `from_json` filtering; covered by `test_appsettings_loads_old_json_without_last_update_check`). ✅

**2. Placeholder scan:** No TODO/TBD; every code step has complete content. All strings ASCII (the `✕` and `◆`-style escapes match the file's existing convention).

**3. Type consistency:** `_should_check_for_update(last_check_iso, today_iso) -> bool` is defined in Task 2 and called identically in Task 3. `last_update_check` field name matches across `models.py`, the throttle call, and the structural test. `_update_banner`, `_update_banner_lbl`, `_content_frame`, `_update_url` are created in Task 3 Step 3 and used consistently in Steps 4. `_open_update_url` and `check_for_update` are pre-existing and reused unchanged.

---

## Manual verification (post-implementation, before release)

1. **Live macOS banner check** — Task 3 Step 8 (the withdraw-pattern simulation) plus a normal launch with no freeze.
2. **Real update path** — after the next release tag, launch a slightly older installed build and confirm the banner appears once, the Download button opens the Releases page, and the × dismisses it.
3. **Throttle** — launch twice on the same day; confirm only the first launch performs a network check (e.g. by watching `app.log` or temporarily logging in `_maybe_auto_check_update`).
