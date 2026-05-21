"""Tests for GET /health."""

from httpx import AsyncClient


async def test_health_returns_200(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200


async def test_health_body_fields(client: AsyncClient) -> None:
    response = await client.get("/health")
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert "env" in body
    assert body["db"] == "reachable"
    assert body["storage"] == "reachable"


async def test_health_no_auth_required(client: AsyncClient) -> None:
    """Health endpoint must not require X-Device-Id."""
    response = await client.get("/health")
    assert response.status_code == 200
