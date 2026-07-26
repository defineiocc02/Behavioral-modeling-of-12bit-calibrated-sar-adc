"""Generate a deterministic manifest for the frozen VM standalone evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(root: Path) -> dict[str, object]:
    files = []
    # pathlib ordering follows host filesystem semantics; case-fold the
    # repository-relative POSIX path so Windows and Linux emit identical JSON.
    paths = sorted(
        root.rglob("*"),
        key=lambda path: path.relative_to(root).as_posix().casefold(),
    )
    for path in paths:
        if not path.is_file() or path.name == "manifest.json":
            continue
        files.append(
            {
                "path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )

    status_path = root / "reports" / "run_status.txt"
    statuses = {}
    if status_path.exists():
        for line in status_path.read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                statuses[key] = value

    return {
        "schema_version": 1,
        "captured_date": "2026-07-26",
        "sandbox_source_commit": "74e7366",
        "remote_root": "/home/meow/jxy/trae_sandbox/current_git_74e7366",
        "protected_main_root": "/home/meow/jxy/12bit_50M_SAR",
        "protected_main_files_newer_than_run_marker": 0,
        "statuses": statuses,
        "files": files,
    }


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=repo_root / "evidence" / "vm_sandbox" / "current_git_74e7366",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    manifest = build_manifest(root)
    output = root / "manifest.json"
    output.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(output)


if __name__ == "__main__":
    main()
