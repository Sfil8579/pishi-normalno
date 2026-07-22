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
CHATGPT_BUNDLE = DIST / "pishi-normalno-chatgpt.md"
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


def _without_frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        return text.strip()
    _, separator, body = text[4:].partition("\n---\n")
    return body.strip() if separator else text.strip()


def _build_chatgpt_bundle() -> str:
    intro = (
        "# Пиши нормально для обычного ChatGPT\n\n"
        "Используй этот документ как постоянную редакторскую систему внутри проекта. "
        "Автоматически применяй его ко всем существенным русским текстам: постам, "
        "маркетингу, SMM, письмам, статьям, сценариям, лендингам, анонсам, кейсам, "
        "CTA и UI-текстам. Не применяй правила к коду, командам, логам и дословным "
        "цитатам.\n\n"
        "Сохраняй факты, смысловые связи и голос автора. Не сообщай о внутренней "
        "проверке, если пользователь не просил отчет. Если исходный текст уже работает, "
        "не переписывай его ради самого факта редактуры.\n\n"
        "Этот файл является fallback для аккаунтов ChatGPT без загрузки Agent Skills. "
        "Полная версия с детерминированным аудитором находится в ZIP-пакете проекта."
    )
    parts = [intro.strip()]
    skill_text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    parts.append("# Основные инструкции\n\n" + _without_frontmatter(skill_text))
    for path in sorted((SKILL / "references").glob("*.md"), key=lambda item: item.name):
        content = path.read_text(encoding="utf-8").strip()
        parts.append(f"# Дополнение: {path.name}\n\n{content}")
    CHATGPT_BUNDLE.write_text("\n\n---\n\n".join(parts) + "\n", encoding="utf-8")
    return _sha256(CHATGPT_BUNDLE)


def build() -> str:
    DIST.mkdir(parents=True, exist_ok=True)
    chatgpt_hash = _build_chatgpt_bundle()
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
        "chatgpt_bundle": CHATGPT_BUNDLE.name,
        "chatgpt_bundle_sha256": chatgpt_hash,
        "files": manifest_files,
    }
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    CHECKSUMS.write_text(
        f"{archive_hash}  {ARCHIVE.name}\n{chatgpt_hash}  {CHATGPT_BUNDLE.name}\n",
        encoding="utf-8",
    )
    return archive_hash


def main() -> int:
    archive_hash = build()
    print(f"Создано: {ARCHIVE}")
    print(f"SHA256: {archive_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
