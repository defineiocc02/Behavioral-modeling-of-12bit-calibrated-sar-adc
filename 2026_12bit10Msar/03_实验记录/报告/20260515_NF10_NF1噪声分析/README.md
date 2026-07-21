# 2026-05-15 NF10/NF1 noise analysis package

This folder archives the NF=10 / noisescale=10 sampling-noise stress run and the NF=1 / noisescale=1 full-noise run for the updated 12-bit 50 MS/s SAR ADC structure.

## Contents

- `NF10_NF1_combined_analysis_20260515.pdf`: PDF compiled from LaTeX with MiKTeX `xelatex`.
- `NF10_NF1_combined_analysis_20260515.tex`: reproducible LaTeX report. Figures are generated with `pgfplots`; it does not require Inkscape or shell escape.
- `NF10_NF1_combined_analysis_20260515.md`: Markdown report.
- `data/`: original and derived CSV data. Keep NF=10 and NF=1 raw files separate.
- `figures/`: SVG figures generated during analysis.
- `tools/`: report generation scripts.

## Compile

From this directory:

```powershell
& 'C:\Users\Administrator\AppData\Local\Programs\MiKTeX\miktex\bin\x64\xelatex.exe' -interaction=nonstopmode -halt-on-error 'NF10_NF1_combined_analysis_20260515.tex'
& 'C:\Users\Administrator\AppData\Local\Programs\MiKTeX\miktex\bin\x64\xelatex.exe' -interaction=nonstopmode -halt-on-error 'NF10_NF1_combined_analysis_20260515.tex'
```

The two passes stabilize links and longtable widths.

## Data guardrails

- NF=10 data source: `ExplorerRun.0`, noisescale=10, points 1-20 complete with 0 Spectre errors.
- NF=1 data source: latest `ExplorerRun.0`, noisescale=1, points 1-20 complete with 0 Spectre errors.
- Do not mix these data with older Interactive runs or old dragged netlists.
- Analyze each process corner independently: Nominal, C0, C1, fs, sf. Averages are not primary conclusions.
