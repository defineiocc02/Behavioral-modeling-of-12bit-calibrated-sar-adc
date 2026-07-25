# 纭欢璧勬簮涓?Verilog-A 绉绘鏂规

## 1. 妯℃嫙閮ㄥ垎

姣忎釜宸垎渚э細

| 椤圭洰 | 鏁伴噺 |
|---|---:|
| high-segment unit capacitance | 71 Cu |
| bridge | 2 Cu |
| low-segment unit capacitance | 65 Cu |
| total | 138 Cu |
| independently switched groups | 14 |

P/N 鎬昏 276 Cu銆傝嫢 `Cu=4 fF`锛屼富闃靛垪鎬诲悕涔夌數瀹逛负 `1.104 pF`锛屾瘡渚?`552 fF`銆傝繖涓嶅寘鍚?sampling switch銆乧omparator input 鍜?routing parasitic銆?
鍙渶瑕佷竴涓富 comparator銆倂3.0 涓嶅鍔?auxiliary calibration comparator銆?calibration sub-DAC銆丩UT SRAM 鎴?CAM銆?
## 2. 姝ｅ父杞崲鏁板瓧璧勬簮

- 15-state asynchronous SAR sequencer锛?- 14 瀵?P/N bottom-plate controls锛?- 7 涓?P-side 鍜?7 涓?N-side calibrated high-weight registers锛?- 浣庢 7 涓?nominal constants 涓?1 涓?terminal constant锛?- 涓€涓害 20-bit signed Q6 accumulator锛?- 涓€涓?common normalization reciprocal/multiplier锛?- 14-bit unsigned Q2 output (`12 integer + 2 fractional`)銆?
鑻?high-weight register 閲囩敤 unsigned Q6銆?2 涓暣鏁颁綅锛屾瘡涓?18 bits锛?14 涓瘎瀛樺櫒鍏?252 bits銆備綆娈靛父鏁板彲缁煎悎涓鸿繛绾垮父閲忋€?
## 3. 鏍″噯鏁板瓧璧勬簮

鏍″噯纭欢鍙笌姝ｅ父 decoder 澶嶇敤锛?
- 涓€涓?target counter锛? states锛夛紱
- 涓€涓?pair counter锛? bits锛?..511锛夛紱
- P0/P1/N0/N1 鍥涚姸鎬佹帶鍒讹紱
- 涓€涓害 30-bit signed accumulation register锛屽彲鍒嗘椂澶嶇敤锛?- target validation comparator锛?- 252-bit high-weight register bank銆?
鎬绘牎鍑嗗伐浣滀负 14336 涓?lower-SAR sub-conversions锛屼笌閫€褰圭増鏈浉鍚屻€?鏍″噯鏄墠鏅惎鍔ㄦ祦绋嬶紝涓嶅奖鍝嶆瘡娆?normal conversion 鐨?15-comparison 寤惰繜銆?
## 4. Verilog-A 绔彛

鎺ㄨ崘妯℃嫙妯″潡鍙弿杩扮墿鐞?CDAC 涓?comparator-facing top plates锛?
```text
electrical VINP, VINN, VREFP, VREFN, VCM
electrical VTOP_P, VTOP_N
input SAMPLE
input [13:0] BITP
input [13:0] BITN
```

stage 鍒扮數瀹圭粍锛?
```text
0 H32, 1 H16, 2 H8-A, 3 H8-R, 4 H4, 5 H2, 6 H1,
7 L32, 8 L16, 9 L8, 10 L4, 11 L2-A, 12 L2-R, 13 L1
```

閲囨牱鐩镐綅锛孭 渚ф墍鏈?14 涓?bottom plates 鎺?VINP锛孨 渚ф帴 VINN銆傝浆鎹㈢浉浣?鐢?BITP/BITN 閫夋嫨 VCM 鎴?VREFP銆俠ridge 鏄唴閮?`VTOP 鈫?VBRIDGE` 鐢靛锛?娌℃湁鏁板瓧 bottom-plate port銆?
## 5. 澶遍厤鏄犲皠

涓嶈缁欎竴涓?32-Cu group 鐩存帴鏂藉姞 `0.5%` group sigma銆傛纭柟娉曟槸锛?
```text
C_group = Cu 脳 sum_{k=1..N}(1 + epsilon_k)
epsilon_k ~ Normal(0, 0.005)
```

鍥犳 group relative sigma 鑷姩鎸?`0.5%/sqrt(N)` 缂╁皬銆侾/N 涓や晶鐙珛鐢熸垚锛?bridge 鐨勪袱涓?unit cells 涔熺嫭绔嬬敓鎴愩€?
## 6. 绉绘椤哄簭

1. 鍏堝湪 Verilog-A 涓鐜扮悊鎯?15-decision trace锛?2. 瀵瑰洓涓唬琛ㄨ緭鍏ユ瘮杈?Python 涓?VA 鐨勬瘡 stage `VTOP_P-VTOP_N`锛?3. 鍔犲叆 unit-cell mismatch 骞舵瘮瀵?physical oracle weights锛?4. 鎺ュ叆鏁板瓧鏍″噯瀵勫瓨鍣ㄤ笌 Q6 accumulator锛?5. 浣跨敤鍚屼竴 `N=4096, k=1019, -0.5 dBFS, rectangular` FFT 鍗忚锛?6. 鏈€鍚庢墠杩涘叆 Spectre PVT銆乻ettling銆乺eference droop 鍜?parasitic 楠岃瘉銆?
杩欎唤鏂囨。鏄鍙ｅ拰璧勬簮瑙勫垝锛屼笉鏄凡瀹屾垚鐨勬櫠浣撶绾ф垨 Verilog-A 绛炬牳銆?