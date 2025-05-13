
"""Binary manipulation utilities for PS5 NOR images.

Implements helpers that mirror the original C# logic found in *Program.cs*:

* **scan_info(path)** – return edition, serials, model, MAC addresses.
* **convert_edition(src, edition, dst=None)** – flip Disc/Digital/Slim flags.
* **set_console_serial(src, new_serial, dst=None)** – write console S/N.
* **set_mobo_serial(src, new_serial, dst=None)** – write motherboard S/N.
* **patch_file(src, dst, digital=True)** – CLI‑compat wrapper (digital⇄disc).

All functions work on Windows, macOS and Linux. A `mmap` view keeps
changes O(1) regardless of file size.
"""
from __future__ import annotations

import mmap
import pathlib
from typing import Dict, Optional

# --------------------------------------------------------------------------------------
# Offsets & constants (derived from original C# Program.cs)
# --------------------------------------------------------------------------------------
OFFSET_VERSION_1 = 0x1C7010  # 4‑byte flag (Disc/Slim)
OFFSET_VERSION_2 = 0x1C7030  # 4‑byte flag (Digital/Slim)
SERIAL_OFFSET    = 0x1C7210  # 17‑byte console serial
MOBO_SN_OFFSET   = 0x1C7200  # 16‑byte motherboard serial
VARIANT_OFFSET   = 0x1C7226  # 19‑byte model string (CFI‑XXXXxx)
WIFI_MAC_OFFSET  = 0x1C73C0  # 6‑byte Wi‑Fi MAC
LAN_MAC_OFFSET   = 0x1C4020  # 6‑byte LAN  MAC

LEN_VERSION = 4
LEN_SERIAL  = 17
LEN_MOBO_SN = 16
LEN_MODEL   = 19
LEN_MAC     = 6

FLAG_SLIM    = bytes.fromhex("22010101")
FLAG_DISC    = bytes.fromhex("22020101")
FLAG_DIGITAL = bytes.fromhex("22030101")

EDITION_TO_FLAG = {
    "slim": FLAG_SLIM,
    "disc": FLAG_DISC,
    "digital": FLAG_DIGITAL,
}

# --------------------------------------------------------------------------------------
# Utility helpers
# --------------------------------------------------------------------------------------
def _read(mm: mmap.mmap, offset: int, length: int) -> bytes:
    mm.seek(offset)
    return mm.read(length)

def _ascii(data: bytes) -> str:
    """Decode and strip padding (0x00 / 0xFF)."""
    return data.rstrip(b"\x00\xFF").decode("latin1", errors="replace")

def _detect_edition(mm: mmap.mmap) -> str:
    for off in (OFFSET_VERSION_1, OFFSET_VERSION_2):
        flag = _read(mm, off, LEN_VERSION)
        if flag == FLAG_DIGITAL:
            return "digital"
        if flag == FLAG_DISC:
            return "disc"
        if flag == FLAG_SLIM:
            return "slim"
    return "unknown"

def scan_info(path: str | pathlib.Path) -> Dict[str, str]:
    """Return a dictionary with high‑level NOR metadata."""
    p = pathlib.Path(path)
    with p.open("rb") as fh, mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ) as mm:
        return {
            "edition": _detect_edition(mm),
            "console_serial": _ascii(_read(mm, SERIAL_OFFSET, LEN_SERIAL)),
            "mobo_serial": _ascii(_read(mm, MOBO_SN_OFFSET, LEN_MOBO_SN)),
            "model_number": _ascii(_read(mm, VARIANT_OFFSET, LEN_MODEL)),
            "wifi_mac": _read(mm, WIFI_MAC_OFFSET, LEN_MAC).hex().upper(),
            "lan_mac":  _read(mm, LAN_MAC_OFFSET, LEN_MAC).hex().upper(),
        }

# --------------------------------------------------------------------------------------
# Mutating helpers
# --------------------------------------------------------------------------------------
def _ensure_target(src: pathlib.Path, dst: Optional[pathlib.Path]) -> pathlib.Path:
    if dst is None or src.resolve() == pathlib.Path(dst).resolve():
        return src
    pathlib.Path(dst).write_bytes(src.read_bytes())
    return pathlib.Path(dst)

def _write(mm: mmap.mmap, offset: int, payload: bytes) -> None:
    mm.seek(offset)
    mm.write(payload)

def _replace_all(buf: bytearray, find: bytes, replace: bytes) -> int:
    pos = 0
    count = 0
    while True:
        i = buf.find(find, pos)
        if i == -1:
            return count
        buf[i : i + len(find)] = replace
        pos = i + len(find)
        count += 1

# --------------------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------------------
def convert_edition(src: str | pathlib.Path, edition: str, *, dst: str | pathlib.Path | None = None) -> None:
    """Convert the NOR dump to the requested *edition* (digital/disc/slim)."""
    if edition.lower() not in EDITION_TO_FLAG:
        raise ValueError("edition must be 'digital', 'disc' or 'slim'")
    src_p = pathlib.Path(src)
    dst_p = _ensure_target(src_p, pathlib.Path(dst) if dst else None)
    target_flag = EDITION_TO_FLAG[edition.lower()]
    with dst_p.open("r+b") as fh, mmap.mmap(fh.fileno(), 0) as mm:
        current = _detect_edition(mm)
        if current == edition.lower():
            return  # nothing to do
        # Overwrite the two fixed offsets first
        _write(mm, OFFSET_VERSION_1, target_flag)
        _write(mm, OFFSET_VERSION_2, target_flag)
        # Full‑image sweep to catch redundant copies
        blob = bytearray(mm)
        for flag in EDITION_TO_FLAG.values():
            if flag == target_flag:
                continue
            _replace_all(blob, flag, target_flag)
        mm[:] = blob

def set_console_serial(src: str | pathlib.Path, new_serial: str, *, dst: str | pathlib.Path | None = None) -> None:
    if not (1 <= len(new_serial) <= LEN_SERIAL):
        raise ValueError("Console serial must be 1‑17 characters long")
    serial_bytes = new_serial.encode("latin1").ljust(LEN_SERIAL, b"\0")
    src_p = pathlib.Path(src)
    dst_p = _ensure_target(src_p, pathlib.Path(dst) if dst else None)
    with dst_p.open("r+b") as fh, mmap.mmap(fh.fileno(), 0) as mm:
        _write(mm, SERIAL_OFFSET, serial_bytes)

def set_mobo_serial(src: str | pathlib.Path, new_serial: str, *, dst: str | pathlib.Path | None = None) -> None:
    if not (1 <= len(new_serial) <= LEN_MOBO_SN):
        raise ValueError("Motherboard serial must be 1‑16 characters long")
    serial_bytes = new_serial.encode("latin1").ljust(LEN_MOBO_SN, b"\0")
    src_p = pathlib.Path(src)
    dst_p = _ensure_target(src_p, pathlib.Path(dst) if dst else None)
    with dst_p.open("r+b") as fh, mmap.mmap(fh.fileno(), 0) as mm:
        _write(mm, MOBO_SN_OFFSET, serial_bytes)

# Backwards‑compat wrapper used by CLI ----------------------------------------
def patch_file(src: str, dst: str, *, digital: bool = True) -> None:
    """CLI‑compat: convert *src* to digital (default) or disc and save to *dst*."""
    convert_edition(src, "digital" if digital else "disc", dst=dst)
