# 12-bit Calibrated Asynchronous SAR ADC 闁?Behavioral Model<br><small>12濞达絽绉甸悧搴ㄥ礄閸℃鈧嘲顕ｉ崒娑卞妱SAR ADC 闁?閻炴稑濂旂拹鐔虹棯瑜庤啯闁?/small>

[![Version](https://img.shields.io/badge/version-3.1.0-0072B2)](https://github.com/defineiocc02/Behavioral-modeling-of-12bit-calibrated-sar-adc/releases)
[![License](https://img.shields.io/badge/license-MIT-009E73)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-0072B2)](https://www.python.org/)
[![FFT](https://img.shields.io/badge/FFT-coherent%20rectangular-009E73)](docs/MODELING_GUIDE.md)
[![Cal](https://img.shields.io/badge/calibration-Shen%202018%20JSSC-E69F00)](https://ieeexplore.ieee.org/document/8248649)

**[English](#english) | [濞戞搩鍘介弸鍍?#chinese)**

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

- All 14 high/low capacitors sample the input 闁?no VCM-masked caps.
- 15 comparator decisions: 14 physical trial/compare/commit + 1 terminal.
- High-segment 8-Cu duplicate provides wide-range redundancy.
- Decoder: **plain P/N calibrated weighted sum with Q2 rounding.**
  No LUT, DP, exception tables, or stateful monotonic clamps.

<p align="center"><img src="docs/assets/figures/fig02_cdac_topology.png" width="800" alt="CDAC topology"></p>

### Calibration

Foreground force-0/force-1 half-difference protocol (Shen 2018 JSSC).

The complete low segment (131 Q0) serves as the seed ruler and is **not
self-calibrated** 闁?the main comparator's ~3 mV offset cannot reliably cover
the lowest bits' backend margin.

```
Calibration order:  H1 闁?H2 闁?H4 闁?H8-R 闁?H8-A 闁?H16 闁?H32
Pairs per target:   128                    (v3.0, down from 512)
Total sub-convs:    7 閼?4 閼?128 = 3584    (v3.0, down from 14336)
Dither:             OFF (noise 闁?1 LSB makes it redundant)
```

| Parameter | Original | Current | Rationale |
|-----------|--------|--------|-----------|
| `AVG_PAIRS` | 512 | **128** | Oracle gap saturated by 128; 4閼?faster |
| `SHEN_DITHER_LSB` | ON (hardcoded) | **OFF** (config) | Redundant when noise 闁?1 LSB + N 闁?32 |
| Divider | 闁?| **right-shift 7** | 128=2闁? no hardware divider needed |

<p align="center"><img src="docs/assets/figures/fig03_weights_and_redundancy.png" width="800" alt="Calibration weights"></p>

### v3.0.0 Results

100-seed Monte Carlo, TSMC 180nm conservative (`閿?= 1%` unit-cap mismatch),
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

| 閿?(MC_SIGMA) | Pre-SNDR | Post-SNDR | Oracle Gap | Verdict |
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

Coherent sampling: signal on bin 1019 (gcd(1019,4096)=1).  No leakage 闁?
rectangular window is correct (ENBW=1 bin).

### Quick Start

```powershell
# Install
python -m pip install -e ".[dev]"

# Run tests
$env:PYTHONPATH = "src"
python -m pytest src/python_cal/tests -q

# One-click calibration debug 闁?
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
| CDAC capacitor array (30 caps) | passive | ~600 濞撶挼閾?|
| Bottom-plate switches (28閼?:1 MUX) | ~560 Tr | ~600 濞撶挼閾?|
| StrongArm comparator | ~24 Tr | ~200 濞撶挼閾?|
| SAR FSM | ~400 gates | ~1200 濞撶挼閾?|
| Calibration controller | ~1800 gates | ~4000 濞撶挼閾?|
| Weighted-sum decoder | ~2000 gates | ~4500 濞撶挼閾?|
| **Total** | **~4200 gates + ~600 Tr** | **~0.011 mm閾?* |

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
  debug_entry.py         one-click calibration debug 闁?
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

## 濞戞搩鍘介弸?

闁稿繈鍔屽Ο濠囧礆閸℃劏鍋撴担鍝ョ＝婵?split-CDAC SAR ADC 閻炴稑濂旂拹鐔虹棯瑜庤啯闁搞劌顑冮埀顒€鍊哥€垫﹢宕ラ銈嗘毄闁艰棄鍢查悾褔骞侀幒鎾舵勾閻熸瑱绲婚埀?
P/N 闁告帒妫旈弲鍫曟偑椤掑倻褰岄柣銏ゆ涧椤旀劖寰勯柆宥呭赋闁靛棔绀佹晶鐘诲疾椤栨稒缍€闂佹彃绉甸悧搴ㄥ礄閸℃劏鍋撻崒娑欐嫳濡炪倕婀卞ú?*闁哥儐鍨粩鎾嫉婢跺娅忛柣?Python 閻炴稑濂旂拹鐔虹棯瑜忔晶妤呭嫉?*闁?

> 閻犲洣鐒﹀畵浣虹驳婢跺矂鐛? **Python behavioral L2.** 闂傚牏鍋炲▍鐘虫媴閹鹃鍚€缂?PVT闁靛棔绶氬顏堟偋閸繃绂堥柛姘凹鐠炪垽濡存笟鈧顏嗘兜閸涱垰顣绘繛鏉戭儔閸ｆ椽濡?

<p align="center"><img src="docs/assets/figures/fig01_model_architecture.png" width="900" alt="婵☆垪鈧磭鈧兘寮搁懜鐢碘偓?></p>

### 闂佸じ绀侀悾?v3.x CDAC 闁归攱鎸绘晶?

婵絽绻嬮弲鑸电閸涱剙鈻忛柣顫妽閺嗭綁寮弶鍨濞达絽绉堕弫鍝モ偓鐟扮畭閳ь剙鈧?.0.0 闁哄鍩栭悗顖炲Υ?

```text
  濡ゅ倹蓱椤?   32, 16, 8, 8, 4, 2, 1 Cu   = 71 Cu
  婵℃ぜ鍎茬敮?                             2 Cu
  濞达絽瀛╅?   32, 16, 8, 4, 2, 2, 1 Cu  = 65 Cu
  闁告娲戦弲鍫曞箑閺勫浚鍚€:                          138 Cu  (552 fF @ Cu=4 fF)
```

闁哄秴娲ㄨⅷ闁哄牆顦伴弲銉╁级閸愵喖娅?($H = 67$):

```text
2144, 1072, 536, 536, 268, 134, 67,
  64,   32,  16,   8,   4,   4,  2, 1 缂備礁鐗忛顒佹媴?
```

- 闁稿繈鍔戦崕?14 濞戞搩浜悵?濞达絽瀛╅宀勬偨闂堟侗鍟囬柛娆忓€风粭宀勬煂閸ャ劎澹夐弶鍫熸尭閸欏棝鍨鹃弬琛″亾閺冣偓濡倗浠﹁箛姘澑闁汇垽娼ч鎰板Υ?
- 15 婵炲棌鍓濋惁顔芥綇閸愩劍鐝ら柛鎺嬪€曢崰? 14 闁绘せ鏅濋幃?trial/compare/commit + 1 缂備礁鐗忛顒佹媴瀹ュ啠鍋?
- 濡ゅ倹蓱椤?8-Cu 闁告劖銇炵紞鎴﹀箵閹邦亞杩斿鍫嗗棗鐦遍柛銉︽綑椤旀劙鏌ㄥ▎宥佸亾?
- 閻熸瑱绲块悥婊堝闯? **缂?P/N 闁哄秮鈧啿娅欓柡澶婂暣閸ｆ悂宕濋悩铏秬闁?+ Q2 闁肩绉撮崣鍡涘Υ?*
  闁?LUT闁靛棔鐒﹀Λ?DP闁靛棔鐒﹀Λ銈咁嚕閸屾氨鍩楅悶娑栧妸閳ь兛鐒﹀Λ銈夋偐閼哥鍋撴笟鈧幐鍛婃媴瀹ュ啠鍋?

<p align="center"><img src="docs/assets/figures/fig02_cdac_topology.png" width="800" alt="CDAC 闁归攱鎸绘晶?></p>

### 闁哄秮鈧啿娅?

闁告挸绉靛▍?force-0/force-1 闁告锕ゅΟ濠傗枖?(Shen 2018 JSSC)闁?

閻庣懓鏈弳锝嗘媴鎼淬埄鍞?(131 Q0) 濞达絾绮堢拹鐔煎礌瑜版帒甯抽柛鈺佹惈閸ｎ垳浜搁悮瀵哥**濞戞挸绉烽崵婊堝冀閳ュ啿娅?*闁炽儲鏌￠埀顒佹煣鐎靛苯袙閺冨洨绐涢柛?~3 mV offset
闁哄啰濮电涵鍫曞矗椤栫偞娴嗛悷鏇炴濞插﹪寮甸埀顒佹媴鎼粹€虫濞达絽绉跺▓鎴﹀触鎼达綆浼?margin闁?

```
闁哄秮鈧啿娅欏銈呮惈缁?  H1 闁?H2 闁?H4 闁?H8-R 闁?H8-A 闁?H16 闁?H32
婵絽绻掑ú浼村冀閸パ屽殸闁? 128                    (v3.0, 濞?512 闂傚嫬绉崇紞?
闁诡剝顕ч悺娆愭姜椤掍礁搴?   7 閼?4 閼?128 = 3584    (v3.0, 濞?14336 闂傚嫬绉崇紞?
Dither:    闁稿繑濞婂Λ?(闁革綆浜滈敍?闁?1 LSB 闁告鍟块崯鎴炴媴?
```

| 闁告瑥鍊归弳?| v3.0.0 | 鐟滅増鎸告晶?| 闁荤偛妫涢弫?|
|------|--------|--------|------|
| `AVG_PAIRS` | 512 | **128** | Oracle gap 闁?128 閻庣數鎳撻幃妤侇殰閸楃偞瀚? 闊?4 闁?|
| `SHEN_DITHER_LSB` | 鐎殿喒鍋?(缁绢収鍓涚槐顏堟儘? | **闁?* (config) | 闁革綆浜滈敍?闁?1 LSB + N 闁?32 闁哄啳娉涢崯鎴炴媴?|
| 闂傚嫨鍊栫涵鍫曞闯?| 闁?| **闁告瑥纾簺 7 濞?* | 128=2闁? 闁哄啰濞€濞撳墎娑甸鎸庮偨闂傚嫨鍊栫涵鍫曞闯?|

<p align="center"><img src="docs/assets/figures/fig03_weights_and_redundancy.png" width="800" alt="闁哄秮鈧啿娅欓柡澶婂暣閸?></p>

### v3.0.0 缂備焦鎸婚悘?

100-seed Monte Carlo, TSMC 180nm 濞ｅ洦绻傞悾褎瀵奸幏宀婂悁 (`閿?= 1%` 闁告娲戠紞鍛存偨闂堟侗鍟囧鍫曚憾閸?,
128 閻? 1 mV RMS 闁哄秮鈧啿娅欓柛锝庝簻閿? 闁活厸鏅涢懜鎵玻濡ゅ啯绁叉?FFT闁?

| 闁圭娲﹂悥?| 闁哄秮鈧啿娅欓柛?| 闁哄秮鈧啿娅欓柛?Q2 | Physical Oracle |
|------|--------:|----------:|----------------:|
| SNDR P50 | 63.73 dB | **74.50 dB** | 74.64 dB |
| ENOB P50 | 10.29 bit | **12.08 bit** | 12.11 bit |
| SFDR P50 | 70.57 dB | 94.29 dB | 96.91 dB |

- 100/100 闁哄牆顦伴弲銉╁冀閳ュ啿娅? 0/100 閻犳劗鍠愰弫褰掓儎?
- Oracle gap P50: **0.14 dB**
- DNL peak P95: 0.75 LSB; INL peak P95: 0.80 LSB
- 100/100 闂傚棗澧庡閬嶆儘? 闁哄牃鍋撳鍫嗗棛鍎查柣?= 1

| 閿?(MC_SIGMA) | 闁哄秮鈧啿娅欓柛?| 闁哄秮鈧啿娅欓柛?| Oracle Gap | 闁告帇鍊曢悾?|
|:------------:|--------:|--------:|----------:|:----:|
| 1% | 63.7 dB | 74.5 dB | 0.14 dB | 闂侇偅淇虹换?|
| 2% | 50.1 dB | 73.3 dB | 1.34 dB | 闂侇偅淇虹换?|
| 5% | 42.2 dB | 72.6 dB | 2.05 dB | 闂侇偅淇虹换?|
| 10% | 36.1 dB | 70.2 dB | 4.47 dB | 濞戞挸顕弲?|
| 20% | 30.2 dB | 50.6 dB | 24.0 dB | 濠㈡儼绮剧憴?|

闁哄洦娼欓ˇ? [v3.0 闁告瑦鍨电粩椋庢嫚鐎涙ɑ顫朷(docs/RELEASE_RESULTS_V3.md),
[閻庡湱鍋ら悰娆愮附濡炵偓顐絔(src/python_cal/analysis/).

<p align="center"><img src="src/python_cal/analysis/fft_comparison.png" width="900" alt="FFT 閻庝絻顫夐惁?></p>

### FFT 闁告绻楅?

| 闁告瑥鍊归弳?| 闁?|
|------|------:|
| FFT 闁绘劘顫夐弳?| 4096 |
| 闁烩晝顭堥崗?bin | 1019 |
| 闁烩晠鏅茬紞?| 0.123 rad |
| 閺夊牊鎸搁崣鍡涚嵁閸涱厼顔?| -0.5 dBFS |
| VFS | 婵?seed 闁告柣鍔嶉埀顑跨劍缁佹挳鏌?|
| 缂佹劖顨呴崵閬嶅极?| **闁活厸鏅涢懜鎵玻?(闁哄啰濮烽悰?** |
| clipping | 婵絽绻戦鍏兼交閹邦垼鏀介柡鍕劤缁扁€澄涢埀顒勫蓟?|

闁烩晝顭堥崗閬嶆煂閸ャ劎澹? 濞ｅ洠鈧啿濞囩紒顔煎⒔閳ユ﹢鎷冮挊澶嬭含 bin 1019 (gcd(1019,4096)=1)闁靛棗鍊瑰Λ銈呪枖閸曨剛纭€闁炽儲鏌￠埀顒佹⒒閻撯晞銇愰姀銏㈠炊闁哄嫷鍨遍婊呮兜椤旂偓鐣?(ENBW=1 bin)闁?

### 闊浂鍋婇埀顒傚枎缁辨垶鎱?

```powershell
# 閻庣懓顦抽ˉ?
python -m pip install -e ".[dev]"

# 閺夆晜鍔橀、鎴澝圭€ｎ厾妲?
$env:PYTHONPATH = "src"
python -m pytest src/python_cal/tests -q

# 濞戞挴鍋撻梺娆惧枟閻楀酣宕欓崱姘辨閻?闁?
python src/python_cal/debug_entry.py
python src/python_cal/debug_entry.py --pairs 64 --mc 0.02
python src/python_cal/debug_entry.py --noise 0.5 --pairs 32

# 閻庣懓鏈弳锝囩不閿涘嫬娈?(100 seeds)
python src/python_cal/run_final_calibration_pipeline.py

# 閻庡湱鍋ら悰娆愮附濡炵偓顐?
python src/python_cal/analysis/generate_fft_comparison.py
python src/python_cal/analysis/generate_multisigma_fft.py
```

### 缁绢収鍏涘▎銏″緞瀹ュ棙绲介幖?

| 婵☆垪鈧櫕鍋?| 闂傚倶鍔嶉弳?闁哄懏婀圭紞瀣不?| 闂傚牄鍨昏ⅶ |
|------|:----------:|-----:|
| CDAC 闁汇垽娼ч鎰版⒓闂堟稑鐏?(30濞? | 閻炴凹鍋勬慨鈺呭闯閵娿倖顐?| ~600 濞撶挼閾?|
| 閹煎瓨娲樺妯侯嚕閳ь剟宕?(28閼?:1 MUX) | ~560 Tr | ~600 濞撶挼閾?|
| StrongArm 婵絾妫佺欢婵嬪闯?| ~24 Tr | ~200 濞撶挼閾?|
| SAR FSM | ~400 闂?| ~1200 濞撶挼閾?|
| 闁哄秮鈧啿娅欓柟璨夊啫鐓戦柛?| ~1800 闂?| ~4000 濞撶挼閾?|
| 闁告梻濮靛鍫ュ椽瀹€鍐冩帡鎯嶆担鍛婄彜 | ~2000 闂?| ~4500 濞撶挼閾?|
| **闁诡剚妲掗?* | **~4200 闂?+ ~600 Tr** | **~0.011 mm閾?* |

閻庣懓鏈弳锝夊礆閸℃鈧? [DELIVERY.md](src/python_cal/DELIVERY.md)

### 濞戞捁妗ㄧ紞宥嗙▔瀹ュ洦鏆忛柡?95-Cu CDAC ?

```text
闁?  1,2,4,6,10,16,24 Cu (濞达絽瀛╅? | 1 Cu (婵℃ぜ鍎茬敮? | 1,2,4,8,16 Cu (濡ゅ倹蓱椤?
闁?  闁轰礁鐡ㄩ弳?138 Cu
```

闁?0.5% 濠㈠爼浜堕崢? 1000-seed 闁活喕鐒﹀﹢鎵偓瀛ゃ値鍚€:
- 闁? 缂傚倽娅ｉ悥?P50=22, 闁哄牃鍋撻柛?84; 闁哄牃鍋撳鍫嗗棛鍎查柣顔荤劍濞撳爼宕?9
- 闁? **1000/1000 闂傚棗澧庡閬嶆儘? 闁哄牃鍋撳鍫嗗棛鍎查柣顔荤椤劗绱?1**

<p align="center"><img src="docs/assets/figures/fig09_cdac_candidate_comparison.png" width="700" alt="CDAC 閻庝絻顫夐惁?></p>

### 闁烩晩鍠栫紞宥囩磼閹惧鈧?

```text
src/python_cal/
  config.py              缂備胶鍠嶇粩鎾煀瀹ュ洨鏋傞柛蹇嬪劚瑜?
  debug_entry.py         濞戞挴鍋撻梺娆惧枟閻楀酣宕欓崱姘辨閻?闁?
  DELIVERY.md            闂侇偅甯婂锕傚棘閸ャ劊鈧?
  topology/              闁轰礁鐡ㄩ弳?CDAC 闁归攱鎸绘晶銈嗙▔鎼达紕纾婚柛蹇撶－婵悂骞€?
  physical/              闁活澀绲诲畵搴ｂ偓鐟扮墛娴滆棄效閸屾粳鎺楀闯?
  comparator/            闁告柣鍔嶉埀顑跨劍閻︻喗娼忛崘銊︾彜婵☆垪鈧磭鈧?
  async_control/         鐎殿喖鍊归?SAR 闁圭儵鍓濇晶?
  calibration/           Shen 2018 force-0/force-1 闁哄秮鈧啿娅?
  decode/                缂佺虎鍨版慨鐐哄级閸愩劍瀚查悷娆欑悼閻栨粓宕?
  validation/            FFT 濞戞挸楠歌ぐ鍙夋綇閸撗呭灣闁哄牜鍓欓鍝ユ媼?
  analysis/              閻庡湱鍋ら悰娆撴嚇濮橆厽鎷卞☉鎾抽濞存鎮?
  tests/                 闁搞儳鍋涚紞濠偯圭€ｎ厾妲稿┑鍌涖仦濞?
docs/
  MODELING_GUIDE.md, VALIDATION_STATUS.md, RELEASE_RESULTS_V3.md, ...
```

### 鐎殿喗娲滈弫?

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

闁哄秮鈧啿娅欓柛妤€绻楅鍛村春鏉炴壆鑹? Shen et al., "A 16-bit 16-MS/s SAR ADC With On-Chip
Calibration in 55-nm CMOS," *IEEE JSSC*, vol. 53, no. 4,
pp. 1147&ndash;1154, Apr. 2018.

### AI 閺夊牆鎳庢慨顏呯珶閻楀牊顫?

闁哄牜鍓熼妴宥夋儎椤旇鈻忛柣?AI 閺夊牆鎳庢慨顏嗙磽閺嶎偆鍨崇€规悶鍎遍崣鍨嚕閳ь剟宕ｉ幋顖滅闁告牕鎳忕€?CODEX 濞?Trae (DeepSeek)闁?
闁圭鍋撻柡?AI 闁汇垻鍠愰崹姘閿濆洨鍨崇€规瓕灏欑划鈩冪閸濆嫪绱ｉ悗鍏夊墲閻撯剝绋夋惔銊у矗閻犲洣闄嶉埀?

### 鐎殿喒鍋撴繝褎鍔橀蹇涘矗?

[MIT](LICENSE)
