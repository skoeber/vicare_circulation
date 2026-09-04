"""Tests for the asynchronous Viessmann API client."""

import asyncio
import json
from collections import deque
from copy import deepcopy
from typing import Any

from custom_components.vicare_circulation.api import (
    ViessmannApiAuthenticationError,
    ViessmannApiClient,
    ViessmannApiError,
    ViessmannApiInvalidDataError,
    ViessmannApiNotSupportedError,
    ViessmannApiRateLimitError,
)
from custom_components.vicare_circulation.const import (
    API_BASE_URL,
    PRESET_OFF,
    PRESETS,
)
from custom_components.vicare_circulation.models import Target

TARGET = Target("installation", "gateway", "device", "serial", "model")


class FakeResponse:
    """Minimal aiohttp response double."""

    def __init__(self, status: int, body: Any = None) -> None:
        self.status = status
        if isinstance(body, str):
            self._body = body
        elif body is None:
            self._body = ""
        else:
            self._body = json.dumps(body)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        return None

    async def text(self) -> str:
        return self._body


class FakeSession:
    """Record requests and return queued fake responses."""

    def __init__(self, *responses: FakeResponse) -> None:
        self.responses = deque(responses)
        self.requests: list[tuple[str, str, dict[str, Any]]] = []

    async def async_request(self, method: str, url: str, **kwargs: Any):
        self.requests.append((method, url, kwargs))
        return self.responses.popleft()


class RefreshingFakeSession(FakeSession):
    """Session double exposing the optional forced-refresh hook."""

    def __init__(self, *responses: FakeResponse) -> None:
        super().__init__(*responses)
        self.refreshes = 0

    async def async_force_refresh(self) -> None:
        self.refreshes += 1


def run(coroutine):
    """Run one async client operation."""
    return asyncio.run(coroutine)


def feature(name: str, properties: dict, **extra: Any) -> dict:
    """Build a feature response fixture."""
    return {
        "data": {
            "feature": name,
            "isEnabled": extra.pop("isEnabled", True),
            "isReady": extra.pop("isReady", True),
            "properties": properties,
            "commands": extra.pop("commands", {}),
            **extra,
        }
    }


def test_discovers_installations_gateways_and_heating_devices() -> None:
    """Equipment endpoints are parsed and non-heating devices filtered."""
    session = FakeSession(
        FakeResponse(200, {"data": [{"id": "installation"}]}),
        FakeResponse(
            200,
            {
                "data": [
                    {"serial": "gateway", "installationId": "installation"},
                    {"serial": "other", "installationId": "other-installation"},
                ]
            },
        ),
        FakeResponse(
            200,
            {
                "data": [
                    {"id": "device", "deviceType": "heating"},
                    {"id": "gateway-device", "deviceType": "gateway"},
                ]
            },
        ),
    )
    api = ViessmannApiClient(session)

    assert run(api.async_get_installations()) == [{"id": "installation"}]
    assert run(api.async_get_gateways("installation"))[0]["serial"] == "gateway"
    assert run(api.async_get_heating_devices("installation", "gateway")) == [
        {"id": "device", "deviceType": "heating"}
    ]
    assert session.requests[2][1].endswith(
        "/equipment/installations/installation/gateways/gateway/devices"
    )


def test_does_not_guess_unassociated_gateway_for_multiple_installations() -> None:
    """Unassociated account-wide gateways require an unambiguous account."""
    api = ViessmannApiClient(
        FakeSession(FakeResponse(200, {"data": [{"serial": "gateway"}]}))
    )
    try:
        run(api.async_get_gateways("installation"))
    except ViessmannApiInvalidDataError:
        pass
    else:
        raise AssertionError("Expected ambiguous gateway data to be rejected")

    api = ViessmannApiClient(
        FakeSession(FakeResponse(200, {"data": [{"serial": "gateway"}]}))
    )
    assert run(api.async_get_gateways("installation", allow_unassociated=True)) == [
        {"serial": "gateway"}
    ]


def test_reads_schedule_and_physical_pump_status() -> None:
    """The two independent circulation features become one coordinator payload."""
    schedule = deepcopy(PRESETS[PRESET_OFF])
    session = FakeSession(
        FakeResponse(
            200,
            feature(
                "heating.dhw.pumps.circulation.schedule",
                {
                    "entries": {"type": "Schedule", "value": schedule},
                    "active": {"type": "boolean", "value": True},
                },
            ),
        ),
        FakeResponse(
            200,
            feature(
                "heating.dhw.pumps.circulation",
                {"status": {"type": "string", "value": "off"}},
            ),
        ),
    )
    data = run(ViessmannApiClient(session).async_get_circulation_data(TARGET))
    assert data.schedule == schedule
    assert data.schedule_active is True
    assert data.pump_status == "off"
    assert data.schedule_feature_enabled is True
    assert data.pump_feature_ready is True


