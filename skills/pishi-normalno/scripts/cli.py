#!/usr/bin/env python3
"""Command line wrapper for the Pishi Normalno skill and auditor."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from collections.abc import Sequence
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

try:
    __version__ = version("pishi-normalno")
except PackageNotFoundError:
    __version__ = "1.0.0"

try:
    from . import audit_russian_text as audit
except ImportError:
    import audit_russian_text as audit  # type: ignore[import-not-found, no-redef]


SKILL_DIR = Path(__file__).resolve().parent.parent
SKILL_NAME = "pishi-normalno"


def _target_path(target: str, custom: str | None) -> Path:
    if target == "custom":
        if not custom:
            raise ValueError("Для target=custom передайте --dest.")
        return Path(custom).expanduser().resolve()
    if custom:
        return Path(custom).expanduser().resolve()
    if target == "codex":
        codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
        return codex_home / "skills" / SKILL_NAME
    if target == "claude":
        return Path.home() / ".claude" / "skills" / SKILL_NAME
    if target == "agents":
        return Path.home() / ".agents" / "skills" / SKILL_NAME
    raise ValueError(f"Неизвестная цель установки: {target}")


def _ignore_runtime_noise(_directory: str, names: list[str]) -> set[str]:
    ignored = {"__pycache__"}
    ignored.update(name for name in names if name.endswith((".pyc", ".pyo")))
    return ignored


def _verify_skill(path: Path) -> None:
    required = (
        path / "SKILL.md",
        path / "agents" / "openai.yaml",
        path / "references" / "patterns.json",
        path / "scripts" / "audit_russian_text.py",
    )
    missing = [str(item) for item in required if not item.is_file()]
    if missing:
        raise ValueError("В пакете не хватает файлов: " + ", ".join(missing))
    config = audit.load_config(path / "references" / "patterns.json")
    if not config["rules"]:
        raise ValueError("Каталог правил пуст.")


def install_skill(*, target: str, custom: str | None, update: bool, dry_run: bool) -> int:
    destination = _target_path(target, custom)
    print(f"Источник: {SKILL_DIR}")
    print(f"Назначение: {destination}")
    if destination.exists() and not update:
        print("Скилл уже установлен. Для обновления добавьте --update.", file=sys.stderr)
        return 2
    if dry_run:
        print("Dry run: файлы не изменены.")
        return 0

    destination.parent.mkdir(parents=True, exist_ok=True)
    staging_root = Path(tempfile.mkdtemp(prefix=f".{SKILL_NAME}-", dir=destination.parent))
    staged_skill = staging_root / SKILL_NAME
    backup: Path | None = None
    try:
        shutil.copytree(SKILL_DIR, staged_skill, ignore=_ignore_runtime_noise)
        _verify_skill(staged_skill)
        if destination.exists():
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
            backup = destination.with_name(f".{SKILL_NAME}.backup-{stamp}")
            destination.replace(backup)
        staged_skill.replace(destination)
    except Exception:
        if backup is not None and backup.exists() and not destination.exists():
            backup.replace(destination)
        raise
    finally:
        shutil.rmtree(staging_root, ignore_errors=True)

    print("Скилл установлен и проверен.")
    if backup is not None:
        print(f"Предыдущая версия сохранена: {backup}")
    print("Перезапустите агент, чтобы он перечитал каталог скиллов.")
    return 0


def doctor() -> int:
    try:
        _verify_skill(SKILL_DIR)
        config = audit.load_config(SKILL_DIR / "references" / "patterns.json")
        clean = audit.audit_text(
            "Редактор сохранил факты и уточнил формулировку.",
            genre="neutral",
            config=config,
        )
        bad = audit.audit_text(
            "Аккуратный промпт. Трата твоего времени.",
            genre="social",
            config=config,
        )
        if clean or "nominal-fragment-pair" not in {item.code for item in bad}:
            raise ValueError("Самопроверка аудитора дала неожиданный результат.")
    except (OSError, ValueError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 2
    print(f"Pishi Normalno {__version__}")
    print(f"Скилл: {SKILL_DIR}")
    print(f"Правил: {len(config['rules'])}")
    print("Аудитор и каталог правил работают.")
    return 0


def _handle_audit(args: argparse.Namespace) -> int:
    if not args.audit_args:
        print("audit требует путь к файлу или - для stdin", file=sys.stderr)
        return 2
    return audit.main(args.audit_args)


def _handle_doctor(_args: argparse.Namespace) -> int:
    return doctor()


def _handle_where(_args: argparse.Namespace) -> int:
    print(SKILL_DIR)
    return 0


def _handle_install(args: argparse.Namespace) -> int:
    try:
        return install_skill(
            target=args.target,
            custom=args.dest,
            update=args.update,
            dry_run=args.dry_run,
        )
    except (OSError, ValueError) as error:
        print(f"Ошибка установки: {error}", file=sys.stderr)
        return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pishi-normalno",
        description="Русский редакторский скилл и детерминированный аудитор.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command")

    audit_parser = subparsers.add_parser("audit", help="Проверить русский текст")
    audit_parser.add_argument("audit_args", nargs=argparse.REMAINDER)
    audit_parser.set_defaults(handler=_handle_audit)

    doctor_parser = subparsers.add_parser("doctor", help="Проверить установку и правила")
    doctor_parser.set_defaults(handler=_handle_doctor)
    where_parser = subparsers.add_parser("where", help="Показать путь к скиллу")
    where_parser.set_defaults(handler=_handle_where)

    install_parser = subparsers.add_parser("install", help="Установить скилл")
    install_parser.add_argument(
        "--target",
        choices=("codex", "claude", "agents", "custom"),
        default="codex",
    )
    install_parser.add_argument("--dest", help="Точный путь назначения")
    install_parser.add_argument(
        "--update", action="store_true", help="Обновить существующую установку"
    )
    install_parser.add_argument(
        "--dry-run", action="store_true", help="Показать действие без записи"
    )
    install_parser.set_defaults(handler=_handle_install)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    known_commands = {"audit", "doctor", "where", "install", "-h", "--help", "--version"}
    if arguments and arguments[0] not in known_commands:
        return audit.main(arguments)

    parser = _build_parser()
    args = parser.parse_args(arguments)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 0
    if not callable(handler):
        raise TypeError("Некорректный обработчик CLI-команды.")
    result = handler(args)
    if not isinstance(result, int):
        raise TypeError("CLI-команда вернула некорректный код завершения.")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
