"""Asynchronous client for the Viessmann Climate Solutions API."""

from __future__ import annotations

import json
from collections.abc import Mapping
from http import HTTPStatus
from typing import Any, Protocol

from aiohttp import ClientError, ClientResponse

from .const import API_BASE_URL, FEATURE_PUMP, FEATURE_SCHEDULE
from .models import CirculationData, Schedule, Target


class OAuthSession(Protocol):
    """Subset of Home Assistant's OAuth2Session used by the client."""

    async def async_request(
        self, method: str, url: str, **kwargs: Any
    ) -> ClientResponse:
        """Perform an authenticated HTTP request."""


class ViessmannApiError(Exception):
    """Base Viessmann API error."""


class ViessmannApiAuthenticationError(ViessmannApiError):
    """Viessmann rejected the access token."""


class ViessmannApiRateLimitError(ViessmannApiError):
    """Viessmann rate limit was reached."""


class ViessmannApiNotSupportedError(ViessmannApiError):
    """The required circulation feature is unavailable."""


class ViessmannApiInvalidDataError(ViessmannApiError):
    """Viessmann returned malformed data."""


class ViessmannApiClient:
    """Client for circulation-related Viessmann endpoints."""

    def __init__(self, session: OAuthSession) -> None:
        """Initialize the client."""
        self._session = session

    async def async_get_installations(self) -> list[dict[str, Any]]:
        """Return installations available to the authenticated account."""
        return await self._get_list(f"{API_BASE_URL}/equipment/installations")

    async def async_get_gateways(
        self, installation_id: str, *, allow_unassociated: bool = False
    ) -> list[dict[str, Any]]:
        """Return gateways associated with an installation."""
        gateways = await self._get_list(f"{API_BASE_URL}/equipment/gateways")
        associated = [
            gateway
            for gateway in gateways
            if "installationId" in gateway or "installation_id" in gateway
        ]
        if not associated:
            if allow_unassociated:
                return gateways
            raise ViessmannApiInvalidDataError(
                "Gateways cannot be associated with one of multiple installations"
            )
        matching = [
            gateway
            for gateway in associated
            if str(gateway.get("installationId", gateway.get("installation_id", "")))
            == installation_id
        ]
        return matching

    async def async_get_heating_devices(
        self, installation_id: str, gateway_serial: str
    ) -> list[dict[str, Any]]:
        """Return heating devices behind a gateway."""
        devices = await self._get_list(
            f"{API_BASE_URL}/equipment/installations/{installation_id}"
            f"/gateways/{gateway_serial}/devices"
        )
        return [device for device in devices if device.get("deviceType") == "heating"]

    async def async_validate_target(self, target: Target) -> None:
        """Ensure the circulation schedule can be written for a target."""
        feature = await self.async_get_feature(target, FEATURE_SCHEDULE)
        commands = feature.get("commands")
        command = commands.get("setSchedule") if isinstance(commands, dict) else None
        if (
            feature.get("isEnabled") is not True
            or feature.get("isReady") is not True
            or not isinstance(command, dict)
            or command.get("isExecutable") is not True
        ):
            raise ViessmannApiNotSupportedError(
                "The DHW circulation schedule is not enabled, ready, and writable"
            )

    async def async_get_feature(self, target: Target, feature: str) -> dict[str, Any]:
        """Read one feature."""
        data = await self._request_json("GET", self._feature_url(target, feature))
        if not isinstance(data, dict):
            raise ViessmannApiInvalidDataError("Feature response is not an object")
        feature_data = data.get("data", data)
        if not isinstance(feature_data, dict):
            raise ViessmannApiInvalidDataError("Feature data is not an object")
        return feature_data

    async def async_get_circulation_data(self, target: Target) -> CirculationData:
        """Read schedule and physical pump state."""
        from datetime import UTC, datetime

        try:
            schedule_feature = await self.async_get_feature(target, FEATURE_SCHEDULE)
        except ViessmannApiAuthenticationError:
            raise
        except ViessmannApiError:
            schedule_feature = {}

        try:
            pump_feature = await self.async_get_feature(target, FEATURE_PUMP)
        except ViessmannApiAuthenticationError:
            raise
        except ViessmannApiError:
            pump_feature = {}

        properties = schedule_feature.get("properties")
        entries = properties.get("entries") if isinstance(properties, dict) else None
        schedule = entries.get("value") if isinstance(entries, dict) else None
        if not isinstance(schedule, dict):
            schedule = None

        active = properties.get("active") if isinstance(properties, dict) else None
        schedule_active = active.get("value") if isinstance(active, dict) else None
        if not isinstance(schedule_active, bool):
            schedule_active = None

        pump_properties = pump_feature.get("properties")
        status = (
            pump_properties.get("status") if isinstance(pump_properties, dict) else None
        )
        pump_status = status.get("value") if isinstance(status, dict) else None
        if not isinstance(pump_status, str):
            pump_status = None

        return CirculationData(
            schedule=schedule,
            schedule_active=schedule_active,
            pump_status=pump_status,
            schedule_feature_enabled=schedule_feature.get("isEnabled") is True,
            schedule_feature_ready=schedule_feature.get("isReady") is True,
            pump_feature_enabled=pump_feature.get("isEnabled") is True,
            pump_feature_ready=pump_feature.get("isReady") is True,
            last_successful_update=datetime.now(UTC),
        )

    async def async_set_schedule(self, target: Target, schedule: Schedule) -> None:
        """Replace the complete circulation schedule."""
        await self._request_json(
            "POST",
            f"{self._feature_url(target, FEATURE_SCHEDULE)}/commands/setSchedule",
            json={"newSchedule": schedule},
            allow_empty=True,
        )

    async def _get_list(self, url: str) -> list[dict[str, Any]]:
        data = await self._request_json("GET", url)
        items = data.get("data") if isinstance(data, dict) else None
        if not isinstance(items, list) or not all(
            isinstance(item, dict) for item in items
        ):
            raise ViessmannApiInvalidDataError("Expected a data array")
        return items

    async def _request_json(
        self,
        method: str,
        url: str,
        *,
        allow_empty: bool = False,
        retry_auth: bool = True,
        **kwargs: Any,
    ) -> Any:
        headers = {"Accept": "application/json"}
        if "json" in kwargs:
            headers["Content-Type"] = "application/json"
        kwargs["headers"] = headers

        try:
            response = await self._session.async_request(method, url, **kwargs)
            async with response:
                if response.status in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
                    raise ViessmannApiAuthenticationError("Authentication failed")
                if response.status == HTTPStatus.TOO_MANY_REQUESTS:
                    raise ViessmannApiRateLimitError("API rate limit reached")
                if response.status == HTTPStatus.NOT_FOUND:
                    raise ViessmannApiNotSupportedError("API resource not found")
                if response.status >= HTTPStatus.BAD_REQUEST:
                    raise ViessmannApiError(
                        f"Viessmann API returned HTTP {response.status}"
                    )
                if response.status == HTTPStatus.NO_CONTENT:
                    return {} if allow_empty else None
                body = await response.text()
                if not body and allow_empty:
                    return {}
                try:
                    payload = json.loads(body)
                except json.JSONDecodeError as err:
                    raise ViessmannApiInvalidDataError(
                        "API response is not JSON"
                    ) from err
                self._raise_payload_error(payload)
                return payload
        except ViessmannApiAuthenticationError:
            force_refresh = getattr(self._session, "async_force_refresh", None)
            if retry_auth and force_refresh is not None:
                await force_refresh()
                return await self._request_json(
                    method,
                    url,
                    allow_empty=allow_empty,
                    retry_auth=False,
                    **kwargs,
                )
            raise
        except ViessmannApiError:
            raise
        except (ClientError, TimeoutError) as err:
            raise ViessmannApiError(str(err)) from err

    @staticmethod
    def _feature_url(target: Target, feature: str) -> str:
        return (
            f"{API_BASE_URL}/features/installations/{target.installation_id}"
            f"/gateways/{target.gateway_serial}/devices/{target.device_id}"
            f"/features/{feature}"
        )

    @staticmethod
    def _raise_payload_error(payload: Any) -> None:
        """Handle Viessmann errors occasionally returned with HTTP 200."""
        if not isinstance(payload, dict):
            return
        if payload.get("error") == "EXPIRED TOKEN":
            raise ViessmannApiAuthenticationError("Authentication failed")

        status = payload.get("statusCode")
        try:
            status_code = int(status)
        except (TypeError, ValueError):
            status_code = 0

        extended = payload.get("extendedPayload")
        if status_code < HTTPStatus.BAD_REQUEST and isinstance(extended, dict):
            try:
                status_code = int(extended.get("code", 0))
            except (TypeError, ValueError):
                status_code = 0

        if status_code in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
            raise ViessmannApiAuthenticationError("Authentication failed")
        if status_code == HTTPStatus.TOO_MANY_REQUESTS:
            raise ViessmannApiRateLimitError("API rate limit reached")
        if status_code == HTTPStatus.NOT_FOUND:
            raise ViessmannApiNotSupportedError("API resource not found")
        if status_code >= HTTPStatus.BAD_REQUEST:
            raise ViessmannApiError(f"Viessmann API returned status {status_code}")


def item_id(item: Mapping[str, Any], *keys: str) -> str | None:
    """Return the first non-empty identifier in an API item."""
    for key in keys:
        value = item.get(key)
        if value is not None and str(value):
            return str(value)
    return None
