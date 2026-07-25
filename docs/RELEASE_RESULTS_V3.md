# v3.0 鍙戝竷缁撴灉

## 杩愯鏉′欢

- run ID: `dbac69f3`
- 100 Monte Carlo seeds锛寀nit-cap mismatch sigma = 1.0%
- 128 calibration pairs锛宑alibration noise = 1 mV RMS
- 4096-point coherent FFT锛宍k=1019`锛宲hase `0.123 rad`
- dynamic VFS锛岃緭鍏?`-0.5 dBFS`锛宺ectangular window
- Q2 calibrated output锛沬nteger 12-bit 鍙綔浜屾閲忓寲璇婃柇

## 鍔ㄦ€佺粨鏋?
| 鎸囨爣 | 鏍″噯鍓?| 鏍″噯鍚?Q2 | 鐗╃悊 oracle |
|---|---:|---:|---:|
| SNDR P50 | 66.616 dB | 74.482 dB | 74.671 dB |
| SNDR min | 59.972 dB | 74.094 dB | 74.435 dB |
| ENOB P50 | 鈥?| 12.080 bit | 12.112 bit |
| ENOB min | 鈥?| 12.016 bit | 12.072 bit |

- valid calibrations: 100/100
- negative gain: 0/100
- oracle gap P50/P95/max: `0.156/0.412/0.559 dB`
- gap <= 0.5 dB: 98/100锛沢ap <= 1.0 dB: 100/100
- calibrated integer-12 diagnostic P50: `71.149 dB / 11.526 bit`

Q2 涓?integer-12 鐩稿樊绾?3.33 dB銆傝繖涓鐓х洿鎺ヨ鏄庢棫鈥滃彧鏈?11 浣嶁€濈幇璞?涓昏鏉ヨ嚜鏍″噯鍚庣殑鍒嗘暟鏉冮噸鍐嶆琚暣鏁?12-bit 杈撳嚭閲忓寲锛岃€屼笉鏄緭鍏ユ憜骞呫€?鐢靛鐗╃悊 oracle 鎴?FFT 绐楀鑷淬€?
## 闈欐€佺粨鏋?
| 鎸囨爣 | P50 | P95 | max |
|---|---:|---:|---:|
| DNL peak | 0.7500 LSB | 0.8663 LSB | 0.9501 LSB |
| INL peak | 0.8020 LSB | 0.9234 LSB | 0.9572 LSB |
| missing codes | 0 | 0 | 0 |
| maximum integer jump | 1 | 1 | 1 |

鍙戝竷闂ㄤ互 code-density DNL/INL銆佺己鐮佸拰鏈€澶ф暣鏁拌烦鐮佷负鍑嗭紝鍏ㄩ儴閫氳繃銆?
褰㈠紡鍖栧眬閮ㄨ瘖鏂粛璁板綍 27065 涓?integer backsteps锛?00 seeds 鍚堣锛夈€傝繖浜?鏉ヨ嚜鍐椾綑鍐崇瓥瀛楀湪浜?LSB 杈撳叆鍖洪棿鐨勯噸鍙狅紝鍥犳鏈増鏈笉瀹ｇО浠绘剰鏃犻檺灏忚緭鍏?鎵板姩涓嬮兘涓ユ牸鏁板鍗曡皟銆傚畠浠病鏈夐€氳繃鎺掑簭銆丩UT銆丆AM銆丏P 鎴栧紓甯歌〃淇銆?
## 鏍″噯璇樊

| target | absolute error P50/P95 (Q0) | normalized ratio error P50/P95 |
|---|---:|---:|
| H1 | 0.1797 / 0.4788 | 0.000846 / 0.002554 |
| H2 | 0.3014 / 0.8049 | 0.000486 / 0.001256 |
| H4 | 0.5435 / 1.5343 | 0.000346 / 0.000790 |
| H8-R | 1.0448 / 3.0292 | 0.000125 / 0.000297 |
| H8-A | 1.0039 / 3.1613 | 0.000153 / 0.000353 |
| H16 | 1.9804 / 6.2707 | 0.000067 / 0.000194 |
| H32 | 3.8674 / 12.3308 | 0.000061 / 0.000182 |

缁濆 Q0 璇樊闅忕洰鏍囨潈閲嶆斁澶э紱鍘婚櫎涓嶅彲瑙傛祴鐨勫叏灞€ scale 鍚庯紝H32 鐨勬瘮渚?璇樊 P50/P95 浠?`0.0061%/0.0182%`锛屼笌 0.156 dB 鐨勫姩鎬?oracle gap 涓€鑷淬€?
## 鏈哄櫒鍙璇佹嵁

- `src/python_cal/validation_results/final_pipeline/final_pipeline_dbac69f3.csv`
- `src/python_cal/validation_results/final_pipeline/final_summary_dbac69f3.json`
- `src/python_cal/validation_results/final_pipeline/final_report_dbac69f3.md`
- `src/python_cal/validation_results/final_pipeline/run_manifest.json`
- `src/python_cal/validation_results/cdac_design_audit.json`

杩欎簺缁撴灉鏄?Python behavioral L2锛屼笉浠ｆ浛 Verilog-A銆佹櫠浣撶绾?PVT銆佺増鍥?鍚庝豢鎴栫鐗?code-density 绛炬牳銆?