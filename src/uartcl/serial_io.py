"""Cross‑platform serial helpers (replaces SerialPort code in Program.cs)."""
import asyncio
from typing import AsyncGenerator, Tuple, List
import serial  # type: ignore
import serial.tools.list_ports as list_ports

DEFAULT_BAUD = 115_200

class UartSession:
    """Async wrapper around a *pyserial* `Serial` object."""

    def __init__(self, port: str, baud: int = DEFAULT_BAUD, *, timeout: float = 0.5):
        self._ser = serial.Serial(port, baudrate=baud, timeout=timeout)

    async def read_lines(self) -> AsyncGenerator[str, None]:
        """Yield lines from the port without blocking the event‑loop."""
        loop = asyncio.get_running_loop()
        while True:
            line: bytes = await loop.run_in_executor(None, self._ser.readline)
            if not line:
                continue  # timeout – keep listening
            yield line.decode(errors="replace").rstrip("\r\n")

    def write(self, data: str) -> None:
        self._ser.write((data + "\r\n").encode())

    def close(self) -> None:
        self._ser.close()

    # Context‑manager sugar
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        self.close()


def available_ports() -> List[Tuple[str, str]]:
    """Return list of `(device, description)` pairs present in the system."""
    return [(p.device, p.description) for p in list_ports.comports()]
