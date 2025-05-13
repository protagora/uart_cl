"""Online / offline error‑code database logic."""
from __future__ import annotations
import json, httpx, pathlib, asyncio
from typing import Dict

_DB_URL = "https://uart.codes/latest.json"
_CACHE = pathlib.Path.home() / ".cache" / "uartcl" / "db.json"

class ErrorDB:
    """Lazily loads and caches the PS5 UART error‑code list."""

    _codes: Dict[str, str] | None = None

    @classmethod
    async def ensure_latest(cls) -> None:
        _CACHE.parent.mkdir(parents=True, exist_ok=True)
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(_DB_URL)
            r.raise_for_status()
            _CACHE.write_bytes(r.content)
            cls._codes = json.loads(r.text)

    @classmethod
    def _load_offline(cls) -> None:
        if not _CACHE.exists():
            raise FileNotFoundError("Offline DB missing – run `uartcl db download` first.")
        cls._codes = json.loads(_CACHE.read_text())

    @classmethod
    def translate(cls, code_hex: str) -> str:
        if cls._codes is None:
            cls._load_offline()
        return cls._codes.get(code_hex.upper(), "<unknown error code>")
