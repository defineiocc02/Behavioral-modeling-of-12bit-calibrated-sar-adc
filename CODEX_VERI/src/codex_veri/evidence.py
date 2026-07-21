"""Evidence integrity helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def verify_source_manifest(project_root: str | Path) -> list[dict[str, object]]:
    root = Path(project_root).resolve()
    manifest_path = root / "evidence" / "source_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    results: list[dict[str, object]] = []
    for source in manifest["sources"]:
        raw = Path(source["path"])
        path = raw if raw.is_absolute() else (root / raw).resolve()
        digest = hashlib.sha256(path.read_bytes()).hexdigest().upper()
        size = path.stat().st_size
        results.append(
            {
                "path": str(path),
                "exists": path.exists(),
                "bytes": size,
                "bytes_match": size == int(source["bytes"]),
                "sha256": digest,
                "sha256_match": digest == str(source["sha256"]).upper(),
            }
        )
    return results
