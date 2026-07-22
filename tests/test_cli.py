from __future__ import annotations

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.dont_write_bytecode = True


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills" / "pishi-normalno" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import cli  # type: ignore[import-not-found]


class CliTests(unittest.TestCase):
    def test_doctor(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            status = cli.main(["doctor"])
        self.assertEqual(status, 0)
        self.assertIn("Аудитор и каталог правил работают", output.getvalue())

    def test_doctor_reconfigures_legacy_console_to_utf8(self) -> None:
        buffer = io.BytesIO()
        output = io.TextIOWrapper(buffer, encoding="cp1252")
        with redirect_stdout(output):
            status = cli.main(["doctor"])
            output.flush()
        rendered = buffer.getvalue().decode("utf-8")
        output.detach()
        self.assertEqual(status, 0)
        self.assertIn("Аудитор и каталог правил работают", rendered)

    def test_where(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            status = cli.main(["where"])
        self.assertEqual(status, 0)
        self.assertEqual(Path(output.getvalue().strip()), cli.SKILL_DIR)

    def test_official_global_skill_paths(self) -> None:
        home = Path("/example/home")
        with patch.object(Path, "home", return_value=home):
            self.assertEqual(
                cli._target_path("codex", None),
                home / ".agents" / "skills" / "pishi-normalno",
            )
            self.assertEqual(
                cli._target_path("claude", None),
                home / ".claude" / "skills" / "pishi-normalno",
            )

    def test_install_to_custom_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "installed" / "pishi-normalno"
            with redirect_stdout(io.StringIO()):
                status = cli.main(["install", "--target", "custom", "--dest", str(destination)])
            self.assertEqual(status, 0)
            self.assertTrue((destination / "SKILL.md").is_file())
            self.assertFalse(any(destination.rglob("*.pyc")))

    def test_install_refuses_silent_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "pishi-normalno"
            destination.mkdir()
            error = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(error):
                status = cli.main(["install", "--target", "custom", "--dest", str(destination)])
            self.assertEqual(status, 2)
            self.assertIn("уже установлен", error.getvalue())

    def test_audit_subcommand_preserves_status(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            text_path = Path(temporary) / "post.md"
            text_path.write_text("Аккуратный промпт. Трата твоего времени.", encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                status = cli.main(["audit", str(text_path), "--genre", "social", "--strict"])
            self.assertEqual(status, 1)


if __name__ == "__main__":
    unittest.main()
