# Model scope and provenance boundary

## Layer A - Huang paper equations

The paper explicitly provides:

```text
D_plus  = +W + Vos + n_plus
D_minus = -W + Vos + n_minus
W_hat   = mean(D_plus - D_minus) / 2
```

It also provides the `C0...C5` symmetric analog precharge/switching structure and
32 pair averages. It does **not** define this project's terminal bit, exact-tie
policy, Q6 state variables, masks, or wall-plus-residual algorithm.

## Layer B - historical legacy evidence

The 224-pair `calibration_full32_baseline_stdout.log` proves the historical
legacy-direct run produced H1C-R=65.46875 and H32C=2087.5. The current DEC source
has SHA-256 `D91F...CBF0` and defaults to `CENTERED_RESIDUAL_MODE=1`; the historical
log does not carry a matching source hash. Therefore it is a failure-replay input,
not evidence that the current centered source was tested.

## Layer C - engineering candidate

`wall + signed residual` is a project candidate. Python tests may establish its
mathematical properties under explicit quantizer/noise assumptions. Those tests
must not be described as a reproduction of Huang's physical `C0...C5` switching,
nor as Verilog-A verification.

Odd symmetry is an engineering invariant selected to prevent direction-dependent
digital tie bias. It is consistent with the paper's symmetric architecture but is
not quoted as a paper-defined digital quantizer rule.
