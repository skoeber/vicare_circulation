"""Schedule normalization and preset matching."""

from typing import Any

from .const import (
    DAYS,
    PRESET_TO_SCHEDULE,
    PRESETS,
    SCHEDULE_CUSTOM,
    SCHEDULE_UNKNOWN,
)
from .models import Schedule

_ENTRY_KEYS = ("start", "end", "mode", "position")


def normalize_schedule(value: Any) -> Schedule | None:
    """Return a deterministic schedule containing only supported fields."""
    if not isinstance(value, dict):
        return None

    normalized: Schedule = {}
    for day in DAYS:
        entries = value.get(day, [])
        if not isinstance(entries, list):
            return None

        normalized_entries: list[dict[str, Any]] = []
        for entry in entries:
            if not isinstance(entry, dict) or not all(
                key in entry for key in _ENTRY_KEYS
            ):
                return None
            if not isinstance(entry["start"], str) or not isinstance(entry["end"], str):
                return None
            if not isinstance(entry["mode"], str) or not isinstance(
                entry["position"], int
            ):
                return None
            normalized_entries.append({key: entry[key] for key in _ENTRY_KEYS})

        normalized[day] = sorted(
            normalized_entries,
            key=lambda item: (
                item["position"],
                item["start"],
                item["end"],
                item["mode"],
            ),
        )
    return normalized


def detect_schedule(value: Any) -> str:
    """Map a Viessmann schedule to a known preset or custom/unknown."""
    normalized = normalize_schedule(value)
    if normalized is None:
        return SCHEDULE_UNKNOWN

    for preset_name, preset in PRESETS.items():
        if normalized == normalize_schedule(preset):
            return PRESET_TO_SCHEDULE[preset_name]
    return SCHEDULE_CUSTOM
