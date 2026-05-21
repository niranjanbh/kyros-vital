"""Admin HTTP Basic Auth tests."""
import os

import bcrypt
import pytest
from httpx import AsyncClient

# Set credentials before any app import
os.environ.setdefault("ADMIN_USERNAME", "testadmin")
_hashed = bcrypt.hashpw(b"testpassword", bcrypt.gensalt()).decode()
os.environ["ADMIN_PASSWORD_HASH"] = _hashed


@pytest.mark.asyncio
async def test_dashboard_without_credentials(client: AsyncClient) -> None:
    resp = await client.get("/admin/")
    assert resp.status_code == 401
    assert "WWW-Authenticate" in resp.headers
    assert resp.headers["WWW-Authenticate"] == "Basic"


@pytest.mark.asyncio
async def test_dashboard_with_wrong_password(client: AsyncClient) -> None:
    resp = await client.get("/admin/", auth=("testadmin", "wrongpassword"))
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_dashboard_with_wrong_username(client: AsyncClient) -> None:
    resp = await client.get("/admin/", auth=("hacker", "testpassword"))
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_dashboard_with_correct_credentials(client: AsyncClient) -> None:
    resp = await client.get("/admin/", auth=("testadmin", "testpassword"))
    assert resp.status_code == 200
    assert b"Dashboard" in resp.content


@pytest.mark.asyncio
async def test_no_hash_configured_rejects(client: AsyncClient, monkeypatch) -> None:
    """If ADMIN_PASSWORD_HASH is empty, all requests must be rejected."""
    from app import config as cfg
    monkeypatch.setattr(cfg.settings, "ADMIN_PASSWORD_HASH", "")
    resp = await client.get("/admin/", auth=("testadmin", "testpassword"))
    assert resp.status_code == 401
