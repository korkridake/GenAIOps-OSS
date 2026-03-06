"""
LiteLLM cost-tracking utilities.

Queries the LiteLLM proxy's spend and metrics endpoints so the application
can surface per-user, per-key, and per-model cost information.
"""

from __future__ import annotations

import os
from typing import Any

import httpx


class CostTracker:
    """Query LiteLLM's spend and model-metrics endpoints.

    Args:
        base_url: LiteLLM proxy URL (no trailing slash).
        api_key:  Master key or admin virtual key.
        timeout:  HTTP request timeout in seconds.
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float = 15.0,
    ) -> None:
        self._base_url = (base_url or os.getenv("APP_LITELLM_BASE_URL", "http://localhost:4000")).rstrip("/")
        self._api_key = api_key or os.getenv("LITELLM_MASTER_KEY", "")
        self._timeout = timeout

    # ── internal helpers ──────────────────────────────────────────────────────

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        """Issue a GET request to the LiteLLM proxy and return parsed JSON."""
        url = f"{self._base_url}{path}"
        headers = {"Authorization": f"Bearer {self._api_key}"}
        try:
            resp = httpx.get(url, headers=headers, params=params or {}, timeout=self._timeout)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            print(f"[cost_tracker] HTTP {exc.response.status_code} from {url}")
            return None
        except httpx.RequestError as exc:
            print(f"[cost_tracker] Request error: {exc}")
            return None

    # ── public API ────────────────────────────────────────────────────────────

    def get_spend_summary(self) -> dict[str, Any] | None:
        """Return the global spend summary from ``/spend/logs``."""
        return self._get("/spend/logs")

    def get_model_metrics(self) -> list[dict[str, Any]]:
        """Return per-model usage metrics from ``/model/metrics``."""
        result = self._get("/model/metrics")
        if result is None:
            return []
        # The endpoint returns either a list or ``{"data": [...]}``
        if isinstance(result, list):
            return result
        return result.get("data", [])

    def get_key_spend(self, virtual_key: str) -> dict[str, Any] | None:
        """Return spend detail for a specific virtual key."""
        return self._get("/key/info", params={"key": virtual_key})

    def get_team_spend(self, team_id: str) -> dict[str, Any] | None:
        """Return spend detail for a team."""
        return self._get("/team/info", params={"team_id": team_id})

    def get_user_spend(self, user_id: str) -> dict[str, Any] | None:
        """Return spend detail for a user."""
        return self._get("/user/info", params={"user_id": user_id})
