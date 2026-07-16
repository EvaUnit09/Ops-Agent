"""Async HTTP client for the domain API with envelope validation and retry.

Single responsibility: provide DomainApiClient.get(), which makes an async GET
request against the domain API and normalizes every outcome into one of two
things the tool layer can rely on:

  1. the envelope's `data` payload, on success — with a successful empty
     collection normalized to [] and payload fields (including UTC timestamp
     strings) passed through unmodified; or
  2. a raised DomainApiError carrying one of the four canonical kinds —
     `invalid_request` (4xx validation), `not_found` (404),
     `upstream_unavailable` (timeouts, transport failures, and 5xx after
     retries are exhausted), or `unexpected_response` (missing/malformed
     {data, error, meta} envelope) — with a concise message and never the
     raw upstream detail.

Retry policy: only transport failures and 502/503/504 are retried, up to
API_MAX_RETRIES additional attempts (default 2); validation errors and 404s
are never retried. Every request applies API_TIMEOUT_SECONDS via the timeout
already configured on the injected httpx.AsyncClient.

A 404 is an error, not an empty result. The client never fabricates an empty
success after an upstream failure; converting DomainApiError into the
canonical ToolMessage error payload is the tool layer's job, not this
module's.

Governed by:
  §"Six canonical tool contracts / All tool wrappers share these behaviors"
    in 00-roadmap-and-contracts.md
  §"Environment-variable matrix / Agent and checkpointer"
    in 00-roadmap-and-contracts.md
  §"agent/app/api_client.py" in 02-langgraph-agent.md
"""

import asyncio
from typing import Any, Literal

import httpx

ErrorKind = Literal["invalid_request", "not_found", "upstream_unavailable", "unexpected_response"]


class DomainApiError(Exception):
    def __init__(self, kind: ErrorKind, message: str):
        self.kind = kind
        self.message = message
        # store both as attributes, then call super().__init__(message)
        # so the exception still prints normally
        super().__init__(message)


class DomainApiClient:
    _RETRYABLE_STATUSES = frozenset({502, 503, 504})

    def __init__(
        self,
        http: httpx.AsyncClient,
        *,
        max_retries: int = 2,
        retry_delay_seconds: float = 0.1,
    ) -> None:
        self._http = http
        self._max_retries = max_retries
        self._retry_delay = retry_delay_seconds

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        clean = {key: value for key, value in (params or {}).items() if value is not None}
        attempts = self._max_retries + 1
        for attempt in range(attempts):
            is_last_attempt = attempt == attempts - 1
            try:
                response = await self._http.get(path, params=clean)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                if not is_last_attempt:
                    await asyncio.sleep(self._retry_delay)
                    continue
                raise DomainApiError(
                    "upstream_unavailable", "domain API is temporarily unavailable"
                ) from exc

            if response.status_code in self._RETRYABLE_STATUSES and not is_last_attempt:
                await asyncio.sleep(self._retry_delay)
                continue
            if response.status_code == 404:
                raise DomainApiError("not_found", f"{path} was not found")
            if response.status_code == 422:
                raise DomainApiError("invalid_request", "invalid request")
            if response.status_code in self._RETRYABLE_STATUSES or response.status_code == 500:
                raise DomainApiError(
                    "upstream_unavailable", "domain API is temporarily unavailable"
                )
            if response.status_code != 200:
                raise DomainApiError(
                    "unexpected_response", f"unexpected status {response.status_code}"
                )
            try:
                payload = response.json()
            except ValueError as exc:
                raise DomainApiError(
                    "unexpected_response", "domain API returned invalid JSON"
                ) from exc
            if not isinstance(payload, dict) or not {"data", "error", "meta"} <= payload.keys():
                raise DomainApiError(
                    "unexpected_response", "domain API returned a malformed envelope"
                )
            if payload["error"] is not None:
                raise DomainApiError(
                    "unexpected_response", "domain API reported an application error"
                )
            return payload["data"]