def test_schedule_remains_available_when_pump_feature_fails() -> None:
    """A pump-only failure does not hide a valid controllable schedule."""
    schedule = deepcopy(PRESETS[PRESET_OFF])
    session = FakeSession(
        FakeResponse(
            200,
            feature(
                "heating.dhw.pumps.circulation.schedule",
                {
                    "entries": {"type": "Schedule", "value": schedule},
                    "active": {"type": "boolean", "value": True},
                },
            ),
        ),
        FakeResponse(503),
    )
    data = run(ViessmannApiClient(session).async_get_circulation_data(TARGET))
    assert data.schedule == schedule
    assert data.schedule_feature_ready is True
    assert data.pump_status is None
    assert data.pump_feature_ready is False


def test_writes_exact_complete_schedule_to_v2_command() -> None:
    """setSchedule receives exactly one newSchedule parameter."""
    session = FakeSession(FakeResponse(204))
    api = ViessmannApiClient(session)
    schedule = deepcopy(PRESETS[PRESET_OFF])
    run(api.async_set_schedule(TARGET, schedule))

    method, url, kwargs = session.requests[0]
    assert method == "POST"
    assert url == (
        f"{API_BASE_URL}/features/installations/installation/gateways/gateway"
        "/devices/device/features/heating.dhw.pumps.circulation.schedule"
        "/commands/setSchedule"
    )
    assert kwargs["json"] == {"newSchedule": schedule}
    assert kwargs["headers"]["Content-Type"] == "application/json"


def test_validates_executable_schedule_feature() -> None:
    """A ready executable setSchedule command is accepted."""
    session = FakeSession(
        FakeResponse(
            200,
            feature(
                "heating.dhw.pumps.circulation.schedule",
                {},
                commands={"setSchedule": {"isExecutable": True}},
            ),
        )
    )
    run(ViessmannApiClient(session).async_validate_target(TARGET))


def test_rejects_non_executable_schedule_feature() -> None:
    """A disabled command cannot create a functional integration."""
    session = FakeSession(
        FakeResponse(
            200,
            feature(
                "heating.dhw.pumps.circulation.schedule",
                {},
                commands={"setSchedule": {"isExecutable": False}},
            ),
        )
    )
    try:
        run(ViessmannApiClient(session).async_validate_target(TARGET))
    except ViessmannApiNotSupportedError:
        pass
    else:
        raise AssertionError("Expected unsupported schedule error")


def test_maps_auth_rate_limit_and_not_found_errors() -> None:
    """Important HTTP statuses receive actionable typed errors."""
    cases = (
        (401, ViessmannApiAuthenticationError),
        (403, ViessmannApiAuthenticationError),
        (429, ViessmannApiRateLimitError),
        (404, ViessmannApiNotSupportedError),
    )
    for status, error in cases:
        api = ViessmannApiClient(FakeSession(FakeResponse(status, {"error": "x"})))
        try:
            run(api.async_get_feature(TARGET, "feature"))
        except error:
            pass
        else:
            raise AssertionError(f"Expected {error.__name__} for HTTP {status}")


def test_retries_once_after_forced_token_refresh() -> None:
    """An HTTP 401 refreshes the token and retries exactly once."""
    session = RefreshingFakeSession(
        FakeResponse(401),
        FakeResponse(200, feature("feature", {})),
    )
    result = run(ViessmannApiClient(session).async_get_feature(TARGET, "feature"))
    assert result["feature"] == "feature"
    assert session.refreshes == 1
    assert len(session.requests) == 2


def test_server_error_does_not_expose_response_body() -> None:
    """Potentially identifying cloud error details never enter logs via exceptions."""
    api = ViessmannApiClient(
        FakeSession(FakeResponse(500, "installation installation-secret failed"))
    )
    try:
        run(api.async_get_feature(TARGET, "feature"))
    except ViessmannApiError as err:
        assert str(err) == "Viessmann API returned HTTP 500"
        assert "installation-secret" not in str(err)
    else:
        raise AssertionError("Expected server error")


def test_maps_errors_embedded_in_successful_http_response() -> None:
    """Viessmann error envelopes returned with HTTP 200 are not accepted as data."""
    cases = (
        ({"error": "EXPIRED TOKEN"}, ViessmannApiAuthenticationError),
        ({"statusCode": 429}, ViessmannApiRateLimitError),
        ({"extendedPayload": {"code": "503"}}, ViessmannApiError),
    )
    for payload, error in cases:
        api = ViessmannApiClient(FakeSession(FakeResponse(200, payload)))
        try:
            run(api.async_get_feature(TARGET, "feature"))
        except error:
            pass
        else:
            raise AssertionError(f"Expected {error.__name__} for {payload}")


def test_rejects_invalid_json_and_missing_data_arrays() -> None:
    """Malformed cloud responses never become valid entity data."""
    api = ViessmannApiClient(FakeSession(FakeResponse(200, "not-json")))
    try:
        run(api.async_get_feature(TARGET, "feature"))
    except ViessmannApiInvalidDataError:
        pass
    else:
        raise AssertionError("Expected invalid JSON error")

    api = ViessmannApiClient(FakeSession(FakeResponse(200, {"data": {}})))
    try:
        run(api.async_get_installations())
    except ViessmannApiInvalidDataError:
        pass
    else:
        raise AssertionError("Expected invalid data array error")
