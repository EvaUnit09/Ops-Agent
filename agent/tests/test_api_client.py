import httpx
import pytest

from app.api_client import DomainApiError
from tests.conftest import error_envelope, success_envelope


# api returns 200 with data -> get() returns the data
async def test_success_returns_data(make_client):
    def handler(request):
        return httpx.Response(200, json=success_envelope([{"id": 1, "tag": "LAP-0001"}]))

    client = make_client(handler)
    result = await client.get("/assets/search")
    assert result == [{"id": 1, "tag": "LAP-0001"}]

# api returns 200 with empty data -> get() returns an empty list
async def test_success_returns_empty_list(make_client):
    def handler(request):
        return httpx.Response(200, json=success_envelope([]))

    client = make_client(handler)
    result = await client.get("/assets/search")
    assert result == []

# api returns 404 -> get() raises DomainApiError with kind "not_found";
# the client builds its own message from the requested path rather than
# trusting the upstream envelope's error text.
async def test_not_found_raises_not_found(make_client):
    def handler(request):
        return httpx.Response(404, json=error_envelope("not_found", "asset 999 was not found"))

    client = make_client(handler)
    with pytest.raises(DomainApiError) as exc_info:
        await client.get("/assets/999")
    assert exc_info.value.kind == "not_found"
    assert exc_info.value.message == "/assets/999 was not found"

# transient timeout then a 200 -> get() retries and returns the eventual data
async def test_timeout_then_success_retries_and_returns_data(make_client):
    attempts = 0

    def handler(request):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.ReadTimeout("timeout", request=request)
        return httpx.Response(200, json=success_envelope([{"id": 7}]))

    client = make_client(handler)
    result = await client.get("/assets/search")
    assert result == [{"id": 7}]
    assert attempts == 2

# every attempt times out -> get() raises DomainApiError with kind "upstream_unavailable"
# after exhausting max_retries + 1 total attempts
async def test_repeated_timeout_exhausts_retries(make_client):
    attempts = 0

    def handler(request):
        nonlocal attempts
        attempts += 1
        raise httpx.ConnectError("offline", request=request)

    client = make_client(handler)
    with pytest.raises(DomainApiError) as exc_info:
        await client.get("/assets/search")
    assert exc_info.value.kind == "upstream_unavailable"
    assert attempts == 3

# a 503 is retried like a transport failure, then succeeds
async def test_503_is_retried_then_succeeds(make_client):
    attempts = 0

    def handler(request):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503)
        return httpx.Response(200, json=success_envelope([]))

    client = make_client(handler)
    result = await client.get("/assets/search")
    assert result == []
    assert attempts == 2

# 422 is a validation error, never retried
async def test_422_is_not_retried(make_client):
    attempts = 0

    def handler(request):
        nonlocal attempts
        attempts += 1
        return httpx.Response(422)

    client = make_client(handler)
    with pytest.raises(DomainApiError) as exc_info:
        await client.get("/assets/search")
    assert exc_info.value.kind == "invalid_request"
    assert attempts == 1

# a non-null envelope error is reported generically, without leaking upstream detail
async def test_envelope_error_is_reported_without_leaking_detail(make_client):
    def handler(request):
        return httpx.Response(
            200,
            json={
                "data": None,
                "error": {"code": "INTERNAL", "message": "sensitive detail"},
                "meta": {"count": 0, "limit": None},
            },
        )

    client = make_client(handler)
    with pytest.raises(DomainApiError) as exc_info:
        await client.get("/reported")
    assert exc_info.value.kind == "unexpected_response"
    assert "sensitive detail" not in exc_info.value.message

# a response missing required envelope keys is rejected as malformed
async def test_malformed_envelope_is_rejected(make_client):
    def handler(request):
        return httpx.Response(200, json={"data": []})

    client = make_client(handler)
    with pytest.raises(DomainApiError) as exc_info:
        await client.get("/malformed")
    assert exc_info.value.kind == "unexpected_response"
