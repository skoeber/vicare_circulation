"""Tests for schedule normalization and preset detection."""

from copy import deepcopy

from custom_components.vicare_circulation.const import (
    PRESET_ALL_DAY,
    PRESET_OFF,
    PRESET_STANDARD,
    PRESETS,
    SCHEDULE_ALL_DAY,
    SCHEDULE_CUSTOM,
    SCHEDULE_OFF,
    SCHEDULE_STANDARD,
    SCHEDULE_UNKNOWN,
)
from custom_components.vicare_circulation.schedule import (
    detect_schedule,
    normalize_schedule,
)


def test_detects_all_presets() -> None:
    """Each fixed schedule is recognized."""
    assert detect_schedule(PRESETS[PRESET_STANDARD]) == SCHEDULE_STANDARD
    assert detect_schedule(PRESETS[PRESET_ALL_DAY]) == SCHEDULE_ALL_DAY
    assert detect_schedule(PRESETS[PRESET_OFF]) == SCHEDULE_OFF


def test_detects_custom_schedule() -> None:
    """A valid schedule not matching a preset is custom."""
    schedule = deepcopy(PRESETS[PRESET_STANDARD])
    schedule["mon"][0]["start"] = "18:00"
    assert detect_schedule(schedule) == SCHEDULE_CUSTOM


def test_invalid_schedule_is_unknown() -> None:
    """Malformed API data is not treated as a custom valid plan."""
    assert detect_schedule(None) == SCHEDULE_UNKNOWN
    assert detect_schedule({"mon": "invalid"}) == SCHEDULE_UNKNOWN
    assert detect_schedule({"mon": [{"start": "17:00"}]}) == SCHEDULE_UNKNOWN


def test_missing_days_normalize_to_empty_lists() -> None:
    """Missing weekdays have the API default of no entries."""
    normalized = normalize_schedule({})
    assert normalized == PRESETS[PRESET_OFF]


def test_key_and_entry_order_do_not_affect_comparison() -> None:
    """Dictionary and API entry ordering are normalized."""
    schedule = deepcopy(PRESETS[PRESET_OFF])
    schedule["mon"] = [
        {"mode": "on", "position": 1, "end": "12:00", "start": "11:00"},
        {"end": "10:00", "start": "09:00", "position": 0, "mode": "on"},
    ]
    normalized = normalize_schedule(schedule)
    assert normalized is not None
    assert normalized["mon"][0]["position"] == 0
    assert list(normalized["mon"][0]) == ["start", "end", "mode", "position"]


def test_vicare_time_values_are_preserved() -> None:
    """07:30 and 24:00 must not be rounded or rewritten."""
    standard = normalize_schedule(PRESETS[PRESET_STANDARD])
    all_day = normalize_schedule(PRESETS[PRESET_ALL_DAY])
    assert standard is not None and standard["sat"][0]["start"] == "07:30"
    assert all_day is not None and all_day["mon"][0]["end"] == "24:00"


def test_additional_entry_metadata_is_ignored() -> None:
    """Metadata added by the API does not prevent preset recognition."""
    schedule = deepcopy(PRESETS[PRESET_STANDARD])
    schedule["mon"][0]["serverMetadata"] = "ignored"
    assert detect_schedule(schedule) == SCHEDULE_STANDARD
