from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any, ClassVar

sys.dont_write_bytecode = True


ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "pishi-normalno"
sys.path.insert(0, str(SKILL / "scripts"))

import audit_russian_text as audit  # type: ignore[import-not-found]


class DemoTests(unittest.TestCase):
    config: ClassVar[dict[str, Any]]
    source: ClassVar[str]

    @classmethod
    def setUpClass(cls) -> None:
        cls.config = audit.load_config(SKILL / "references" / "patterns.json")
        cls.source = (ROOT / "demo" / "source.md").read_text(encoding="utf-8")

    def test_bad_demo_exposes_composite_slop(self) -> None:
        text = (ROOT / "demo" / "bad-result.md").read_text(encoding="utf-8")
        findings = audit.audit_text(
            text,
            genre="social",
            config=self.config,
            source_text=self.source,
        )
        codes = {item.code for item in findings}
        self.assertIn("nominal-fragment-pair", codes)
        self.assertIn("final-question-chain", codes)
        self.assertIn("source-benefit-claim-added", codes)

    def test_clean_demo_has_no_blocking_findings(self) -> None:
        text = (ROOT / "demo" / "clean-result.md").read_text(encoding="utf-8")
        findings = audit.audit_text(
            text,
            genre="social",
            config=self.config,
            source_text=self.source,
        )
        self.assertEqual(audit.exit_status(findings, strict=True), 0)


if __name__ == "__main__":
    unittest.main()
