"""Constants for the ViCare Circulation integration."""

from datetime import timedelta
from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "vicare_circulation"
NAME: Final = "ViCare Circulation"

PLATFORMS: Final = [Platform.SELECT, Platform.SENSOR, Platform.BINARY_SENSOR]
UPDATE_INTERVAL: Final = timedelta(minutes=5)
SCHEDULE_VERIFY_DELAYS: Final = (0, 1, 2, 4)
SCHEDULE_FOLLOW_UP_DELAY: Final = 15

API_BASE_URL: Final = "https://api.viessmann-climatesolutions.com/iot/v2"
AUTHORIZE_URL: Final = "https://iam.viessmann-climatesolutions.com/idp/v3/authorize"
TOKEN_URL: Final = "https://iam.viessmann-climatesolutions.com/idp/v3/token"
OAUTH_SCOPES: Final = ["IoT", "User", "offline_access"]

CONF_INSTALLATION_ID: Final = "installation_id"
CONF_GATEWAY_SERIAL: Final = "gateway_serial"
CONF_DEVICE_ID: Final = "device_id"
CONF_DEVICE_SERIAL: Final = "device_serial"
CONF_DEVICE_MODEL: Final = "device_model"

FEATURE_PUMP: Final = "heating.dhw.pumps.circulation"
FEATURE_SCHEDULE: Final = "heating.dhw.pumps.circulation.schedule"

DAYS: Final = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")

PRESET_STANDARD: Final = "Standard"
PRESET_ALL_DAY: Final = "Ganztägig"
PRESET_OFF: Final = "Aus"
PRESET_OPTIONS: Final = [PRESET_STANDARD, PRESET_ALL_DAY, PRESET_OFF]

_STANDARD_WEEKDAY = [{"start": "17:00", "end": "22:00", "mode": "on", "position": 0}]
_STANDARD_WEEKEND = [{"start": "07:30", "end": "23:00", "mode": "on", "position": 0}]
_ALL_DAY = [{"start": "00:00", "end": "24:00", "mode": "on", "position": 0}]

PRESETS: Final = {
    PRESET_STANDARD: {
        "mon": _STANDARD_WEEKDAY,
        "tue": _STANDARD_WEEKDAY,
        "wed": _STANDARD_WEEKDAY,
        "thu": _STANDARD_WEEKDAY,
        "fri": _STANDARD_WEEKDAY,
        "sat": _STANDARD_WEEKEND,
        "sun": _STANDARD_WEEKEND,
    },
    PRESET_ALL_DAY: {day: _ALL_DAY for day in DAYS},
    PRESET_OFF: {day: [] for day in DAYS},
}

SCHEDULE_STANDARD: Final = "standard"
SCHEDULE_ALL_DAY: Final = "all_day"
SCHEDULE_OFF: Final = "off"
SCHEDULE_CUSTOM: Final = "custom"
SCHEDULE_UNKNOWN: Final = "unknown"

SCHEDULE_TO_PRESET: Final = {
    SCHEDULE_STANDARD: PRESET_STANDARD,
    SCHEDULE_ALL_DAY: PRESET_ALL_DAY,
    SCHEDULE_OFF: PRESET_OFF,
}

PRESET_TO_SCHEDULE: Final = {value: key for key, value in SCHEDULE_TO_PRESET.items()}
