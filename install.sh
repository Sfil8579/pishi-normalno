#!/usr/bin/env bash
set -euo pipefail

target="codex"
version="v1.0.0"
update=0
dry_run=0
repo="fsbtactic-code/pishi-normalno"
asset="pishi-normalno.zip"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      target="$2"
      shift 2
      ;;
    --version)
      version="$2"
      shift 2
      ;;
    --update)
      update=1
      shift
      ;;
    --dry-run)
      dry_run=1
      shift
      ;;
    *)
      printf 'Unknown argument: %s\n' "$1" >&2
      exit 2
      ;;
  esac
done

case "$target" in
  codex|claude|agents) ;;
  *)
    printf 'Unknown target: %s\n' "$target" >&2
    exit 2
    ;;
esac

if command -v python3 >/dev/null 2>&1; then
  python_cmd="python3"
elif command -v python >/dev/null 2>&1; then
  python_cmd="python"
else
  printf 'Python 3.10 or newer is required.\n' >&2
  exit 2
fi

run_install() {
  local skill_dir="$1"
  local args=("$skill_dir/scripts/cli.py" install --target "$target")
  if [[ $update -eq 1 ]]; then
    args+=(--update)
  fi
  if [[ $dry_run -eq 1 ]]; then
    args+=(--dry-run)
  fi
  PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1 "$python_cmd" "${args[@]}"
}

script_dir=""
if [[ -n "${BASH_SOURCE[0]:-}" && -f "${BASH_SOURCE[0]}" ]]; then
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi

if [[ -n "$script_dir" && -f "$script_dir/skills/pishi-normalno/SKILL.md" ]]; then
  run_install "$script_dir/skills/pishi-normalno"
  exit 0
fi

temp_root="$(mktemp -d)"
cleanup() {
  rm -rf -- "$temp_root"
}
trap cleanup EXIT

base_url="https://github.com/$repo/releases/download/$version"
curl -fsSL "$base_url/$asset" -o "$temp_root/$asset"
curl -fsSL "$base_url/checksums.txt" -o "$temp_root/checksums.txt"

expected="$(awk '$2 == "pishi-normalno.zip" { print $1; exit }' "$temp_root/checksums.txt")"
if [[ -z "$expected" ]]; then
  printf 'Archive checksum is missing.\n' >&2
  exit 2
fi
if command -v sha256sum >/dev/null 2>&1; then
  actual="$(sha256sum "$temp_root/$asset" | awk '{ print $1 }')"
else
  actual="$(shasum -a 256 "$temp_root/$asset" | awk '{ print $1 }')"
fi
if [[ "$expected" != "$actual" ]]; then
  printf 'Archive checksum mismatch.\n' >&2
  exit 2
fi

"$python_cmd" - "$temp_root/$asset" "$temp_root/extracted" <<'PY'
from pathlib import Path
import sys
import zipfile

archive = Path(sys.argv[1])
destination = Path(sys.argv[2])
destination.mkdir(parents=True)
root = destination.resolve()
with zipfile.ZipFile(archive) as bundle:
    for member in bundle.infolist():
        resolved = (destination / member.filename).resolve()
        if root not in resolved.parents and resolved != root:
            raise SystemExit("Unsafe archive path")
    bundle.extractall(destination)
PY

downloaded_skill="$temp_root/extracted/pishi-normalno"
if [[ ! -f "$downloaded_skill/SKILL.md" ]]; then
  printf 'Release archive has an invalid structure.\n' >&2
  exit 2
fi
run_install "$downloaded_skill"
