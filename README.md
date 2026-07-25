# 12-bit Calibrated Asynchronous SAR ADC 閳?Behavioral Model<br><small>12娴ｅ秵鐗庨崙鍡楃€峰鍌涱劄SAR ADC 閳?鐞涘奔璐熺痪褎膩閸?/small>

[![Version](https://img.shields.io/badge/version-3.1.0-0072B2)](https://github.com/defineiocc02/Behavioral-modeling-of-12bit-calibrated-sar-adc/releases)
[![License](https://img.shields.io/badge/license-MIT-009E73)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-0072B2)](https://www.python.org/)
[![FFT](https://img.shields.io/badge/FFT-coherent%20rectangular-009E73)](docs/MODELING_GUIDE.md)
[![Cal](https://img.shields.io/badge/calibration-Shen%202018%20JSSC-E69F00)](https://ieeexplore.ieee.org/document/8248649)

**[English](#english) | [娑擃厽鏋僝(#chinese)**

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

- All 14 high/low capacitors sample the input 閳?no VCM-masked caps.
- 15 comparator decisions: 14 physical trial/compare/commit + 1 terminal.
- High-segment 8-Cu duplicate provides wide-range redundancy.
- Decoder: **plain P/N calibrated weighted sum with Q2 rounding.**
  No LUT, DP, exception tables, or stateful monotonic clamps.

<p align="center"><img src="docs/assets/figures/fig02_cdac_topology.png" width="800" alt="CDAC topology"></p>

### Calibration

Foreground force-0/force-1 half-difference protocol (Shen 2018 JSSC).

The complete low segment (131 Q0) serves as the seed ruler and is **not
self-calibrated** 閳?the main comparator's ~3 mV offset cannot reliably cover
the lowest bits' backend margin.

```
Calibration order:  H1 閳?H2 閳?H4 閳?H8-R 閳?H8-A 閳?H16 閳?H32
Pairs per target:   128                    (v3.0, down from 512)
Total sub-convs:    7 鑴?4 鑴?128 = 3584    (v3.0, down from 14336)
Dither:             OFF (noise 閳?1 LSB makes it redundant)
```

| Parameter | Original | Current | Rationale |
|-----------|--------|--------|-----------|
| `AVG_PAIRS` | 512 | **128** | Oracle gap saturated by 128; 4鑴?faster |
| `SHEN_DITHER_LSB` | ON (hardcoded) | **OFF** (config) | Redundant when noise 閳?1 LSB + N 閳?32 |
| Divider | 閳?| **right-shift 7** | 128=2閳? no hardware divider needed |

<p align="center"><img src="docs/assets/figures/fig03_weights_and_redundancy.png" width="800" alt="Calibration weights"></p>

### v3.0.0 Results

100-seed Monte Carlo, TSMC 180nm conservative (`锜?= 1%` unit-cap mismatch),
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

| 锜?(MC_SIGMA) | Pre-SNDR | Post-SNDR | Oracle Gap | Verdict |
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

Coherent sampling: signal on bin 1019 (gcd(1019,4096)=1).  No leakage 閳?
rectangular window is correct (ENBW=1 bin).

### Quick Start

```powershell
# Install
python -m pip install -e ".[dev]"

# Run tests
$env:PYTHONPATH = "src"
python -m pytest src/python_cal/tests -q

# One-click calibration debug 閳?
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
| CDAC capacitor array (30 caps) | passive | ~600 娓璵铏?|
| Bottom-plate switches (28鑴?:1 MUX) | ~560 Tr | ~600 娓璵铏?|
| StrongArm comparator | ~24 Tr | ~200 娓璵铏?|
| SAR FSM | ~400 gates | ~1200 娓璵铏?|
| Calibration controller | ~1800 gates | ~4000 娓璵铏?|
| Weighted-sum decoder | ~2000 gates | ~4500 娓璵铏?|
| **Total** | **~4200 gates + ~600 Tr** | **~0.011 mm铏?* |

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
  debug_entry.py         one-click calibration debug 閳?
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

## 娑擃厽鏋?

閸忋劌妯婇崚鍡愨偓浣哥磽濮?split-CDAC SAR ADC 鐞涘奔璐熺痪褎膩閸ㄥ鈧倸瀵橀崥顐ゆ暩閼藉嘲鐣ч幁鎺撶湴鐟欙絻鈧?
P/N 閸掑棔鏅堕悪顒傜彌閻㈤潧顔愭径閬嶅帳閵嗕礁澧犻弲顖涙綀闁插秵鐗庨崙鍡愨偓鍌涙拱妞ゅ湱娲?*閸烆垯绔撮張澶嬫櫏閻?Python 鐞涘奔璐熺痪褏澧楅張?*閵?

> 鐠囦焦宓佺粵澶岄獓: **Python behavioral L2.** 闂堢偞娅犳担鎾额吀缁?PVT閵嗕線娼悧鍫濇禈閸氬簼璞㈤妴渚€娼涵鍛濞村鍣洪妴?

<p align="center"><img src="docs/assets/figures/fig01_model_architecture.png" width="900" alt="濡€崇€烽弸鑸电€?></p>

### 闁夸礁鐣?v3.x CDAC 閹锋挻澧?

濮ｅ繋鏅舵禒鍛▏閻劍鏆ｉ弫鏉垮礋娴ｅ秶鏁哥€瑰箍鈧€?.0.0 閺嬭埖鐎妴?

```text
  妤傛ɑ顔?   32, 16, 8, 8, 4, 2, 1 Cu   = 71 Cu
  濡椼儲甯?                             2 Cu
  娴ｅ孩顔?   32, 16, 8, 4, 2, 2, 1 Cu  = 65 Cu
  閸楁洑鏅堕幀鏄忣吀:                          138 Cu  (552 fF @ Cu=4 fF)
```

閺嶅洨袨閺堝鏅ラ弶鍐櫢 ($H = 67$):

```text
2144, 1072, 536, 536, 268, 134, 67,
  64,   32,  16,   8,   4,   4,  2, 1 缂佸牏顏担?
```

- 閸忋劑鍎?14 娑擃亪鐝?娴ｅ孩顔岄悽闈涱啇閸欏倷绗岄柌鍥ㄧ壉鏉堟挸鍙嗛垾鏂衡偓鏃€妫ょ仦蹇氭杸閻㈤潧顔愰妴?
- 15 濞嗏剝鐦潏鍐ㄦ珤閸掋倕鍠? 14 閻椻晝鎮?trial/compare/commit + 1 缂佸牏顏担宥冣偓?
- 妤傛ɑ顔?8-Cu 閸愭ぞ缍戦幓鎰返婢堆嗗瘱閸ユ潙顔愰柨娆嶁偓?
- 鐟欙絿鐖滈崳? **缁?P/N 閺嶁€冲櫙閺夊啴鍣搁崝鐘虫綀閸?+ Q2 閼稿秴鍙嗛妴?*
  閺?LUT閵嗕焦妫?DP閵嗕焦妫ゅ鍌氱埗鐞涖劊鈧焦妫ら悩鑸碘偓渚€鎸告担宥冣偓?

<p align="center"><img src="docs/assets/figures/fig02_cdac_topology.png" width="800" alt="CDAC 閹锋挻澧?></p>

### 閺嶁€冲櫙

閸撳秵娅?force-0/force-1 閸楀﹤妯婂▔?(Shen 2018 JSSC)閵?

鐎瑰本鏆ｆ担搴㈩唽 (131 Q0) 娴ｆ粈璐熼崠褰掑帳閸╁搫鍣亸鐚寸礉**娑撳秷鍤滈弽鈥冲櫙**閳ユ柡鈧柧瀵屽В鏃囩窛閸?~3 mV offset
閺冪姵纭堕崣顖炴浆鐟曞棛娲婇張鈧担搴″殤娴ｅ秶娈戦崥搴ｎ伂 margin閵?

```
閺嶁€冲櫙妞ゅ搫绨?  H1 閳?H2 閳?H4 閳?H8-R 閳?H8-A 閳?H16 閳?H32
濮ｅ繒娲伴弽鍥ь嚠閺? 128                     (v3.1, 娴?512 闂勫秳缍?
閹鐡欐潪顒佸床:   7 鑴?4 鑴?128 = 3584     (v3.1, 娴?14336 闂勫秳缍?
Dither:    閸忔娊妫?(閸ｎ亜锛?閳?1 LSB 閸楀啿鍟戞担?
```

| 閸欏倹鏆?| v3.0.0 | 瑜版挸澧?| 閻炲棛鏁?|
|------|--------|--------|------|
| `AVG_PAIRS` | 512 | **128** | Oracle gap 閸?128 鐎电懓鎮楁鍗炴嫲; 韫?4 閸?|
| `SHEN_DITHER_LSB` | 瀵偓 (绾剛绱惍? | **閸?* (config) | 閸ｎ亜锛?閳?1 LSB + N 閳?32 閺冭泛鍟戞担?|
| 闂勩倖纭堕崳?| 閳?| **閸欏磭些 7 娴?* | 128=2閳? 閺冪娀娓剁涵顑挎闂勩倖纭堕崳?|

<p align="center"><img src="docs/assets/figures/fig03_weights_and_redundancy.png" width="800" alt="閺嶁€冲櫙閺夊啴鍣?></p>

### v3.0.0 缂佹挻鐏?

100-seed Monte Carlo, TSMC 180nm 娣囨繂鐣ф导鎷岊吀 (`锜?= 1%` 閸楁洑缍呴悽闈涱啇婢堕亶鍘?,
128 鐎? 1 mV RMS 閺嶁€冲櫙閸ｎ亜锛? 閻晛鑸扮粣妤冩祲楠?FFT閵?

| 閹稿洦鐖?| 閺嶁€冲櫙閸?| 閺嶁€冲櫙閸?Q2 | Physical Oracle |
|------|--------:|----------:|----------------:|
| SNDR P50 | 63.73 dB | **74.50 dB** | 74.64 dB |
| ENOB P50 | 10.29 bit | **12.08 bit** | 12.11 bit |
| SFDR P50 | 70.57 dB | 94.29 dB | 96.91 dB |

- 100/100 閺堝鏅ラ弽鈥冲櫙, 0/100 鐠愮喐鏁归惄?
- Oracle gap P50: **0.14 dB**
- DNL peak P95: 0.75 LSB; INL peak P95: 0.80 LSB
- 100/100 闂嗗墎宸遍惍? 閺堚偓婢堆嗙儲閻?= 1

| 锜?(MC_SIGMA) | 閺嶁€冲櫙閸?| 閺嶁€冲櫙閸?| Oracle Gap | 閸掋倕鐣?|
|:------------:|--------:|--------:|----------:|:----:|
| 1% | 63.7 dB | 74.5 dB | 0.14 dB | 闁俺绻?|
| 2% | 50.1 dB | 73.3 dB | 1.34 dB | 闁俺绻?|
| 5% | 42.2 dB | 72.6 dB | 2.05 dB | 闁俺绻?|
| 10% | 36.1 dB | 70.2 dB | 4.47 dB | 娑撳鏅?|
| 20% | 30.2 dB | 50.6 dB | 24.0 dB | 婢惰精瑙?|

閺囨潙顦? [v3.0 閸欐垵绔风拠瀛樻](docs/RELEASE_RESULTS_V3.md),
[鐎圭偤鐛欐總妞炬](src/python_cal/analysis/).

<p align="center"><img src="src/python_cal/analysis/fft_comparison.png" width="900" alt="FFT 鐎佃鐦?></p>

### FFT 閸楀繗顔?

| 閸欏倹鏆?| 閸?|
|------|------:|
| FFT 閻愯鏆?| 4096 |
| 閻╃鍏?bin | 1019 |
| 閻╅晲缍?| 0.123 rad |
| 鏉堟挸鍙嗛獮鍛 | -0.5 dBFS |
| VFS | 濮?seed 閸斻劍鈧焦绁撮柌?|
| 缁愭鍤遍弫?| **閻晛鑸扮粣?(閺冪姷鐛?** |
| clipping | 濮ｅ繑顐兼潻鎰攽閺勬儳绱″Λ鈧弻?|

閻╃鍏遍柌鍥ㄧ壉: 娣団€冲娇缁墽鈥橀拃钘夋躬 bin 1019 (gcd(1019,4096)=1)閵嗗倹妫ゅ▔鍕础閳ユ柡鈧梻鐓╄ぐ銏㈢崶閺勵垱顒滅涵顔炬畱 (ENBW=1 bin)閵?

### 韫囶偊鈧喎绱戞慨?

```powershell
# 鐎瑰顥?
python -m pip install -e ".[dev]"

# 鏉╂劘顢戝ù瀣槸
$env:PYTHONPATH = "src"
python -m pytest src/python_cal/tests -q

# 娑撯偓闁款喗鐗庨崙鍡氱殶鐠?閳?
python src/python_cal/debug_entry.py
python src/python_cal/debug_entry.py --pairs 64 --mc 0.02
python src/python_cal/debug_entry.py --noise 0.5 --pairs 32

# 鐎瑰本鏆ｇ粻锛勫殠 (100 seeds)
python src/python_cal/run_final_calibration_pipeline.py

# 鐎圭偤鐛欐總妞炬
python src/python_cal/analysis/generate_fft_comparison.py
python src/python_cal/analysis/generate_multisigma_fft.py
```

### 绾兛娆㈡径宥嗘絽鎼?

| 濡€虫健 | 闂傘劍鏆?閺呮湹缍嬬粻?| 闂堛垻袧 |
|------|:----------:|-----:|
| CDAC 閻㈤潧顔愰梼闈涘灙 (30娑? | 鐞氼偄濮╅崳銊ゆ | ~600 娓璵铏?|
| 鎼存洘婢樺鈧崗?(28鑴?:1 MUX) | ~560 Tr | ~600 娓璵铏?|
| StrongArm 濮ｆ棁绶濋崳?| ~24 Tr | ~200 娓璵铏?|
| SAR FSM | ~400 闂?| ~1200 娓璵铏?|
| 閺嶁€冲櫙閹貉冨煑閸?| ~1800 闂?| ~4000 娓璵铏?|
| 閸旂姵娼堥崪宀冃掗惍浣告珤 | ~2000 闂?| ~4500 娓璵铏?|
| **閹槒顓?* | **~4200 闂?+ ~600 Tr** | **~0.011 mm铏?* |

鐎瑰本鏆ｉ崚鍡樼€? [DELIVERY.md](src/python_cal/DELIVERY.md)

### 娑撹桨缍嶆稉宥囨暏閺?95-Cu CDAC ?

```text
閺?  1,2,4,6,10,16,24 Cu (娴ｅ孩顔? | 1 Cu (濡椼儲甯? | 1,2,4,8,16 Cu (妤傛ɑ顔?
閺?  閺佸瓨鏆?138 Cu
```

閸?0.5% 婢堕亶鍘? 1000-seed 閻焦婀扮€孤ゎ吀:
- 閺? 缂傝櫣鐖?P50=22, 閺堚偓閸?84; 閺堚偓婢堆嗙儲閻焦娓堕崸?9
- 閺? **1000/1000 闂嗗墎宸遍惍? 閺堚偓婢堆嗙儲閻礁顫愮紒?1**

<p align="center"><img src="docs/assets/figures/fig09_cdac_candidate_comparison.png" width="700" alt="CDAC 鐎佃鐦?></p>

### 閻╊喖缍嶇紒鎾寸€?

```text
src/python_cal/
  config.py              缂佺喍绔撮柊宥囩枂閸忋儱褰?
  debug_entry.py         娑撯偓闁款喗鐗庨崙鍡氱殶鐠?閳?
  DELIVERY.md            闁帊姘﹂弬鍥ㄣ€?
  topology/              閺佸瓨鏆?CDAC 閹锋挻澧ゆ稉搴＄磻閸忓磭濮搁幀?
  physical/              閻絻宓庣€瑰牊浜藉Ч鍌澬掗崳?
  comparator/            閸斻劍鈧焦鐦潏鍐ㄦ珤濡€崇€?
  async_control/         瀵倹顒?SAR 閹烩剝澧?
  calibration/           Shen 2018 force-0/force-1 閺嶁€冲櫙
  decode/                缁绢垰濮為弶鍐ㄦ嫲鐟欙絿鐖滈崳?
  validation/            FFT 娑撳骸褰叉潏鍓х垳閺堫剙顓哥拋?
  analysis/              鐎圭偤鐛欓懘姘拱娑撳骸娴樼悰?
  tests/                 閸ョ偛缍婂ù瀣槸婵傛ぞ娆?
docs/
  MODELING_GUIDE.md, VALIDATION_STATUS.md, RELEASE_RESULTS_V3.md, ...
```

### 瀵洜鏁?

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

閺嶁€冲櫙閸楀繗顔呴崺杞扮艾: Shen et al., "A 16-bit 16-MS/s SAR ADC With On-Chip
Calibration in 55-nm CMOS," *IEEE JSSC*, vol. 53, no. 4,
pp. 1147&ndash;1154, Apr. 2018.

### AI 鏉堝懎濮竟鐗堟

閺堫剟銆嶉惄顔诲▏閻?AI 鏉堝懎濮紓鏍垳瀹搞儱鍙垮鈧崣鎴礉閸栧懏瀚?CODEX 娑?Trae (DeepSeek)閵?
閹碘偓閺?AI 閻㈢喐鍨氭禒锝囩垳瀹歌尙绮℃禍鍝勪紣鐎光剝鐓℃稉搴ㄧ崣鐠囦降鈧?

### 瀵偓濠ф劘顔忛崣?

[MIT](LICENSE)
