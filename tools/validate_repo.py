#!/usr/bin/env python3
"""Validate the public repository and portable skill package."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "pishi-normalno"
TEXT_SUFFIXES = {
    ".cff",
    ".editorconfig",
    ".gitattributes",
    ".gitignore",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".sh",
    ".svg",
    ".toml",
    ".yaml",
    ".yml",
}
FORBIDDEN_CODEPOINTS = {0x2013, 0x2014, 0x0401, 0x0451}
ARROW_RANGES = (
    (0x2190, 0x21FF),
    (0x27F0, 0x27FF),
    (0x2900, 0x297F),
    (0x2B00, 0x2BFF),
)
LOCAL_PATH_RE = re.compile(r"[A-Za-z]:[\\/]+Users[\\/]", re.IGNORECASE)
SECRET_RE = re.compile(r"\b(?:gh[opusr]_|sk-[A-Za-z0-9_-]{16})")
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def _in_ranges(codepoint: int, ranges: Iterable[tuple[int, int]]) -> bool:
    return any(start <= codepoint <= end for start, end in ranges)


def _text_files() -> Iterable[Path]:
    ignored_parts = {".git", ".mypy_cache", ".ruff_cache", "build", "dist"}
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in ignored_parts for part in path.parts):
            continue
        if path.suffix.lower() in TEXT_SUFFIXES or path.name in TEXT_SUFFIXES:
            yield path


def _validate_frontmatter(errors: list[str]) -> None:
    skill_text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    parts = skill_text.split("---", 2)
    if len(parts) != 3 or parts[0].strip():
        errors.append("SKILL.md: некорректный YAML frontmatter")
        return
    keys = []
    values: dict[str, str] = {}
    for line in parts[1].splitlines():
        if not line.strip():
            continue
        key, separator, value = line.partition(":")
        if not separator:
            errors.append(f"SKILL.md: некорректная строка frontmatter: {line}")
            continue
        keys.append(key.strip())
        values[key.strip()] = value.strip()
    if keys != ["name", "description"]:
        errors.append("SKILL.md: frontmatter должен содержать только name и description")
    if values.get("name") != SKILL.name:
        errors.append("SKILL.md: name не совпадает с именем каталога")
    if len(skill_text.splitlines()) > 500:
        errors.append("SKILL.md: превышен лимит 500 строк")


def _validate_skill_layout(errors: list[str]) -> None:
    required = (
        SKILL / "SKILL.md",
        SKILL / "agents" / "openai.yaml",
        SKILL / "references" / "patterns.json",
        SKILL / "scripts" / "audit_russian_text.py",
    )
    for path in required:
        if not path.is_file():
            errors.append(f"Не найден обязательный файл: {path.relative_to(ROOT)}")

    forbidden_names = {"README.md", "CHANGELOG.md", "LICENSE", "CONTRIBUTING.md"}
    for path in SKILL.rglob("*"):
        if path.name in forbidden_names:
            errors.append(f"Лишний файл внутри skill folder: {path.relative_to(ROOT)}")
        if path.name == "__pycache__" or path.suffix in {".pyc", ".pyo"}:
            errors.append(f"Runtime-кеш внутри skill folder: {path.relative_to(ROOT)}")

    reference_root = SKILL / "references"
    for path in reference_root.rglob("*"):
        if path.is_file() and path.parent != reference_root:
            errors.append(f"Слишком глубокая reference-структура: {path.relative_to(ROOT)}")
        if path.suffix == ".md":
            lines = path.read_text(encoding="utf-8").splitlines()
            if len(lines) > 100 and "## Содержание" not in lines:
                errors.append(f"В длинном reference нет содержания: {path.relative_to(ROOT)}")


def _validate_text(errors: list[str]) -> None:
    for path in _text_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"Файл не читается как UTF-8: {path.relative_to(ROOT)}")
            continue
        if LOCAL_PATH_RE.search(text):
            errors.append(f"Найден локальный пользовательский путь: {path.relative_to(ROOT)}")
        if SECRET_RE.search(text):
            errors.append(f"Найден возможный секрет: {path.relative_to(ROOT)}")
        for index, char in enumerate(text):
            codepoint = ord(char)
            if codepoint in FORBIDDEN_CODEPOINTS or _in_ranges(codepoint, ARROW_RANGES):
                errors.append(
                    f"Запрещенная кодовая точка U+{codepoint:04X}: {path.relative_to(ROOT)}:{index}"
                )
                break


def _validate_links(errors: list[str]) -> None:
    for path in [ROOT / "README.md", ROOT / "README.en.md", SKILL / "SKILL.md"]:
        text = path.read_text(encoding="utf-8")
        for target in MARKDOWN_LINK_RE.findall(text):
            clean = target.split("#", 1)[0]
            if not clean or "://" in clean or clean.startswith(("mailto:", "#")):
                continue
            resolved = (path.parent / clean).resolve()
            if not resolved.exists():
                errors.append(f"Битая ссылка {target} в {path.relative_to(ROOT)}")


def _validate_rules(errors: list[str]) -> None:
    rules_path = SKILL / "references" / "patterns.json"
    try:
        config = json.loads(rules_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        errors.append(f"patterns.json: {error}")
        return
    if config.get("schema") != "pishi-normalno.patterns.v1":
        errors.append("patterns.json: неверная schema")
    if not config.get("rules"):
        errors.append("patterns.json: нет rules")
    for rule in config.get("rules", []):
        for expression in rule.get("patterns", []):
            try:
                re.compile(expression)
            except re.error as error:
                errors.append(f"patterns.json: regex {rule.get('id')}: {error}")


def validate() -> list[str]:
    errors: list[str] = []
    _validate_frontmatter(errors)
    _validate_skill_layout(errors)
    _validate_text(errors)
    _validate_links(errors)
    _validate_rules(errors)
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("Проверка не пройдена:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Репозиторий и skill package прошли проверку.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
