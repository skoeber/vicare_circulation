"""Test bootstrap without requiring a complete Home Assistant installation."""

import sys
from enum import StrEnum
from pathlib import Path
from types import ModuleType


class Platform(StrEnum):
    """Minimal platform enum used while importing integration constants."""

    BINARY_SENSOR = "binary_sensor"
    SELECT = "select"
    SENSOR = "sensor"


ROOT = Path(__file__).parents[1]
PACKAGE_PATH = ROOT / "custom_components" / "vicare_circulation"

# Loading a submodule normally executes the integration's __init__.py, which requires
# Home Assistant. Use a namespace package so pure schedule and API tests stay small.
custom_components = ModuleType("custom_components")
custom_components.__path__ = [str(ROOT / "custom_components")]
integration = ModuleType("custom_components.vicare_circulation")
integration.__path__ = [str(PACKAGE_PATH)]
homeassistant = ModuleType("homeassistant")
homeassistant_const = ModuleType("homeassistant.const")
homeassistant_const.Platform = Platform

sys.modules.setdefault("custom_components", custom_components)
sys.modules.setdefault("custom_components.vicare_circulation", integration)
sys.modules.setdefault("homeassistant", homeassistant)
sys.modules.setdefault("homeassistant.const", homeassistant_const)
