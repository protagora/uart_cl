
"""Unit‑tests for uartcl.nor.patcher."""
import os, tempfile, pathlib, unittest
from uartcl.nor import patcher

class NorPatcherTests(unittest.TestCase):
    FILESIZE = patcher.LAN_MAC_OFFSET + patcher.LEN_MAC + 1  # minimum size

    def _make_fake_nor(self, *, edition: str = "disc") -> pathlib.Path:
        """Create a temp NOR dump with deterministic content."""
        fd, path = tempfile.mkstemp(prefix="nor_test_", suffix=".bin")
        os.close(fd)
        p = pathlib.Path(path)
        buf = bytearray(b"\xFF") * self.FILESIZE  # typical erased NOR value
        # Inject flags / serials / MAC
        flag = patcher.EDITION_TO_FLAG[edition]
        for off in (patcher.OFFSET_VERSION_1, patcher.OFFSET_VERSION_2):
            buf[off : off + patcher.LEN_VERSION] = flag
        buf[patcher.SERIAL_OFFSET : patcher.SERIAL_OFFSET + patcher.LEN_SERIAL] = b"PS5TESTSERIAL123"
        buf[patcher.MOBO_SN_OFFSET : patcher.MOBO_SN_OFFSET + patcher.LEN_MOBO_SN] = b"MOBO123456789ABC"
        buf[patcher.VARIANT_OFFSET : patcher.VARIANT_OFFSET + patcher.LEN_MODEL] = b"CFI-1016A"
        buf[patcher.WIFI_MAC_OFFSET : patcher.WIFI_MAC_OFFSET + patcher.LEN_MAC] = bytes.fromhex("A1B2C3D4E5F6")
        buf[patcher.LAN_MAC_OFFSET  : patcher.LAN_MAC_OFFSET  + patcher.LEN_MAC] = bytes.fromhex("010203040506")
        p.write_bytes(buf)
        return p

    def test_scan_info(self):
        nor_path = self._make_fake_nor()
        info = patcher.scan_info(nor_path)
        self.assertEqual(info["edition"], "disc")
        self.assertEqual(info["console_serial"], "PS5TESTSERIAL123")
        self.assertEqual(info["wifi_mac"], "A1B2C3D4E5F6")
        pathlib.Path(nor_path).unlink()

    def test_convert_edition(self):
        nor_path = self._make_fake_nor(edition="disc")
        patcher.convert_edition(nor_path, "digital")
        info = patcher.scan_info(nor_path)
        self.assertEqual(info["edition"], "digital")
        pathlib.Path(nor_path).unlink()

    def test_set_serials(self):
        nor_path = self._make_fake_nor()
        patcher.set_console_serial(nor_path, "NEWCONSOLESN")
        patcher.set_mobo_serial(nor_path, "NEWMOBO123")
        info = patcher.scan_info(nor_path)
        self.assertEqual(info["console_serial"], "NEWCONSOLESN")
        self.assertEqual(info["mobo_serial"], "NEWMOBO123")
        pathlib.Path(nor_path).unlink()

if __name__ == "__main__":
    unittest.main()
