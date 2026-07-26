# Version and artifact management

## Active release

The only active release line in this worktree is `v3.1.1` on branch
`codex/python-cal-validation`.

Version-bearing files must agree:

```text
VERSION
pyproject.toml
src/python_cal/__init__.py
spec.yml
README.md badge
docs/final_report.tex
```

## Artifact classes

| Class | Location | Git policy |
|---|---|---|
| Source | `src/python_cal/`, `rtl/`, `va/`, `scripts/` | tracked |
| Report toolchain | `requirements/report-render-py313.txt` | tracked and pinned |
| Frozen v3.1 evidence | `evidence/mismatch_matrix/` | tracked |
| Frozen VM standalone evidence | `evidence/vm_sandbox/` | tracked, sanitized, hashed |
| Active v3.1 figures | `docs/figures/mismatch_report/` | tracked |
| Final report | `docs/final_report.tex`, `docs/final_report.pdf` | tracked |
| Historical v3.0 figures | `docs/archive/v3.0/` | tracked archive; never used by v3.1 |
| Working simulation output | `src/python_cal/validation_results/` | ignored |
| Vivado/XSIM temporary output | `sim_work/`, `.Xil/`, logs/databases | ignored |
| Python/LaTeX caches | `__pycache__/`, `.pytest_cache/`, auxiliary files | ignored |

## Evidence selection

The formal matrix has exactly five declared cases. `freeze_mismatch_evidence.py`
selects the latest complete CSV, summary and run manifest for each case.
`summarize_mismatch_matrix.py` then records file hashes plus current pipeline,
configuration, calibrator, decoder and acceptance hashes.

Figures and LaTeX metrics read only the frozen evidence tree. They must never
read the ignored working result directory when building a release.

Figure generation always uses the repository-owned
`scripts/report_figure_support.py` and Matplotlib's bundled DejaVu Sans. It must
not import a user-level Figura checkout or depend on host-only Arial/YaHei
fonts. Python 3.13 rendering dependencies are pinned in
`requirements/report-render-py313.txt`; CI records the resolved versions and
font path. CI enforces byte-identical regeneration for SVG/PDF and generated
metrics. PNG is a cross-platform preview: CI verifies its count, decodability,
dimensions and color mode, while visual QA and the exact vector gate protect
its content.

## Dirty-worktree discipline

Before committing:

1. wait for all formal processes to finish;
2. freeze and aggregate the selected evidence;
3. regenerate active figures and the PDF from that evidence;
4. run Python, XSIM, synthesis/report checks and PDF visual QA;
5. inspect `git status`, `git diff --check` and the complete staged diff;
6. stage only source, frozen evidence, active figures, report and explicit
   historical moves;
7. verify the branch and remote before push.

No ignored simulation output, temporary runner, cache, Vivado database or
unreviewed local file belongs in the release commit.
