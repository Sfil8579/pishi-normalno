from __future__ import annotations

import hashlib
import json
import sys
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import package_skill
import validate_repo


class RepositoryTests(unittest.TestCase):
    def test_repository_contract(self) -> None:
        self.assertEqual(validate_repo.validate(), [])

    def test_release_archive_is_deterministic(self) -> None:
        first = package_skill.build()
        first_bytes = package_skill.ARCHIVE.read_bytes()
        second = package_skill.build()
        second_bytes = package_skill.ARCHIVE.read_bytes()
        self.assertEqual(first, second)
        self.assertEqual(first_bytes, second_bytes)

    def test_release_archive_contains_only_skill(self) -> None:
        package_skill.build()
        with zipfile.ZipFile(package_skill.ARCHIVE) as bundle:
            names = bundle.namelist()
        self.assertTrue(names)
        self.assertTrue(all(name.startswith("pishi-normalno/") for name in names))
        self.assertFalse(any("__pycache__" in name for name in names))
        self.assertFalse(any(name.endswith("README.md") for name in names))

    def test_release_manifest_matches_archive(self) -> None:
        package_skill.build()
        manifest = json.loads(package_skill.MANIFEST.read_text(encoding="utf-8"))
        actual = hashlib.sha256(package_skill.ARCHIVE.read_bytes()).hexdigest()
        chatgpt_actual = hashlib.sha256(package_skill.CHATGPT_BUNDLE.read_bytes()).hexdigest()
        self.assertEqual(manifest["archive_sha256"], actual)
        self.assertEqual(manifest["chatgpt_bundle_sha256"], chatgpt_actual)
        self.assertEqual(manifest["schema"], "pishi-normalno.release.v1")

    def test_chatgpt_bundle_contains_full_editorial_system(self) -> None:
        package_skill.build()
        text = package_skill.CHATGPT_BUNDLE.read_text(encoding="utf-8")
        self.assertIn("# Основные инструкции", text)
        for reference in (package_skill.SKILL / "references").glob("*.md"):
            self.assertIn(f"# Дополнение: {reference.name}", text)
        forbidden = {0x2013, 0x2014, 0x0401, 0x0451}
        self.assertFalse(any(ord(char) in forbidden for char in text))


if __name__ == "__main__":
    unittest.main()
