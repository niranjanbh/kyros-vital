"""Tests for LocalDiskStorage: save/read/delete roundtrip and signed URL HMAC."""

import hashlib
import hmac
import time

import pytest

from app.core.storage import LocalDiskStorage


@pytest.fixture
def storage(tmp_path) -> LocalDiskStorage:
    return LocalDiskStorage(str(tmp_path))


async def test_save_read_delete_roundtrip(storage: LocalDiskStorage) -> None:
    content = b"hello kyros"
    key = "test/file.bin"

    returned_key = await storage.save(content, key, "application/octet-stream")
    assert returned_key == key

    data = await storage.read(key)
    assert data == content

    await storage.delete(key)

    with pytest.raises(FileNotFoundError):
        await storage.read(key)


async def test_save_creates_nested_directories(storage: LocalDiskStorage) -> None:
    key = "user-abc/labs/report.pdf"
    await storage.save(b"pdf content", key, "application/pdf")
    data = await storage.read(key)
    assert data == b"pdf content"


async def test_delete_nonexistent_is_silent(storage: LocalDiskStorage) -> None:
    # Should not raise even if file doesn't exist
    await storage.delete("nonexistent/file.bin")


async def test_signed_url_contains_valid_hmac(storage: LocalDiskStorage) -> None:
    from app.config import settings

    key = "user-1/labs/test.pdf"
    url = await storage.signed_url(key, ttl_seconds=3600)

    # Parse query params from the URL
    _, qs = url.split("?", 1)
    params = dict(part.split("=", 1) for part in qs.split("&"))
    expires = int(params["expires"])
    sig = params["sig"]

    # Verify HMAC
    expected = hmac.new(
        settings.SIGNING_SECRET.encode(),
        f"{key}:{expires}".encode(),
        hashlib.sha256,
    ).hexdigest()
    assert sig == expected


async def test_signed_url_expires_in_future(storage: LocalDiskStorage) -> None:
    url = await storage.signed_url("some/key.txt", ttl_seconds=600)
    _, qs = url.split("?", 1)
    params = dict(part.split("=", 1) for part in qs.split("&"))
    expires = int(params["expires"])
    assert expires > int(time.time())


async def test_signed_url_ttl_respected(storage: LocalDiskStorage) -> None:
    ttl = 1800
    before = int(time.time())
    url = await storage.signed_url("a/b.txt", ttl_seconds=ttl)
    after = int(time.time())

    _, qs = url.split("?", 1)
    params = dict(part.split("=", 1) for part in qs.split("&"))
    expires = int(params["expires"])

    assert before + ttl <= expires <= after + ttl + 1


async def test_path_traversal_raises(storage: LocalDiskStorage) -> None:
    with pytest.raises(ValueError, match="Invalid storage key"):
        await storage.save(b"x", "../../etc/passwd", "text/plain")
