import hashlib
import hmac
import time
from pathlib import Path
from typing import Protocol, runtime_checkable

import aiofiles
import aiofiles.os

from app.config import settings


@runtime_checkable
class IStorageAdapter(Protocol):
    async def save(self, content: bytes, key: str, mime_type: str) -> str: ...
    async def read(self, key: str) -> bytes: ...
    async def delete(self, key: str) -> None: ...
    async def signed_url(self, key: str, ttl_seconds: int = 3600) -> str: ...


class LocalDiskStorage:
    def __init__(self, base_dir: str) -> None:
        self._base = Path(base_dir)

    def _path(self, key: str) -> Path:
        p = (self._base / key).resolve()
        if not str(p).startswith(str(self._base.resolve())):
            raise ValueError("Invalid storage key.")
        return p

    async def save(self, content: bytes, key: str, mime_type: str) -> str:
        path = self._path(key)
        await aiofiles.os.makedirs(str(path.parent), exist_ok=True)
        async with aiofiles.open(path, "wb") as f:
            await f.write(content)
        return key

    async def read(self, key: str) -> bytes:
        async with aiofiles.open(self._path(key), "rb") as f:
            data: bytes = await f.read()
        return data

    async def delete(self, key: str) -> None:
        path = self._path(key)
        if await aiofiles.os.path.exists(str(path)):
            await aiofiles.os.remove(str(path))

    async def signed_url(self, key: str, ttl_seconds: int = 3600) -> str:
        expires = int(time.time()) + ttl_seconds
        sig = hmac.new(
            settings.SIGNING_SECRET.encode(),
            f"{key}:{expires}".encode(),
            hashlib.sha256,
        ).hexdigest()
        return f"/storage/{key}?expires={expires}&sig={sig}"


def get_storage() -> IStorageAdapter:
    backend = settings.STORAGE_BACKEND
    if backend == "local":
        return LocalDiskStorage(settings.STORAGE_DIR)
    raise ValueError(f"Unknown STORAGE_BACKEND: {backend!r}")
