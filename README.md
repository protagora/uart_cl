# UART‑CL (Python edition)
A pure‑Python, cross‑platform rewrite of the original C# UART‑CL tool for PS5 NOR repair.

Original tool which inspired this oprt: <a href="https://github.com/TheCod3rYouTube/PS5NorModifier">PS5 NOR Modifier</a>

* **Serial console** via `pyserial`
* **NOR patching** scaffolding (logic moved to `uartcl.nor`)
* **Error‑code translation** with online/offline JSON cache
* **CLI** built with `click`

```bash
pip install uartcl  # once published to PyPI
uartcl uart --port /dev/ttyUSB0 --baud 115200
```