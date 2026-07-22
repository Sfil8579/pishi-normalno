from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class InstallScriptTests(unittest.TestCase):
    def test_installers_are_release_pinned_and_verify_checksum(self) -> None:
        for name in ("install.ps1", "install.sh"):
            with self.subTest(name=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                self.assertIn("v1.0.0", text)
                self.assertIn("checksums.txt", text)
                self.assertIn("SHA256" if name.endswith(".ps1") else "sha256", text)
                self.assertNotIn("AGENTS.md", text)


if __name__ == "__main__":
    unittest.main()
