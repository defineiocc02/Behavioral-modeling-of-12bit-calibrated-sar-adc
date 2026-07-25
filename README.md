# 12-bit Calibrated Asynchronous SAR ADC 鈥?Behavioral Model<br><small>12浣嶆牎鍑嗗瀷寮傛SAR ADC 鈥?琛屼负绾фā鍨?/small>

[![Version](https://img.shields.io/badge/version-3.1.0-0072B2)](https://github.com/defineiocc02/Behavioral-modeling-of-12bit-calibrated-sar-adc/releases)
[![License](https://img.shields.io/badge/license-MIT-009E73)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-0072B2)](https://www.python.org/)
[![FFT](https://img.shields.io/badge/FFT-coherent%20rectangular-009E73)](docs/MODELING_GUIDE.md)
[![Cal](https://img.shields.io/badge/calibration-Shen%202018%20JSSC-E69F00)](https://ieeexplore.ieee.org/document/8248649)

**[English](#english) | [涓枃](#chinese)**

---

<a id="english"></a>

## English

Fully-differential, asynchronous split-CDAC SAR ADC behavioral model with
charge-conservation solving, P/N-side independent capacitor mismatch, and
foreground weight calibration.  This is the **only active Python behavioral
version** of the project.

> Evidence level: **Python behavioral L2.**  Results are not transistor-level
> PVT, post-layout, or silicon measurements.

<p align="center"><img src="docs/assets/figures/fig01_model_architecture.png" width="900" alt="Model architecture"></p>

### Locked v3.x CDAC Topology

Per-side integer unit capacitors only.  Identical for all v3.x.

```text
  High segment:  32, 16, 8, 8, 4, 2, 1 Cu   = 71 Cu
  Bridge:                                   2 Cu
  Low segment:   32, 16, 8, 4, 2, 2, 1 Cu  = 65 Cu
  Total per side:                          138 Cu  (552 fF @ Cu=4 fF)
```

Nominal effective weights ($H = 67$):

```text
2144, 1072, 536, 536, 268, 134, 67,
  64,   32,  16,   8,   4,   4,  2, 1 terminal
```

- All 14 high/low capacitors sample the input 鈥?no VCM-masked caps.
- 15 comparator decisions: 14 physical trial/compare/commit + 1 terminal.
- High-segment 8-Cu duplicate provides wide-range redundancy.
- Decoder: **plain P/N calibrated weighted sum with Q2 rounding.**
  No LUT, DP, exception tables, or stateful monotonic clamps.

<p align="center"><img src="docs/assets/figures/fig02_cdac_topology.png" width="800" alt="CDAC topology"></p>

### Calibration

Foreground force-0/force-1 half-difference protocol (Shen 2018 JSSC).

The complete low segment (131 Q0) serves as the seed ruler and is **not
self-calibrated** 鈥?the main comparator's ~3 mV offset cannot reliably cover
the lowest bits' backend margin.

```
Calibration order:  H1 鈫?H2 鈫?H4 鈫?H8-R 鈫?H8-A 鈫?H16 鈫?H32
Pairs per target:   128                    (v3.1, down from 512)
Total sub-convs:    7 脳 4 脳 128 = 3584    (v3.1, down from 14336)
Dither:             OFF (noise 鈮?1 LSB makes it redundant)
```

| Parameter | Original | Current | Rationale |
|-----------|--------|--------|-----------|
| `AVG_PAIRS` | 512 | **128** | Oracle gap saturated by 128; 4脳 faster |
| `SHEN_DITHER_LSB` | ON (hardcoded) | **OFF** (config) | Redundant when noise 鈮?1 LSB + N 鈮?32 |
| Divider | 鈥?| **right-shift 7** | 128=2鈦? no hardware divider needed |

<p align="center"><img src="docs/assets/figures/fig03_weights_and_redundancy.png" width="800" alt="Calibration weights"></p>

### v3.0.0 Results

100-seed Monte Carlo, TSMC 180nm conservative (`蟽 = 1%` unit-cap mismatch),
128 pairs, 1 mV RMS calibration noise, rectangular-window coherent FFT.

| Metric | Pre-Cal | Post-Cal Q2 | Physical Oracle |
|--------|--------:|------------:|----------------:|
| SNDR P50 | 63.73 dB | **74.50 dB** | 74.64 dB |
| ENOB P50 | 10.29 bit | **12.08 bit** | 12.11 bit |
| SFDR P50 | 70.57 dB | 94.29 dB | 96.91 dB |

- 100/100 seeds calibrated, 0/100 negative gain
- Oracle gap P50: **0.14 dB**
- DNL peak P95: 0.75 LSB; INL peak P95: 0.80 LSB
- 100/100 zero missing codes, max jump = 1

| 蟽 (MC_SIGMA) | Pre-SNDR | Post-SNDR | Oracle Gap | Verdict |
|:------------:|--------:|--------:|----------:|:--------:|
| 1% | 63.7 dB | 74.5 dB | 0.14 dB | Pass |
| 2% | 50.1 dB | 73.3 dB | 1.34 dB | Pass |
| 5% | 42.2 dB | 72.6 dB | 2.05 dB | Pass |
| 10% | 36.1 dB | 70.2 dB | 4.47 dB | Marginal |
| 20% | 30.2 dB | 50.6 dB | 24.0 dB | Fail |

More: [v3.0 release notes](docs/RELEASE_RESULTS_V3.md),
[analysis suite](src/python_cal/analysis/).

<p align="center"><img src="src/python_cal/analysis/fft_comparison.png" width="900" alt="FFT comparison"></p>

### FFT Protocol

| Parameter | Value |
|-----------|------:|
| FFT points | 4096 |
| Coherent bin | 1019 |
| Phase | 0.123 rad |
| Input amplitude | -0.5 dBFS |
| VFS | per-seed dynamic measurement |
| Window | **Rectangular** |
| Clipping | explicit per-run check |

Coherent sampling: signal on bin 1019 (gcd(1019,4096)=1).  No leakage 鈥?
rectangular window is correct (ENBW=1 bin).

### Quick Start

```powershell
# Install
python -m pip install -e ".[dev]"

# Run tests
$env:PYTHONPATH = "src"
python -m pytest src/python_cal/tests -q

# One-click calibration debug 鈽?
python src/python_cal/debug_entry.py
python src/python_cal/debug_entry.py --pairs 64 --mc 0.02
python src/python_cal/debug_entry.py --noise 0.5 --pairs 32

# Full pipeline (100 seeds)
python src/python_cal/run_final_calibration_pipeline.py

# Experiment suite
python src/python_cal/analysis/generate_fft_comparison.py
python src/python_cal/analysis/generate_multisigma_fft.py
```

### Hardware Complexity

| Block | Gates / Tr. | Area |
|-------|:----------:|-----:|
| CDAC capacitor array (30 caps) | passive | ~600 渭m虏 |
| Bottom-plate switches (28脳4:1 MUX) | ~560 Tr | ~600 渭m虏 |
| StrongArm comparator | ~24 Tr | ~200 渭m虏 |
| SAR FSM | ~400 gates | ~1200 渭m虏 |
| Calibration controller | ~1800 gates | ~4000 渭m虏 |
| Weighted-sum decoder | ~2000 gates | ~4500 渭m虏 |
| **Total** | **~4200 gates + ~600 Tr** | **~0.011 mm虏** |

Full analysis: [DELIVERY.md](src/python_cal/DELIVERY.md)

### Why Not the Old 95-Cu CDAC?

```text
Old:  1,2,4,6,10,16,24 Cu (low) | 1 Cu (bridge) | 1,2,4,8,16 Cu (high)
New:  integer 138 Cu
```

Same 0.5% mismatch, 1000-seed codebook audit:
- Old: missing codes P50=22, worst=84; max jump worst=9
- New: **1000/1000 zero missing codes, max jump always 1**

<p align="center"><img src="docs/assets/figures/fig09_cdac_candidate_comparison.png" width="700" alt="CDAC comparison"></p>

### Directory

```text
src/python_cal/
  config.py              single-source configuration
  debug_entry.py         one-click calibration debug 鈽?
  DELIVERY.md            handover document
  topology/              integer CDAC and explicit switch states
  physical/              charge-conservation solver
  comparator/            dynamic comparator model
  async_control/         asynchronous SAR handshake
  calibration/           Shen 2018 force-0/force-1 calibration
  decode/                plain weighted-sum decoder
  validation/            FFT and reachable-codebook audits
  analysis/              experiment scripts + figures
  tests/                 regression suite
docs/
  MODELING_GUIDE.md, VALIDATION_STATUS.md, RELEASE_RESULTS_V3.md, ...
```

### Citation

```bibtex
@misc{sar12_cal_behavioral_2026,
  author       = {{SAR ADC Calibration Project Contributors}},
  title        = {12-bit Calibrated Asynchronous SAR ADC -- Behavioral Model},
  year         = {2026},
  version      = {3.1.0},
  url          = {https://github.com/defineiocc02/Behavioral-modeling-of-12bit-calibrated-sar-adc},
  note         = {Python behavioral model, evidence level L2}
}
```

Calibration protocol: Shen et al., "A 16-bit 16-MS/s SAR ADC With
On-Chip Calibration in 55-nm CMOS," *IEEE JSSC*, vol. 53, no. 4,
pp. 1147&ndash;1154, Apr. 2018.

### AI Assistance Notice

This project was developed with AI-assisted coding tools, including
CODEX and Trae (DeepSeek).  All AI-generated code has been
reviewed and validated by human contributors.

### License

[MIT](LICENSE)

---

<a id="chinese"></a>

## 涓枃

鍏ㄥ樊鍒嗐€佸紓姝?split-CDAC SAR ADC 琛屼负绾фā鍨嬨€傚寘鍚數鑽峰畧鎭掓眰瑙ｃ€?
P/N 鍒嗕晶鐙珛鐢靛澶遍厤銆佸墠鏅潈閲嶆牎鍑嗐€傛湰椤圭洰**鍞竴鏈夋晥鐨?Python 琛屼负绾х増鏈?*銆?

> 璇佹嵁绛夌骇: **Python behavioral L2.** 闈炴櫠浣撶绾?PVT銆侀潪鐗堝浘鍚庝豢銆侀潪纭呯墖娴嬮噺銆?

<p align="center"><img src="docs/assets/figures/fig01_model_architecture.png" width="900" alt="妯″瀷鏋舵瀯"></p>

### 閿佸畾 v3.x CDAC 鎷撴墤

姣忎晶浠呬娇鐢ㄦ暣鏁板崟浣嶇數瀹广€倂3.0.0 鏋舵瀯銆?

```text
  楂樻:   32, 16, 8, 8, 4, 2, 1 Cu   = 71 Cu
  妗ユ帴:                             2 Cu
  浣庢:   32, 16, 8, 4, 2, 2, 1 Cu  = 65 Cu
  鍗曚晶鎬昏:                          138 Cu  (552 fF @ Cu=4 fF)
```

鏍囩О鏈夋晥鏉冮噸 ($H = 67$):

```text
2144, 1072, 536, 536, 268, 134, 67,
  64,   32,  16,   8,   4,   4,  2, 1 缁堢浣?
```

- 鍏ㄩ儴 14 涓珮/浣庢鐢靛鍙備笌閲囨牱杈撳叆鈥斺€旀棤灞忚斀鐢靛銆?
- 15 娆℃瘮杈冨櫒鍒ゅ喅: 14 鐗╃悊 trial/compare/commit + 1 缁堢浣嶃€?
- 楂樻 8-Cu 鍐椾綑鎻愪緵澶ц寖鍥村閿欍€?
- 瑙ｇ爜鍣? **绾?P/N 鏍″噯鏉冮噸鍔犳潈鍜?+ Q2 鑸嶅叆銆?*
  鏃?LUT銆佹棤 DP銆佹棤寮傚父琛ㄣ€佹棤鐘舵€侀挸浣嶃€?

<p align="center"><img src="docs/assets/figures/fig02_cdac_topology.png" width="800" alt="CDAC 鎷撴墤"></p>

### 鏍″噯

鍓嶆櫙 force-0/force-1 鍗婂樊娉?(Shen 2018 JSSC)銆?

瀹屾暣浣庢 (131 Q0) 浣滀负鍖归厤鍩哄噯灏猴紝**涓嶈嚜鏍″噯**鈥斺€斾富姣旇緝鍣?~3 mV offset
鏃犳硶鍙潬瑕嗙洊鏈€浣庡嚑浣嶇殑鍚庣 margin銆?

```
鏍″噯椤哄簭:  H1 鈫?H2 鈫?H4 鈫?H8-R 鈫?H8-A 鈫?H16 鈫?H32
姣忕洰鏍囧鏁? 128                     (v3.1, 浠?512 闄嶄綆)
鎬诲瓙杞崲:   7 脳 4 脳 128 = 3584     (v3.1, 浠?14336 闄嶄綆)
Dither:    鍏抽棴 (鍣０ 鈮?1 LSB 鍗冲啑浣?
```

| 鍙傛暟 | v3.0.0 | 褰撳墠 | 鐞嗙敱 |
|------|--------|--------|------|
| `AVG_PAIRS` | 512 | **128** | Oracle gap 鍦?128 瀵瑰悗楗卞拰; 蹇?4 鍊?|
| `SHEN_DITHER_LSB` | 寮€ (纭紪鐮? | **鍏?* (config) | 鍣０ 鈮?1 LSB + N 鈮?32 鏃跺啑浣?|
| 闄ゆ硶鍣?| 鈥?| **鍙崇Щ 7 浣?* | 128=2鈦? 鏃犻渶纭欢闄ゆ硶鍣?|

<p align="center"><img src="docs/assets/figures/fig03_weights_and_redundancy.png" width="800" alt="鏍″噯鏉冮噸"></p>

### v3.0.0 缁撴灉

100-seed Monte Carlo, TSMC 180nm 淇濆畧浼拌 (`蟽 = 1%` 鍗曚綅鐢靛澶遍厤),
128 瀵? 1 mV RMS 鏍″噯鍣０, 鐭╁舰绐楃浉骞?FFT銆?

| 鎸囨爣 | 鏍″噯鍓?| 鏍″噯鍚?Q2 | Physical Oracle |
|------|--------:|----------:|----------------:|
| SNDR P50 | 63.73 dB | **74.50 dB** | 74.64 dB |
| ENOB P50 | 10.29 bit | **12.08 bit** | 12.11 bit |
| SFDR P50 | 70.57 dB | 94.29 dB | 96.91 dB |

- 100/100 鏈夋晥鏍″噯, 0/100 璐熸敹鐩?
- Oracle gap P50: **0.14 dB**
- DNL peak P95: 0.75 LSB; INL peak P95: 0.80 LSB
- 100/100 闆剁己鐮? 鏈€澶ц烦鐮?= 1

| 蟽 (MC_SIGMA) | 鏍″噯鍓?| 鏍″噯鍚?| Oracle Gap | 鍒ゅ畾 |
|:------------:|--------:|--------:|----------:|:----:|
| 1% | 63.7 dB | 74.5 dB | 0.14 dB | 閫氳繃 |
| 2% | 50.1 dB | 73.3 dB | 1.34 dB | 閫氳繃 |
| 5% | 42.2 dB | 72.6 dB | 2.05 dB | 閫氳繃 |
| 10% | 36.1 dB | 70.2 dB | 4.47 dB | 涓寸晫 |
| 20% | 30.2 dB | 50.6 dB | 24.0 dB | 澶辫触 |

鏇村: [v3.0 鍙戝竷璇存槑](docs/RELEASE_RESULTS_V3.md),
[瀹為獙濂椾欢](src/python_cal/analysis/).

<p align="center"><img src="src/python_cal/analysis/fft_comparison.png" width="900" alt="FFT 瀵规瘮"></p>

### FFT 鍗忚

| 鍙傛暟 | 鍊?|
|------|------:|
| FFT 鐐规暟 | 4096 |
| 鐩稿共 bin | 1019 |
| 鐩镐綅 | 0.123 rad |
| 杈撳叆骞呭害 | -0.5 dBFS |
| VFS | 姣?seed 鍔ㄦ€佹祴閲?|
| 绐楀嚱鏁?| **鐭╁舰绐?(鏃犵獥)** |
| clipping | 姣忔杩愯鏄惧紡妫€鏌?|

鐩稿共閲囨牱: 淇″彿绮剧‘钀藉湪 bin 1019 (gcd(1019,4096)=1)銆傛棤娉勬紡鈥斺€旂煩褰㈢獥鏄纭殑 (ENBW=1 bin)銆?

### 蹇€熷紑濮?

```powershell
# 瀹夎
python -m pip install -e ".[dev]"

# 杩愯娴嬭瘯
$env:PYTHONPATH = "src"
python -m pytest src/python_cal/tests -q

# 涓€閿牎鍑嗚皟璇?鈽?
python src/python_cal/debug_entry.py
python src/python_cal/debug_entry.py --pairs 64 --mc 0.02
python src/python_cal/debug_entry.py --noise 0.5 --pairs 32

# 瀹屾暣绠＄嚎 (100 seeds)
python src/python_cal/run_final_calibration_pipeline.py

# 瀹為獙濂椾欢
python src/python_cal/analysis/generate_fft_comparison.py
python src/python_cal/analysis/generate_multisigma_fft.py
```

### 纭欢澶嶆潅搴?

| 妯″潡 | 闂ㄦ暟/鏅朵綋绠?| 闈㈢Н |
|------|:----------:|-----:|
| CDAC 鐢靛闃靛垪 (30涓? | 琚姩鍣ㄤ欢 | ~600 渭m虏 |
| 搴曟澘寮€鍏?(28脳4:1 MUX) | ~560 Tr | ~600 渭m虏 |
| StrongArm 姣旇緝鍣?| ~24 Tr | ~200 渭m虏 |
| SAR FSM | ~400 闂?| ~1200 渭m虏 |
| 鏍″噯鎺у埗鍣?| ~1800 闂?| ~4000 渭m虏 |
| 鍔犳潈鍜岃В鐮佸櫒 | ~2000 闂?| ~4500 渭m虏 |
| **鎬昏** | **~4200 闂?+ ~600 Tr** | **~0.011 mm虏** |

瀹屾暣鍒嗘瀽: [DELIVERY.md](src/python_cal/DELIVERY.md)

### 涓轰綍涓嶇敤鏃?95-Cu CDAC ?

```text
鏃?  1,2,4,6,10,16,24 Cu (浣庢) | 1 Cu (妗ユ帴) | 1,2,4,8,16 Cu (楂樻)
鏂?  鏁存暟 138 Cu
```

鍚?0.5% 澶遍厤, 1000-seed 鐮佹湰瀹¤:
- 鏃? 缂虹爜 P50=22, 鏈€鍧?84; 鏈€澶ц烦鐮佹渶鍧?9
- 鏂? **1000/1000 闆剁己鐮? 鏈€澶ц烦鐮佸缁?1**

<p align="center"><img src="docs/assets/figures/fig09_cdac_candidate_comparison.png" width="700" alt="CDAC 瀵规瘮"></p>

### 鐩綍缁撴瀯

```text
src/python_cal/
  config.py              缁熶竴閰嶇疆鍏ュ彛
  debug_entry.py         涓€閿牎鍑嗚皟璇?鈽?
  DELIVERY.md            閫掍氦鏂囨。
  topology/              鏁存暟 CDAC 鎷撴墤涓庡紑鍏崇姸鎬?
  physical/              鐢佃嵎瀹堟亽姹傝В鍣?
  comparator/            鍔ㄦ€佹瘮杈冨櫒妯″瀷
  async_control/         寮傛 SAR 鎻℃墜
  calibration/           Shen 2018 force-0/force-1 鏍″噯
  decode/                绾姞鏉冨拰瑙ｇ爜鍣?
  validation/            FFT 涓庡彲杈剧爜鏈璁?
  analysis/              瀹為獙鑴氭湰涓庡浘琛?
  tests/                 鍥炲綊娴嬭瘯濂椾欢
docs/
  MODELING_GUIDE.md, VALIDATION_STATUS.md, RELEASE_RESULTS_V3.md, ...
```

### 寮曠敤

```bibtex
@misc{sar12_cal_behavioral_2026,
  author       = {{SAR ADC Calibration Project Contributors}},
  title        = {12-bit Calibrated Asynchronous SAR ADC -- Behavioral Model},
  year         = {2026},
  version      = {3.1.0},
  url          = {https://github.com/defineiocc02/Behavioral-modeling-of-12bit-calibrated-sar-adc},
  note         = {Python behavioral model, evidence level L2}
}
```

鏍″噯鍗忚鍩轰簬: Shen et al., "A 16-bit 16-MS/s SAR ADC With On-Chip
Calibration in 55-nm CMOS," *IEEE JSSC*, vol. 53, no. 4,
pp. 1147&ndash;1154, Apr. 2018.

### AI 杈呭姪澹版槑

鏈」鐩娇鐢?AI 杈呭姪缂栫爜宸ュ叿寮€鍙戯紝鍖呮嫭 CODEX 涓?Trae (DeepSeek)銆?
鎵€鏈?AI 鐢熸垚浠ｇ爜宸茬粡浜哄伐瀹℃煡涓庨獙璇併€?

### 寮€婧愯鍙?

[MIT](LICENSE)
