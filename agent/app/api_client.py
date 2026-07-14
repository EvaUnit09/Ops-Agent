"""Async HTTP client for the domain API with envelope validation and retry.

Single responsibility: provide DomainApiClient.get(), which makes a GET
request against the domain API, retries exactly once on transport errors and
502/503/504, validates that the response carries the {data, error, meta}
envelope, raises DomainApiError (never the raw upstream detail) on all
failure paths, and returns a deep copy of the envelope's data field —
normalising 404 and null data to the caller-supplied empty sentinel.

Governed by:
  §"Six canonical tool contracts / All tool wrappers share these behaviors"
    in 00-roadmap-and-contracts.md
  §"agent/app/api_client.py" in 02-langgraph-agent.md
"""
