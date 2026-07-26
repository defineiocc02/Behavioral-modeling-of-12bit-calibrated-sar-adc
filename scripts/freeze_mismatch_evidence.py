"""Copy the latest complete formal matrix artifacts into the tracked evidence tree."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


CASE_ORDER = (
    "ideal_zero_noise",
    "mismatch_0p5_zero_noise",
    "mismatch_0p5_calnoise_0p3mV",
    "mismatch_1p0_zero_noise",
    "mismatch_1p0_calnoise_0p3mV",
)


def _latest(path: Path, pattern: str) -> Path:
    matches = sorted(path.glob(pattern), key=lambda item: item.stat().st_mtime)
    if not matches:
        raise FileNotFoundError(f"no {pattern} under {path}")
    return matches[-1]


def freeze(source_root: Path, destination_root: Path) -> None:
    selected: list[tuple[Path, Path]] = []
    for case in CASE_ORDER:
        source_case = source_root / case
        destination_case = destination_root / case
        selected.extend(
            [
                (
                    _latest(source_case, "final_pipeline_*.csv"),
                    destination_case,
                ),
                (
                    _latest(source_case, "final_summary_*.json"),
                    destination_case,
                ),
                (source_case / "run_manifest.json", destination_case),
            ]
        )
    for source, destination in selected:
        if not source.exists():
            raise FileNotFoundError(source)
        destination.mkdir(parents=True, exist_ok=True)
        target = destination / source.name
        shutil.copy2(source, target)
        print(f"{source} -> {target}")


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        type=Path,
        default=(
            repo_root
            / "src"
            / "python_cal"
            / "validation_results"
            / "mismatch_matrix"
        ),
    )
    parser.add_argument(
        "--destination",
        type=Path,
        default=repo_root / "evidence" / "mismatch_matrix",
    )
    args = parser.parse_args()
    freeze(args.source.resolve(), args.destination.resolve())


if __name__ == "__main__":
    main()
