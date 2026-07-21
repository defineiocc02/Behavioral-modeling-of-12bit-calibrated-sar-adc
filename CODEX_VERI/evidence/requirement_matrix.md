# Python-stage requirement matrix

| ID | Requirement | Authoritative evidence | Gate |
|---|---|---|---|
| P01 | Huang equations (4.17)-(4.19) are implemented without terminal or wall assumptions | unit tests plus frozen equation trace | mandatory |
| P02 | `Q(-x) = -Q(x)` including exact half-LSB boundaries | exhaustive boundary test | mandatory |
| P03 | Trial exact tie terminates with no terminal increment | directed trace test | mandatory |
| P04 | H1C-A and H1C-R both recover 65 in the ideal centered model | recursive ideal test | mandatory |
| P05 | All seven ideal weights recover exactly in Q6 without exceeding the declared 127 LSB residual reach | recursive ideal and saturation tests | mandatory |
| P06 | Legacy log has exactly one record for every target 0-6 and pair 0-31; DIFF is internally consistent; all target means match | strict log parser, frozen hash, and seven-target replay table | mandatory |
| P07 | Legacy recursive propagation replays H32C=2087.5 | recursive replay test | mandatory |
| P08 | Constant comparator offset cancels in the unquantized signed estimator | offset sweep test | mandatory |
| P09 | Random error scales approximately as N^-1/2 without hiding excessive bias or variance | >=2000-trial Monte Carlo, fitted slope, bias bound, variance-ratio bound, simultaneous CI | mandatory |
| P10 | Single-stage physical perturbation has controlled sensitivity | finite-difference sensitivity matrix | mandatory |
| P11 | Every numerical conclusion is bound to passing unit tests, complete configuration, source/test/report hashes, CSV/JSON data, and fixed seeds | schema-v2 run manifest | mandatory |
| P12 | Independent reviewer finds no unresolved critical Python-stage issue | signed review record | mandatory |
| P13 | Historical legacy logs are not attributed to the current centered-source hash | provenance audit | mandatory |
| P14 | Huang paper model and wall-plus-signed engineering candidate remain separate | model-scope audit | mandatory |
| P15 | Signed half-difference and exact negative-magnitude representation agree sample by sample | representation equivalence test | mandatory |
| P16 | Deterministic N=1 and N=32 traces agree when noise/dither are absent | repeat determinism test | mandatory |
| P17 | H1C-R causal ablation removes the legacy recursive error chain | injected-delta test | mandatory |
| P18 | Direct and centered timing counts are not mixed | counting oracle: 448 frames, 4480 vs 3584 decisions | mandatory |
| P19 | Candidate A/B improvement is material and statistically supported | RMSE-ratio threshold and paired MSE-improvement 95% CI | mandatory |

Passing Python does not prove Verilog-A timing, CDAC settling, comparator reset,
metastability, PVT, or physical implementation. Those belong to the later VA gate.
