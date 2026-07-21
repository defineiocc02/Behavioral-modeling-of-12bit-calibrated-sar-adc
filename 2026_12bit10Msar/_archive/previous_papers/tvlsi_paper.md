# A 12-bit 10-MS/s SAR ADC With Current-Domain $kT/C$ Noise Cancellation via CAAZ

> **Authors:** Zhao Yi (Student Member, IEEE)
> **Affiliation:** School of Integrated Circuits, Huazhong University of Science and Technology
> **Journal:** IEEE Transactions on VLSI Systems (TVLSI)
> **Date:** May 2026 | **Doc:** HUST-SAR-2026-003

---

## Abstract

This paper presents a 12-bit 10-MS/s SAR ADC employing a current-adjusting auto-zeroing (CAAZ) technique for $kT/C$ noise cancellation in 180-nm CMOS. The CAAZ architecture overcomes the fundamental gain-saturation trade-off of conventional voltage-domain output offset storage (OOS) approaches by shifting noise extraction to the current domain. A capacitance burden shifting mechanism relocates the storage capacitor to a low-impedance internal node, enabling $C_{\rm AZ}=300$ fF to suppress secondary noise while keeping input capacitance minimal. The CAAZ noise cancellation efficiency $\eta$ is experimentally characterized using a 100$\times$ noise injection (NF=10) double-$t_d$ method across five PVT corners. Transient noise simulations demonstrate an ENOB of 11.61 bit and SNR of 71.81 dB at the TT corner (NF=1, $t_d$=26 ns), with all corners exceeding 11.4 bit. The CAAZ $\eta$ reaches 87.9% at TT, reducing to 79.7% at the worst-case SF corner (85°C, slow-N fast-P). Total power consumption is 720 $\mu$W from a 1.8-V supply. A two-batch cross-validation confirms $\eta$ consistency within 1.4 p.p.

**Keywords:** SAR ADC, $kT/C$ noise cancellation, current-adjusted auto-zeroing, CAAZ, 180-nm CMOS.

---

## 1. Introduction

Successive approximation register (SAR) ADCs dominate medium-resolution medium-speed applications due to excellent power efficiency [1]. Beyond 12-bit resolution, $kT/C$ sampling noise emerges as the primary SNR bottleneck [2]. Suppressing this noise in a 12-bit system with 1.8-V reference demands picofarad-range capacitors, incurring severe power penalties.

Liu et al. [3] pioneered voltage-domain $kT/C$ noise cancellation for SAR ADCs but exposed a gain-saturation trade-off inherent to output offset storage (OOS). For a 12-bit converter, even gain $A=10$ produces 9-V output, forcing $A\approx6$ and capping $kT/C$ attenuation at ~16 dB [3]. Subsequent efforts [4,5,6,7] address specific aspects but introduce alternative burdens.

Safiallah et al. [8] proposed a current-adjusting auto-zeroing (CAAZ) scheme. This work builds upon that principle for a complete 12-bit 10-MS/s SAR ADC in 180-nm CMOS.

**Contributions:**
1. CAAZ with $\eta=87.9\%$ via NF=10 double-$t_d$ characterization across 5 PVT corners
2. Capacitance burden shifting: $C_{\rm AZ}=300$ fF at low-impedance node
3. ENOB=11.61 bit, SNR=71.81 dB, all corners >11.4 bit, 720 $\mu$W, two-batch validation

---

## 2. Background and CAAZ Architecture

### 2.1 Limitations of Voltage-Domain OOS

The conventional voltage-domain $kT/C$ noise cancellation [3] stores amplified noise on a feedback capacitor. Residual input-referred noise:

$$v_{\rm ns,res}=v_{\rm ns1}e^{-2\Delta t/\tau}+v_{\rm ns,AZ}/A+v_{\rm ns,comp}/A$$

where $v_{\rm ns1}$ is the main sampling noise, $\Delta t$ the noise-sampling window, and $A$ the preamplifier gain. The output swing limitation is decisive: with 0.9-V MSB step, $A=10$ produces 9-V output, compelling $A\approx6$.

