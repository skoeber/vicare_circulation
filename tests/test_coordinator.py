"""Regression tests for delayed Viessmann schedule consistency."""

import asyncio
from collections import deque
from copy import deepcopy
from datetime import UTC, datetime

from custom_components.vicare_circulation.api import ViessmannApiError
from custom_components.vicare_circulation.const import (
    PRESET_ALL_DAY,
    PRESET_OFF,
    PRESET_STANDARD,
    PRESETS,
)
from custom_components.vicare_circulation.coordinator import (
    ViCareCirculationCoordinator,
)
from custom_components.vicare_circulation.models import CirculationData, Target


def circulation_data(schedule):
    """Build coordinator data around a schedule fixture."""
    return CirculationData(
        schedule=deepcopy(schedule),
        schedule_active=True,
        pump_status="off",
        schedule_feature_enabled=True,
        schedule_feature_ready=True,
        pump_feature_enabled=True,
        pump_feature_ready=True,
        last_successful_update=datetime.now(UTC),
    )


class FakeApi:
    """Queue read results and record writes."""

    def __init__(self, *reads, write_error=None) -> None:
        self.reads = deque(reads)
        self.write_error = write_error
        self.writes = []

    async def async_set_schedule(self, target, schedule) -> None:
        if self.write_error is not None:
            raise self.write_error
        self.writes.append(deepcopy(schedule))

    async def async_get_circulation_data(self, target):
        return self.reads.popleft()


class FakeEntry:
    """Create lifecycle tasks and record reauthentication requests."""

    def __init__(self) -> None:
        self.reauth_requests = 0
        self.unload_callbacks = []

    def async_on_unload(self, callback) -> None:
        self.unload_callbacks.append(callback)

    def async_start_reauth_if_available(self, hass) -> None:
        self.reauth_requests += 1


class FakeHass:
    """Create and track Home Assistant tasks."""

    def __init__(self) -> None:
        self.tasks = []

    def async_create_task(self, coroutine, name):
        task = asyncio.create_task(coroutine, name=name)
        self.tasks.append(task)
        return task


def create_coordinator(
    api: FakeApi,
) -> tuple[ViCareCirculationCoordinator, FakeEntry, FakeHass]:
    """Create a coordinator using lightweight Home Assistant stubs."""
    entry = FakeEntry()
    hass = FakeHass()
    coordinator = ViCareCirculationCoordinator(
        hass, entry, api, Target("installation", "gateway", "device")
    )
    return coordinator, entry, hass


def test_stale_read_is_retried_until_requested_schedule_is_visible(monkeypatch) -> None:
    """The service succeeds when Viessmann initially returns the previous plan."""
    import custom_components.vicare_circulation.coordinator as module

    monkeypatch.setattr(module, "SCHEDULE_VERIFY_DELAYS", (0, 0, 0))
    old_schedule = PRESETS[PRESET_STANDARD]
    requested = PRESETS[PRESET_ALL_DAY]
    api = FakeApi(
        circulation_data(old_schedule),
        circulation_data(old_schedule),
        circulation_data(requested),
    )
    coordinator, _entry, hass = create_coordinator(api)

    confirmed = asyncio.run(coordinator.async_write_schedule(deepcopy(requested)))

    assert confirmed is True
    assert coordinator.data.schedule == requested
    assert api.writes == [requested]
    assert not hass.tasks


def test_unconfirmed_accepted_write_schedules_follow_up_without_error(
    monkeypatch,
) -> None:
    """A successful POST is not reported as failed because reads remain stale."""
    import custom_components.vicare_circulation.coordinator as module

    monkeypatch.setattr(module, "SCHEDULE_VERIFY_DELAYS", (0, 0))
    monkeypatch.setattr(module, "SCHEDULE_FOLLOW_UP_DELAY", 3600)
    old_schedule = PRESETS[PRESET_STANDARD]
    requested = PRESETS[PRESET_OFF]
    api = FakeApi(circulation_data(old_schedule), circulation_data(old_schedule))
    coordinator, entry, hass = create_coordinator(api)

    async def exercise() -> None:
        confirmed = await coordinator.async_write_schedule(deepcopy(requested))
        assert confirmed is False
        assert coordinator.data.schedule == old_schedule
        assert len(hass.tasks) == 1
        entry.unload_callbacks[0]()
        await asyncio.gather(*hass.tasks, return_exceptions=True)

    asyncio.run(exercise())


def test_follow_up_refresh_publishes_eventually_visible_schedule(monkeypatch) -> None:
    """The delayed refresh updates entities when Viessmann finishes publishing."""
    import custom_components.vicare_circulation.coordinator as module

    monkeypatch.setattr(module, "SCHEDULE_VERIFY_DELAYS", (0, 0))
    monkeypatch.setattr(module, "SCHEDULE_FOLLOW_UP_DELAY", 0)
    old_schedule = PRESETS[PRESET_STANDARD]
    requested = PRESETS[PRESET_OFF]
    api = FakeApi(
        circulation_data(old_schedule),
        circulation_data(old_schedule),
        circulation_data(requested),
    )
    coordinator, _entry, hass = create_coordinator(api)

    async def exercise() -> None:
        confirmed = await coordinator.async_write_schedule(deepcopy(requested))
        assert confirmed is False
        await asyncio.gather(*hass.tasks)
        assert coordinator.data.schedule == requested
        assert coordinator.refresh_requests == 1
        assert coordinator._pending_schedule is None

    asyncio.run(exercise())


def test_failed_post_remains_a_service_error(monkeypatch) -> None:
    """A genuine command failure is not converted into pending confirmation."""
    import custom_components.vicare_circulation.coordinator as module

    monkeypatch.setattr(module, "SCHEDULE_VERIFY_DELAYS", (0,))
    error = ViessmannApiError("write failed")
    api = FakeApi(write_error=error)
    coordinator, _entry, hass = create_coordinator(api)

    try:
        asyncio.run(coordinator.async_write_schedule(deepcopy(PRESETS[PRESET_OFF])))
    except ViessmannApiError as err:
        assert err is error
    else:
        raise AssertionError("Expected write error")

    assert not api.reads
    assert not hass.tasks
