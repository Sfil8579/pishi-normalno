#!/usr/bin/env python3
"""Build a deterministic release archive for the portable skill."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "pishi-normalno"
DIST = ROOT / "dist"
ARCHIVE = DIST / "pishi-normalno.zip"
CHECKSUMS = DIST / "checksums.txt"
MANIFEST = DIST / "pishi-normalno.manifest.json"
FIXED_TIME = (2026, 7, 22, 0, 0, 0)


def _files() -> list[Path]:
    result = []
    for path in SKILL.rglob("*"):
        if not path.is_file():
            continue
        if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        result.append(path)
    return sorted(result, key=lambda item: item.relative_to(SKILL).as_posix())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build() -> str:
    DIST.mkdir(parents=True, exist_ok=True)
    manifest_files = []
    with zipfile.ZipFile(
        ARCHIVE,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as bundle:
        for path in _files():
            relative = path.relative_to(SKILL).as_posix()
            archive_name = f"pishi-normalno/{relative}"
            data = path.read_bytes()
            info = zipfile.ZipInfo(archive_name, date_time=FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            mode = 0o755 if path.suffix in {".py", ".sh"} else 0o644
            info.external_attr = mode << 16
            bundle.writestr(info, data, compresslevel=9)
            manifest_files.append(
                {
                    "path": archive_name,
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "size": len(data),
                }
            )

    archive_hash = _sha256(ARCHIVE)
    manifest = {
        "schema": "pishi-normalno.release.v1",
        "version": "1.0.0",
        "archive": ARCHIVE.name,
        "archive_sha256": archive_hash,
        "files": manifest_files,
    }
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    CHECKSUMS.write_text(f"{archive_hash}  {ARCHIVE.name}\n", encoding="utf-8")
    return archive_hash


def main() -> int:
    archive_hash = build()
    print(f"Создано: {ARCHIVE}")
    print(f"SHA256: {archive_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