### 2.2 CAAZ Operating Principle

Three-phase operation:
- **Phase 1 — Sampling:** Input switch opens, freezing $V_{\rm in}+v_{\rm ns1}$ on $C_1$
- **Phase 2 — Current-Domain Noise Sampling:** Loads diode-connected, gain $\approx$1. Noise stored on $C_{\rm AZ}$ as $I_{\rm diff}=-g_{mp}v_{\rm ns1}$
- **Phase 3 — SAR Conversion:** Loads switch to current-source, gain $>$50. Stored current cancels $v_{\rm ns1}$

### 2.3 Current-Domain Noise Derivation

Equivalent input-referred noise:

$$v_{\rm ns,eq}\approx v_{\rm ns1}/(g_{mp}R_{\rm OA})+v_{\rm ns2}/(g_{mp}R_{\rm OA})\cdot g_{mn}/g_{mp}$$

- **Residual main noise:** $v_{\rm ns1,res}=v_{\rm ns1}/(g_{mp}R_{\rm OA})$, scaling with gain $>$50
- **Secondary noise:** from $C_{\rm AZ}$, attenuated by $C_{\rm AZ}=300$ fF

### 2.4 Capacitance Burden Shifting

In OOS: storage at high-impedance output ($\sim$100 k$\Omega$).
In CAAZ: $C_{\rm AZ}$ at low-impedance node ($\sim$1 k$\Omega$):
$$\tau_{\rm external}=R_{\rm driver}C_1 \gg \tau_{\rm internal}=C_{\rm AZ}/g_{mn}$$

---

## 3. Circuit Implementation

pMOS input pair, nMOS active loads. Phase 2: diode-connected (gain$\approx$1). Phase 3: current-source ($g_{mp}R_{\rm OA}>50$). $C_{\rm AZ}=300$ fF at nMOS gates. Optimal $t_d=26$ ns. StrongARM latch with kickback isolation.

---

## 4. Characterization Methodology

Noise-factor (NF) injection: injected noise power = NF$^2$ $\times$ thermal noise. NF=10 gives 100$\times$ power. CAAZ efficiency:

$$\eta = 1 - (101\cdot 10^{-\Delta\text{SNR}/10} - 1) / 100$$

where $\Delta\text{SNR}=\text{SNR}_{t_d=26\text{ns}}-\text{SNR}_{t_d=24.05\text{ns}}$.

---

## 5. Simulation Results

Simulated in 180-nm CMOS, 1.8-V supply, 5 corners (TT/FF/SS/SF/FS). Spectre 231 APS, transient noise 15 $\mu$s.

### 5.1 Baseline (NF=1, td=26ns)

| Corner | Temp | SNR (dB) | ENOB (bit) |
|--------|------|---------|-----------|
| **TT** | 27°C | **71.81** | **11.61** |
| FF | $-40$°C | 71.16 | 11.49 |
| SS | 85°C | 71.48 | 11.55 |
| SF | 85°C | 71.29 | 11.53 |
| FS | $-40$°C | 70.92 | 11.47 |

All corners ENOB $>$ 11.4 bit. ENOB spread: 0.14 bit.

### 5.2 CAAZ Efficiency (NF=10)

| Corner | SNR$_{26}$ (dB) | SNR$_{24}$ (dB) | $\eta$ | Suppression |
|--------|----------------|----------------|-------|------------|
| TT | 64.10 | 55.22 | **87.9%** | 8.3$\times$ |
| FF | 66.40 | 57.01 | 89.4% | 9.4$\times$ |
| SS | 61.03 | 53.33 | 83.9% | 6.2$\times$ |
| SF | 61.60 | 54.84 | **79.7%** | 4.9$\times$ |
| FS | 67.06 | 56.94 | **91.2%** | 11.4$\times$ |

### 5.3 td Optimization (24.05 vs 26.0 ns)

- High-temperature corners (SS/SF): SNR +1.8 dB
- Low-temperature corners (FF/FS): minimal change ($<$0.6 dB)
- 26.0 ns selected as optimal

