# field_values.py
"""Pure value->field-type translation for PDF form filling.

Checkboxes and radio buttons only fill when given a PDF name matching their
"on" appearance state (proven: a plain string never ticks a box). Choice
fields must match one of their defined options. These helpers translate a raw
spreadsheet cell into the right value, with no GUI or PDF-library state.
"""
from typing import List, Optional, Tuple
from pypdf.generic import NameObject

# Spreadsheet values that mean "ticked" / "not ticked" (lowercased, stripped).
TRUTHY = {"yes", "y", "true", "t", "1", "x", "✓", "✔", "on", "checked"}
FALSEY = {"no", "n", "false", "f", "0", "", "off", "unchecked", "nan"}


def normalize_button_value(raw, on_states: List[str]) -> Optional[NameObject]:
    """Map a spreadsheet value to a checkbox/radio appearance state.

    Single on-state (checkbox): truthy -> /<state>, falsey -> /Off.
    Multiple on-states (radio): value must match a state (case-insensitive)
        -> /<matched state>.
    Returns None when the value cannot be resolved; the caller should warn and
    leave the field untouched rather than guess.
    """
    s = str(raw).strip().lower()
    states = on_states or []

    if len(states) <= 1:
        # Checkbox semantics (default on-state "Yes" if none was detected).
        if s in TRUTHY:
            return NameObject("/" + (states[0] if states else "Yes"))
        if s in FALSEY:
            return NameObject("/Off")
        return None

    # Radio semantics: match the chosen option by export value.
    for state in states:
        if s == state.strip().lower():
            return NameObject("/" + state)
    return None


def normalize_choice_value(raw, options: List[str]) -> Tuple[str, bool]:
    """Resolve a dropdown/listbox value against its options.

    Returns (value_to_write, matched). On a case-insensitive/whitespace match
    the canonical option text is returned with matched=True. Otherwise the raw
    string is returned with matched=False so the caller can warn the user that
    the value is not one of the field's allowed options.
    """
    s = str(raw).strip()
    for opt in (options or []):
        if s.lower() == opt.strip().lower():
            return (opt, True)
    return (s, False)
