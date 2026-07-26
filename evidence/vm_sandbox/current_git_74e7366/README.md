# VM standalone VA/RTL evidence

This directory freezes the small, reviewable evidence package from
`/home/meow/jxy/trae_sandbox/current_git_74e7366` on 2026-07-26. The sandbox
used the repository design sources associated with commit `74e7366`; later
documentation-only commits do not change those source hashes.

The authoritative status is `reports/run_status.txt`:

- StrongARM comparator Verilog-A: PASS, Spectre 0 errors and 0 warnings;
- split-CDAC Verilog-A: PASS, Spectre 0 errors and 4 `VACOMP-1116` warnings;
- calibration RTL self-check: PASS at 4065 ns;
- lower-SAR RTL self-check: PASS at 705 ns;
- `cal_top` compile/elaborate: PASS.

The four CDAC warnings are retained in `reports/postpatch_evidence.txt`. They
come from applying `transition()` to continuous expressions at
`va/cdac_behavioral.va` lines 153--156. The smoke run is valid, but this is an
open modeling-semantics item before AMS integration.

`reports/source_manifest.sha256` binds the uploaded source and task-owned
testbenches to exact file content. The compact Xcelium logs are retained. Full
Spectre logs and the combined console transcript are intentionally not
published because they include machine and license-server identifiers; the
diagnostic extract preserves the relevant version, warning, error, and PASS
evidence without those identifiers.

The run wrote only inside the standalone sandbox and its dated temporary
evidence directory. `reports/postpatch_evidence.txt` records zero files written
under the protected active project `/home/meow/jxy/12bit_50M_SAR` after the run
marker.

Regenerate the deterministic file manifest with:

```powershell
python scripts\generate_vm_evidence_manifest.py
```

This evidence proves standalone VA compilation/smoke behavior and the stated
RTL contracts. It does not prove full ADC AMS integration, PVT, transistor
performance, post-layout performance, or silicon readiness.
