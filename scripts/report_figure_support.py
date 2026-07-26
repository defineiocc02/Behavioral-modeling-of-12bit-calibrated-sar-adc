"""Repository-owned plotting primitives for deterministic report figures.

The visual design follows the Figura workflow, but artifact generation never
imports user-level skill files.  Keeping this small layer in the repository
removes a hidden local-versus-CI dependency while retaining the reviewed style.
"""

from __future__ import annotations

import os
from pathlib import Path

import matplotlib as mpl


class _PubStyle:
    _sizes = {
        "single": (3.3, 2.2),
        "single_tall": (3.3, 3.0),
        "double": (6.8, 2.6),
        "double_tall": (6.8, 4.0),
        "square": (3.3, 3.3),
    }

    @staticmethod
    def apply(extra: dict | None = None) -> None:
        mpl.rcdefaults()
        params = {
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "font.family": "sans-serif",
            "font.sans-serif": ["DejaVu Sans"],
            "font.size": 9,
            "axes.titlesize": 10,
            "axes.labelsize": 9,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.linewidth": 0.8,
            "axes.labelpad": 3.0,
            "axes.titlepad": 6.0,
            "xtick.major.size": 3.0,
            "ytick.major.size": 3.0,
            "xtick.major.width": 0.8,
            "ytick.major.width": 0.8,
            "xtick.direction": "out",
            "ytick.direction": "out",
            "lines.linewidth": 1.25,
            "lines.markersize": 4.0,
            "patch.linewidth": 0.8,
            "axes.grid": False,
            "legend.frameon": False,
            "figure.facecolor": "white",
            "mathtext.fontset": "stixsans",
            "mathtext.default": "regular",
        }
        if extra:
            params.update(extra)
        mpl.rcParams.update(params)

    @classmethod
    def figsize(cls, kind: str = "single") -> tuple[float, float]:
        try:
            return cls._sizes[kind]
        except KeyError as exc:
            raise ValueError(f"unknown figure size: {kind}") from exc


class _Colors:
    OKABE_ITO = (
        "#0072B2",
        "#D55E00",
        "#009E73",
        "#CC79A7",
        "#56B4E9",
        "#E69F00",
        "#000000",
        "#F0E442",
    )

    @classmethod
    def categorical(cls, n: int = 8) -> list[str]:
        if n > len(cls.OKABE_ITO):
            raise ValueError(f"requested {n} colors; maximum is 8")
        return list(cls.OKABE_ITO[:n])


class _Export:
    @staticmethod
    def save(
        fig,
        name: str,
        *,
        formats: tuple[str, ...] = ("pdf", "svg", "png"),
        outdir: str | Path = "figures",
        dpi: int = 300,
    ) -> list[Path]:
        if not name or Path(name).name != name or name in (".", ".."):
            raise ValueError("name must be a basename stem")
        destination = Path(outdir)
        destination.mkdir(parents=True, exist_ok=True)
        outputs: list[Path] = []
        temporary: list[tuple[Path, Path]] = []
        try:
            for extension in formats:
                final = destination / f"{name}.{extension}"
                temp = destination / f".{name}.{extension}.tmp"
                kwargs = {
                    "format": extension,
                    "bbox_inches": "tight",
                    "pad_inches": 0.02,
                }
                if extension == "png":
                    kwargs["dpi"] = dpi
                fig.savefig(temp, **kwargs)
                temporary.append((temp, final))
            for temp, final in temporary:
                os.replace(temp, final)
                outputs.append(final)
        except Exception:
            for temp, _ in temporary:
                temp.unlink(missing_ok=True)
            raise
        return outputs


pubstyle = _PubStyle()
colors = _Colors()
export = _Export()
