"""Async API clients for ZeroMOUSE cloud services."""

import logging
import time
from datetime import datetime, timezone

import aiohttp

from .const import (
    COGNITO_CLIENT_ID,
    COGNITO_ENDPOINT,
    GRAPHQL_URL,
    S3_BUCKET,
    S3_REGION,
    SHADOW_API_URL,
    TOKEN_REFRESH_MARGIN,
)

_LOGGER = logging.getLogger(__name__)

EVENT_QUERY = """
query listMbrPtfEventDataWithImages(
  $deviceID: String!,
  $sortDirection: ModelSortDirection,
  $filter: ModelMbrPtfEventDataFilterInput,
  $limit: Int
) {
  listEventbyDeviceChrono(
    deviceID: $deviceID,
    sortDirection: $sortDirection,
    filter: $filter,
    limit: $limit
  ) {
    items {
      eventID
      eventTime
      type
      classification_byNet
      catClusterId
      titleImageIndex
      createdAt
      Images {
        items {
          filePath
        }
      }
    }
  }
}
"""


class ZeromouseAuthError(Exception):
    """Raised when authentication fails (bad or expired refresh token)."""


class ZeromouseApiError(Exception):
    """Raised when an API call fails (network, server error, etc.)."""


class CognitoAuth:
    """Manages Cognito token lifecycle using a captured refresh token."""

    def __init__(self, session: aiohttp.ClientSession, refresh_token: str) -> None:
        self._session = session
        self._refresh_token = refresh_token
        self._id_token: str | None = None
        self._token_expiry: float = 0

    @property
    def id_token(self) -> str | None:
        return self._id_token

    async def async_ensure_valid_token(self) -> None:
        """Refresh the token if it's within TOKEN_REFRESH_MARGIN of expiry."""
        if time.time() < self._token_expiry - TOKEN_REFRESH_MARGIN:
            return
        await self._async_refresh()

    async def _async_refresh(self) -> None:
        """Exchange refresh token for a new IdToken via Cognito."""
        _LOGGER.debug("Refreshing Cognito tokens")
        try:
            async with self._session.post(
                COGNITO_ENDPOINT,
                headers={
                    "Content-Type": "application/x-amz-json-1.1",
                    "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth",
                },
                json={
                    "ClientId": COGNITO_CLIENT_ID,
                    "AuthFlow": "REFRESH_TOKEN_AUTH",
                    "AuthParameters": {
                        "REFRESH_TOKEN": self._refresh_token,
                    },
                },
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise ZeromouseAuthError(
                        f"Cognito auth failed (HTTP {resp.status}): {body[:200]}"
                    )
                data = await resp.json(content_type=None)
        except aiohttp.ClientError as err:
            raise ZeromouseApiError(f"Cognito request failed: {err}") from err

        result = data.get("AuthenticationResult")
        if not result or "IdToken" not in result:
            raise ZeromouseAuthError("Cognito response missing AuthenticationResult")

        self._id_token = result["IdToken"]
        self._token_expiry = time.time() + result.get("ExpiresIn", 3600)
        _LOGGER.debug("Cognito tokens refreshed, valid for %ds", result.get("ExpiresIn", 3600))


class ShadowClient:
    """Fetches device shadow state via the ZeroMOUSE REST API."""

    def __init__(
        self, auth: CognitoAuth, session: aiohttp.ClientSession, device_id: str
    ) -> None:
        self._auth = auth
        self._session = session
        self._device_id = device_id

    async def async_get_shadow(self) -> dict:
        """Fetch the full device shadow. Returns the shadow dict."""
        await self._auth.async_ensure_valid_token()
        try:
            async with self._session.get(
                SHADOW_API_URL,
                params={"deviceID": self._device_id},
                headers={"auth-token": self._auth.id_token},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 401 or resp.status == 403:
                    raise ZeromouseAuthError("Shadow API auth failed (token expired?)")
                if resp.status != 200:
                    body = await resp.text()
                    raise ZeromouseApiError(
                        f"Shadow API error (HTTP {resp.status}): {body[:200]}"
                    )
                return await resp.json(content_type=None)
        except aiohttp.ClientError as err:
            raise ZeromouseApiError(f"Shadow API request failed: {err}") from err


class EventClient:
    """Fetches detection events via the ZeroMOUSE AppSync GraphQL API."""

    def __init__(
        self, auth: CognitoAuth, session: aiohttp.ClientSession, device_id: str
    ) -> None:
        self._auth = auth
        self._session = session
        self._device_id = device_id

    async def async_get_latest_events(self, limit: int = 5) -> list[dict]:
        """Fetch the latest detection events. Returns a list of event dicts."""
        await self._auth.async_ensure_valid_token()
        try:
            async with self._session.post(
                GRAPHQL_URL,
                headers={
                    "Authorization": self._auth.id_token,
                    "Content-Type": "application/json",
                },
                json={
                    "query": EVENT_QUERY,
                    "variables": {
                        "deviceID": self._device_id,
                        "limit": limit,
                        "sortDirection": "DESC",
                        "filter": {
                            "classification_byNet": {"ne": "free"},
                        },
                    },
                },
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 401 or resp.status == 403:
                    raise ZeromouseAuthError("GraphQL auth failed (token expired?)")
                if resp.status != 200:
                    body = await resp.text()
                    raise ZeromouseApiError(
                        f"GraphQL error (HTTP {resp.status}): {body[:200]}"
                    )
                data = await resp.json(content_type=None)
        except aiohttp.ClientError as err:
            raise ZeromouseApiError(f"GraphQL request failed: {err}") from err

        return (
            data.get("data", {})
            .get("listEventbyDeviceChrono", {})
            .get("items", [])
        )

    @staticmethod
    def get_image_url(file_path: str) -> str:
        """Build a public S3 URL from an event image file path."""
        return f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/private/{file_path}"


async def async_validate_credentials(
    session: aiohttp.ClientSession,
    device_id: str,
    refresh_token: str,
) -> dict:
    """Validate credentials by refreshing the token and fetching the shadow.

    Returns the shadow dict on success.
    Raises ZeromouseAuthError or ZeromouseApiError on failure.
    """
    auth = CognitoAuth(session, refresh_token)
    await auth.async_ensure_valid_token()
    client = ShadowClient(auth, session, device_id)
    return await client.async_get_shadow()
