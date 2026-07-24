# Archive and release policy

Version 3.0 keeps one active implementation:

- `src/python_cal/` — Python behavioral model, calibration, decoder and tests;
- `src/python_cal/run_final_calibration_pipeline.py` — the acceptance entry;
- `docs/` — current design, verification and hardware-mapping documents;
- `src/python_cal/validation_results/final_pipeline/` — one signed release run.

Older Verilog-A, RTL, Spectre, alternate Python models, generated reports and
review workspaces are not duplicated in the active Git tree. They remain
recoverable from Git history and release tags. Local working copies are moved
under the ignored `.artifacts/` directory before release.

The directory `2026_12bit10Msar` is explicitly excluded from this repository
release. A local copy may exist under `.artifacts/`, but no file from it may be
staged or pushed.

Before a release:

1. run `git status --short` and inspect every untracked path;
2. retain only the current test, documentation, figure and final-run evidence;
3. verify `git ls-files | rg 2026_12bit10Msar` returns no matches;
4. run the regression suite and the 100-seed acceptance pipeline;
5. record the release version in `VERSION`, `pyproject.toml`, `spec.yml`,
   `CHANGELOG.md` and `python_cal.__version__`;
6. tag the accepted commit.