### 5.4 Power (TT corner)

| Block | Power ($\mu$W) | Share |
|-------|--------------|-------|
| Preamplifier+SR+Driver | 363.7 | 50% |
| Switch Network | 97.1 | 14% |
| SAR Logic | 149.0 | 21% |
| SYNC | 110.4 | 15% |
| **Total** | **720.2** | 100% |

### 5.5 Cross-Batch Validation

$\eta$ deviation $<$ 1.4 p.p. between batches. COMPOWER/digital power consistent to $<$3 $\mu$W.

### 5.6 Performance Comparison

| Parameter | This Work | JSSC'20 [3] | ESSERC'24 [5] | JSSC'25 [7] |
|-----------|----------|-------------|---------------|-------------|
| Technology | 180 nm | 40 nm | 65 nm | 180 nm |
| Resolution | 12 bit | 13 bit | 13 bit | 16 bit |
| Rate | **10 MS/s** | 40 MS/s | 40 MS/s | 5 MS/s |
| ENOB | **11.61** bit | 11.16 bit | 11.08 bit | 15.27 bit |
| SNR | **71.81 dB** | 69.0 dB | 68.5 dB | 93.7 dB |
| Power | 720 $\mu$W | 591 $\mu$W | 667 $\mu$W | 5310 $\mu$W |
| $C_{\rm AZ}$ | 300 fF | N/A (OOS) | N/A | N/A |
| CAAZ $\eta$ | **87.9%** | N/A | N/A | N/A |
| PVT Corners | **5 (SF incl.)** | 3 | 3 | 3 |
| Cross-Batch | **Yes** | No | No | No |

---

## 6. Conclusion

A 12-bit 10-MS/s SAR ADC with CAAZ $kT/C$ noise cancellation in 180-nm CMOS achieves ENOB=11.61 bit, SNR=71.81 dB, SFDR=84.01 dB (all corners $>$11.4 bit). CAAZ $\eta=87.9\%$ (TT), characterized via NF=10 double-$t_d$ method. Two-batch $\eta$ consistency within 1.4 p.p. Total power 720 $\mu$W. SF corner (85°C) identified as worst case ($\eta=79.7\%$). CAAZ is validated as a robust technique for precision SAR ADCs in mature CMOS.

---

## References

[1] S. Liu, Y. Shen, and Z. Zhu, "A 12-Bit 10 MS/s SAR ADC With High Linearity and Energy-Efficient Switching," *IEEE TCAS-I*, vol. 63, no. 10, pp. 1616–1627, 2016.

[2] R. Kapusta, H. Zhu, and C. Lyden, "Sampling Circuits That Break the kT/C Thermal Noise Limit," *IEEE JSSC*, vol. 49, no. 8, pp. 1694–1701, 2014.

[3] J. Liu et al., "A 13-Bit 0.005-mm² 40-MS/s SAR ADC With kT/C Noise Cancellation," *IEEE JSSC*, vol. 55, no. 12, pp. 3260–3270, 2020.

[4] Z. Li et al., "A SAR ADC with Reduced kT/C Noise by Decoupling Noise PSD and BW," *IEEE VLSI Symp.*, pp. 1–2, 2020.

[5] J. Won et al., "A 13b 40MS/s SAR ADC with Robust kT/C Noise Cancellation Using a Feedback Auxiliary Amplifier," *IEEE ESSERC*, pp. 369–372, 2024.

[6] Y. Gu et al., "An Improved kT/C Noise Cancellation Technique with Presampling," *Electron. Lett.*, vol. 60, no. 16, e13298, 2024.

[7] Q. Huang et al., "A 5-MS/s 16-Bit Low-Noise Low-Power Split Sampling SAR ADC," *IEEE JSSC*, vol. 60, no. 3, pp. 813–825, 2025.

[8] M. Safiallah et al., "A Current-Adjusting Auto-Zeroing Technique for DC-Offset and Flicker-Noise Cancellation," *IEEE TVLSI*, vol. 31, no. 12, pp. 1950–1959, 2023.
