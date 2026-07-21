#!/usr/bin/env python3
"""
SAR ADC Calibration Analysis & Academic Plotting
=================================================
Parses Spectre simulation logs, extracts calibration weights,
computes INL/DNL/ENOB/SFDR/SNR/SNDR, and generates publication-quality figures.
"""

import os, re, json, sys
import numpy as np
from collections import OrderedDict

# ============================================================
# Configuration
# ============================================================
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "sim_results")
PLOTS_DIR   = os.path.join(os.path.dirname(__file__), "plots")

# CDAC topology parameters
C_B = 2        # Bridge capacitor (units of Cu)
C_LOW = 63     # Low array total (1+2+4+8+16+32)
C_HIGH = 64    # High array total (1+1+2+4+8+16+32)
H_RATIO = 65   # NOM_H1_WEIGHT

# Nominal weights (Q=6 scaled: q_scale=64)
NOMINAL_WEIGHTS = {
    "w6": 65,   # H1C-A
    "w5": 65,   # H1C-R (redundant)
    "w4": 130,  # H2C
    "w3": 260,  # H4C
    "w2": 520,  # H8C
    "w1": 1040, # H16C
    "w0": 2080, # H32C
    "w7": 64,   # L32C (calDAC MSB)
    "w8": 32,   # L16C
    "w9": 16,   # L8C
    "w10": 8,   # L4C
    "w11": 4,   # L2C
    "w12": 2,   # L1C
    "w13": 1,   # Terminal LSB
}

N_STAGES = 14
TOTAL_WEIGHT_NOM = sum(NOMINAL_WEIGHTS.values())

# Scenario labels
SCENARIO_LABELS = OrderedDict([
    ("ideal",       "Ideal"),
    ("mild_2pct",   "Mild\n+/-2%"),
    ("sev_5pct",    "Severe\n+/-5%"),
    ("sys_pos_2pct","Systematic\n+2%"),
    ("sys_neg_2pct","Systematic\n-2%"),
])

# ============================================================
# Log Parsing
# ============================================================

def parse_log(filepath):
    """Parse a Spectre log file, extracting calibration weights and status."""
    if not os.path.exists(filepath):
        return None
    
    with open(filepath, 'r', errors='ignore') as f:
        text = f.read()
    
    result = {
        "weights": {},
        "done": False,
        "error": False,
        "targets": [],
        "filename": os.path.basename(filepath),
    }
    
    # Extract per-target calibration results
    # Pattern: "POS avg_code=65\nNEG avg_code=65\nDIFF=130\nWEIGHT=65\nVALID=1\nSAT=0"
    target_map = {
        0: "w6",  # H1C-A
        1: "w5",  # H1C-R
        2: "w4",  # H2C
        3: "w3",  # H4C
        4: "w2",  # H8C
        5: "w1",  # H16C
        6: "w0",  # H32C
    }
    
    # Find all TARGET blocks
    target_blocks = re.finditer(
        r'CAL TARGET name=(\S+) stage=(\d+) Wnom=(\d+).*?'
        r'WEIGHT=([\d.]+).*?'
        r'VALID=(\d).*?'
        r'SAT=(\d)',
        text, re.DOTALL
    )
    
    for m in target_blocks:
        name = m.group(1)
        stage = int(m.group(2))
        wnom = int(m.group(3))
        weight = float(m.group(4))
        valid = int(m.group(5))
        sat = int(m.group(6))
        
        tid = None
        for t, wk in target_map.items():
            if stage == (6 - t):  # H1C-A→6, H1C-R→5, ..., H32C→0
                tid = t
                break
        
        result["targets"].append({
            "name": name,
            "stage": stage,
            "wnom": wnom,
            "weight": weight,
            "valid": valid,
            "sat": sat,
            "target_id": tid,
        })
    
    # Extract the final weights line
    w_match = re.search(
        r'CAL WEIGHTS=\{([\d.]+),([\d.]+),([\d.]+),([\d.]+),'
        r'([\d.]+),([\d.]+),([\d.]+),([\d.]+),([\d.]+),'
        r'([\d.]+),([\d.]+),([\d.]+),([\d.]+),([\d.]+)\}',
        text
    )
    if w_match:
        for i in range(14):
            result["weights"]["w{}".format(i)] = float(w_match.group(i+1))
    
    # Check overall status
    result["done"] = "cal_done=1" in text.lower() or "DONE" in text
    result["error"] = "cal_error=1" in text.lower() or "ERR" in text
    result["rc_ok"] = "spectre completes with 0 errors" in text
    
    return result

def load_all_results():
    """Load all simulation results from logs directory."""
    all_results = {}
    
    for scenario in SCENARIO_LABELS:
        for calbp, label in [(0, "calon"), (1, "caloff")]:
            key = "{}_{}".format(scenario, label)
            # Try both local and VM naming
            logfile = os.path.join(RESULTS_DIR, "log_{}.log".format(key))
            if not os.path.exists(logfile):
                # Also check the VM naming
                logfile = os.path.join(RESULTS_DIR, "log_{}.log".format(key))
            
            result = parse_log(logfile)
            if result:
                all_results[key] = result
    
    # Also try to load from a JSON cache
    cache_file = os.path.join(RESULTS_DIR, "parsed_results.json")
    if all_results:
        # Save cache
        cache = {}
        for k, v in all_results.items():
            cache[k] = {
                "weights": v["weights"],
                "done": v["done"],
                "error": v["error"],
                "rc_ok": v["rc_ok"],
                "targets": [{"name": t["name"], "weight": t["weight"], "valid": t["valid"]} 
                           for t in v.get("targets", [])],
            }
        with open(cache_file, 'w') as f:
            json.dump(cache, f, indent=2)
    
    return all_results


# ============================================================
# SAR ADC Transfer Function & INL/DNL
# ============================================================

def generate_all_codes(weights_dict):
    """Generate all possible SAR DAC output codes for the given weights."""
    weights = [weights_dict.get("w{}".format(i), NOMINAL_WEIGHTS.get("w{}".format(i), 0))
               for i in range(N_STAGES)]
    weights = np.array(weights, dtype=float)
    
    n = len(weights)
    # Generate all 2^n combinations
    codes = np.zeros(1 << n, dtype=float)
    for i in range(n):
        # Every 2^(i+1) codes, weight i toggles
        period = 1 << (i + 1)
        half = 1 << i
        for j in range(0, 1 << n, period):
            codes[j+half:j+period] += weights[i]
    
    # Sort unique values
    codes = np.unique(codes)
    return codes

def compute_inl_dnl(weights_dict):
    """Compute INL and DNL from calibrated weights using endpoint fit."""
    codes = generate_all_codes(weights_dict)
    
    if len(codes) < 10:
        return np.array([]), np.array([])
    
    n_codes = len(codes)
    t_first = codes[0]
    t_last = codes[-1]
    t_range = t_last - t_first
    
    if t_range == 0:
        return np.array([]), np.array([])
    
    ideal_step = t_range / (n_codes - 1)
    
    inl = np.zeros(n_codes)
    dnl = np.zeros(n_codes)
    
    for i in range(n_codes):
        t_ideal = t_first + i * ideal_step
        inl[i] = (codes[i] - t_ideal) / ideal_step
    
    for i in range(1, n_codes):
        step = codes[i] - codes[i-1]
        dnl[i] = step / ideal_step - 1.0
    
    return inl, dnl


# ============================================================
# Dynamic Performance (FFT)
# ============================================================

def sar_quantize_sine(weights_dict, n_samples=4096, fs=10e6, vref=1.8):
    """SAR ADC quantization of a sine wave input using DAC transfer function."""
    weights = np.array([weights_dict.get("w{}".format(i), 
                       NOMINAL_WEIGHTS.get("w{}".format(i), 0))
                       for i in range(N_STAGES)], dtype=float)
    
    total_w = np.sum(weights)
    
    # Coherent sampling
    n_cycles = 127  # prime
    fin = fs * n_cycles / n_samples
    
    t = np.arange(n_samples) / fs
    amp = 0.45 * vref  # -0.9 dBFS
    offset = vref / 2
    vin = offset + amp * np.sin(2 * np.pi * fin * t)
    
    # Build DAC transfer function: all possible DAC output levels
    dac_levels = generate_all_codes(weights_dict)
    
    # Normalize to voltage: DAC_code -> voltage
    # The DAC output voltage for code k is: dac_levels[k] / total_w * vref
    dac_voltages = dac_levels / total_w * vref
    
    # Map each input voltage to the nearest DAC level (SAR quantizer)
    codes = np.zeros(n_samples, dtype=int)
    for idx in range(n_samples):
        v = vin[idx]
        # Find the DAC code whose voltage is just below v
        # In SAR, the quantized value is the largest DAC level <= input
        below = dac_voltages <= v
        if np.any(below):
            code_idx = np.where(below)[0][-1]
        else:
            code_idx = 0
        codes[idx] = code_idx
    
    return codes, fin, fs

def fft_metrics(codes, fin, fs):
    """Compute ENOB, SNDR, SNR, SFDR from FFT."""
    n = len(codes)
    data = codes.astype(float) - np.mean(codes)
    
    # Hann window
    window = np.hanning(n)
    data_w = data * window
    w_gain = np.mean(window)
    
    # FFT
    spec = np.fft.fft(data_w) / n
    spec = spec[:n//2]
    
    # Power spectrum
    ps = 2 * np.abs(spec)**2 / w_gain**2
    
    # Signal bin
    sig_bin = int(round(fin / fs * n))
    if sig_bin >= n//2:
        sig_bin = n//2 - 1
    
    sig_power = max(ps[sig_bin], 1e-30)
    
    # Harmonic bins
    harm_bins = set()
    for h in range(2, 8):
        hb = (sig_bin * h) % n
        if hb < n//2:
            harm_bins.add(hb)
    
    dist_power = sum(ps[hb] for hb in harm_bins) if harm_bins else 0
    
    # Noise: exclude DC, signal, signal±2, harmonics
    exclude = {0, sig_bin} | harm_bins
    for d in range(-2, 3):
        b = (sig_bin + d) % (n//2)
        exclude.add(b)
    
    noise_mask = np.ones(n//2, dtype=bool)
    for b in exclude:
        if 0 <= b < n//2:
            noise_mask[b] = False
    noise_power = sum(ps[noise_mask])
    
    # SFDR: ratio of signal to largest spur (excluding DC)
    spur_bins = list(range(1, n//2))
    spur_powers = [ps[b] for b in spur_bins if b != sig_bin]
    max_spur = max(spur_powers) if spur_powers else 1e-30
    
    sndr = 10 * np.log10(sig_power / (noise_power + dist_power + 1e-30))
    snr  = 10 * np.log10(sig_power / (noise_power + 1e-30))
    sfdr = 10 * np.log10(sig_power / (max_spur + 1e-30))
    enob = (sndr - 1.76) / 6.02
    
    return {
        "ENOB": enob,
        "SNDR": sndr,
        "SNR":  snr,
        "SFDR": sfdr,
    }

def build_partial_weights(targets):
    """Build weights dict from calibration targets, using nominal for missing/invalid."""
    weights = dict(NOMINAL_WEIGHTS)  # Start with nominal
    
    # Map target stage to weight key
    stage_to_key = {6: "w6", 5: "w5", 4: "w4", 3: "w3", 2: "w2", 1: "w1", 0: "w0"}
    
    for t in targets:
        key = stage_to_key.get(t.get("stage", -1))
        if key and t.get("valid", 0):
            weights[key] = t["weight"]
    
    return weights

def compute_all_dynamic(all_results):
    """Compute dynamic performance for all scenarios."""
    perf = {}
    
    for scenario in SCENARIO_LABELS:
        for calbp, label in [(0, "calon"), (1, "caloff")]:
            key = "{}_{}".format(scenario, label)
            result = all_results.get(key, {})
            
            if calbp == 0 and result.get("targets"):
                # Use partial calibrated weights from targets
                w = build_partial_weights(result["targets"])
            else:
                w = dict(NOMINAL_WEIGHTS)
            
            # Convert float weights to numeric
            w_clean = {}
            for k, v in w.items():
                try:
                    w_clean[k] = float(v)
                except (ValueError, TypeError):
                    w_clean[k] = float(NOMINAL_WEIGHTS.get(k, 0))
            
            codes, fin, fs = sar_quantize_sine(w_clean)
            metrics = fft_metrics(codes, fin, fs)
            perf[key] = metrics
    
    return perf


# ============================================================
# Plotting
# ============================================================

def generate_all_plots(all_results, perf):
    """Generate all academic-quality figures."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import rcParams
    
    os.makedirs(PLOTS_DIR, exist_ok=True)
    
    rcParams.update({
        'font.family': 'serif',
        'font.serif': ['Times New Roman', 'DejaVu Serif'],
        'font.size': 10,
        'axes.labelsize': 11,
        'axes.titlesize': 12,
        'legend.fontsize': 8,
        'figure.dpi': 150,
        'savefig.dpi': 300,
        'savefig.bbox': 'tight',
        'savefig.pad_inches': 0.05,
    })
    
    scenarios = list(SCENARIO_LABELS.keys())
    s_labels = list(SCENARIO_LABELS.values())
    
    # ================================================================
    # Figure 1: CDAC Structure Diagram
    # ================================================================
    fig1, ax = plt.subplots(1, 1, figsize=(12, 5))
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 8)
    ax.axis('off')
    ax.set_title('Binary Bridge CDAC Structure (H=65, $C_B$=2$C_u$)', 
                 fontsize=13, fontweight='bold', pad=15)
    
    # Low array
    low_box = plt.Rectangle((0.3, 4.5), 6.2, 2.5, fill=False, edgecolor='#2c3e50', 
                            linewidth=2, linestyle='-')
    ax.add_patch(low_box)
    ax.text(3.4, 5.5, 'Low Segment ($C_L$=63$C_u$)', ha='center', fontsize=9, 
            fontweight='bold', color='#2c3e50')
    low_caps = ['1C', '2C', '4C', '8C', '16C', '32C']
    low_eff  = ['W=2', 'W=4', 'W=8', 'W=16', 'W=32', 'W=64']
    for i, (cap, eff) in enumerate(zip(low_caps, low_eff)):
        x = 0.8 + i * 1.0
        ax.plot([x-0.1, x-0.1], [2.5, 3.5], 'k-', lw=2)
        ax.plot([x+0.1, x+0.1], [2.5, 3.5], 'k-', lw=2)
        ax.text(x, 2.2, cap, ha='center', fontsize=7.5)
        ax.text(x, 2.0, eff, ha='center', fontsize=6.5, color='#7f8c8d')
    
    # Bridge
    ax.plot([7.5, 7.5], [0.5, 2.5], 'k-', lw=1.5)
    ax.plot([7.35, 7.35], [0.5, 1.5], 'k-', lw=2)
    ax.plot([7.65, 7.65], [0.5, 1.5], 'k-', lw=2)
    ax.text(7.5, 3.0, '$C_B$=2$C_u$', ha='center', fontsize=10, color='#c0392b',
            fontweight='bold', bbox=dict(boxstyle='round', facecolor='#fadbd8', alpha=0.8))
    
    # Bridge ratio annotation
    ax.annotate(r'$\alpha=\frac{C_B}{C_B+C_L}=\frac{2}{65}$',
                xy=(7.5, 0.5), xytext=(10.5, 0.8),
                fontsize=8, ha='center', color='#c0392b',
                arrowprops=dict(arrowstyle='->', color='#c0392b', lw=1))
    
    # High array
    high_box = plt.Rectangle((8.5, 4.5), 8.8, 2.5, fill=False, edgecolor='#27ae60', 
                             linewidth=2, linestyle='-')
    ax.add_patch(high_box)
    ax.text(12.9, 5.5, 'High Segment ($C_H$=64$C_u$, H=65)', ha='center', fontsize=9,
            fontweight='bold', color='#27ae60')
    high_caps = ['1C$_A$', '1C$_R$', '2C', '4C', '8C', '16C', '32C']
    high_eff  = ['W=65', 'W=65', 'W=130', 'W=260', 'W=520', 'W=1040', 'W=2080']
    for i, (cap, eff) in enumerate(zip(high_caps, high_eff)):
        x = 9.0 + i * 1.2
        ax.plot([x-0.1, x-0.1], [2.5, 3.5], 'k-', lw=2)
        ax.plot([x+0.1, x+0.1], [2.5, 3.5], 'k-', lw=2)
        ax.text(x, 2.2, cap, ha='center', fontsize=7.5)
        ax.text(x, 2.0, eff, ha='center', fontsize=6.5, color='#7f8c8d')
    
    # Top-plate labels
    ax.text(3.4, 0.3, '$V_{PD}$', ha='center', fontsize=10, color='#2c3e50', fontweight='bold')
    ax.text(12.9, 0.3, '$V_P$ (comparator input)', ha='center', fontsize=10, color='#27ae60', fontweight='bold')
    
    # Summary box
    summary = (r'$\Sigma W$ = 4287 > 4095  |  14 decisions  |  '
               r'Redundancy: $W_{1C_A}+W_{1C_R}=130>65$  |  '
               r'$C_B=2C_u$ (integer)')
    ax.text(9.0, 0.0, summary, ha='center', fontsize=7.5,
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.7))
    
    fig1.savefig(os.path.join(PLOTS_DIR, 'fig1_cdac_structure.pdf'))
    fig1.savefig(os.path.join(PLOTS_DIR, 'fig1_cdac_structure.png'))
    plt.close(fig1)
    print("  [fig1] CDAC structure diagram saved.")
    
    # ================================================================
    # Figure 2: Calibration Scheme
    # ================================================================
    fig2, ax = plt.subplots(1, 1, figsize=(12, 8))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 13)
    ax.axis('off')
    ax.set_title('Huang-Style Direct Recursive Calibration (7 Targets)', 
                 fontsize=13, fontweight='bold', pad=15)
    
    targets = [
        ("H1C-A", "W=65",  "Direct\ncalDAC only", "#e74c3c"),
        ("H1C-R", "W=65",  "Recursive\n(+H1C-A)", "#e67e22"),
        ("H2C",   "W=130", "Recursive\n(+H1C-A,R)", "#f1c40f"),
        ("H4C",   "W=260", "Recursive\n(+H2C,H1C)", "#2ecc71"),
        ("H8C",   "W=520", "Recursive\n(+H4C..H1C)", "#3498db"),
        ("H16C",  "W=1040","Recursive\n(+H8C..H1C)", "#9b59b6"),
        ("H32C",  "W=2080","Recursive\n(+H16C..H1C)","#1abc9c"),
    ]
    
    y_positions = [11.5, 10, 8.5, 7, 5.5, 4, 2.5]
    
    for idx, (name, wstr, method, color) in enumerate(targets):
        y = y_positions[idx]
        
        # Target box
        box = plt.Rectangle((0.5, y-0.4), 3.5, 0.8, fill=True, facecolor=color, 
                           alpha=0.25, edgecolor=color, linewidth=2)
        ax.add_patch(box)
        ax.text(2.25, y, "T{}: {} ({})".format(idx, name, wstr), 
               ha='center', va='center', fontsize=9, fontweight='bold')
        
        # Arrow
        if idx > 0:
            ax.annotate('', xy=(0.5, y+0.5), xytext=(0.5, y_positions[idx-1]-0.5),
                       arrowprops=dict(arrowstyle='->', color='gray', lw=1.5))
        
        # Method
        method_box = plt.Rectangle((4.5, y-0.4), 3.0, 0.8, fill=True, 
                                   facecolor='#ecf0f1', edgecolor='#bdc3c7', linewidth=1)
        ax.add_patch(method_box)
        ax.text(6.0, y, method, ha='center', va='center', fontsize=7.5)
        
        # D+/D-
        dp_box = plt.Rectangle((8.0, y-0.4), 2.5, 0.8, fill=True,
                               facecolor='#d5f5e3', edgecolor='#27ae60', linewidth=1)
        ax.add_patch(dp_box)
        ax.text(9.25, y, "$D^+$, $D^-$\n(32 pairs)", ha='center', va='center', fontsize=7.5)
        
        # Weight store
        w_box = plt.Rectangle((11.0, y-0.4), 3.0, 0.8, fill=True,
                              facecolor='#fef9e7', edgecolor='#f39c12', linewidth=1)
        ax.add_patch(w_box)
        wlabel = "$\\hat{{W}}_{{{}}}$ stored".format(6-idx)
        ax.text(12.5, y, wlabel, 
               ha='center', va='center', fontsize=8)
        
        # Arrow between boxes
        ax.annotate('', xy=(8.0, y), xytext=(7.5, y),
                   arrowprops=dict(arrowstyle='->', color='gray', lw=1))
        ax.annotate('', xy=(11.0, y), xytext=(10.5, y),
                   arrowprops=dict(arrowstyle='->', color='gray', lw=1))
    
    # Formula box
    formula = (r'$\hat{W}_k = \frac{\sum D^+ + \sum |D^-|}{2 \cdot N_{pairs}}$'
               r'$\quad\sigma_W = \sigma_n/8\quad$'
               r'$V_{OS}$ cancelled by D$^+$/D$^-$ subtraction')
    ax.text(2.0, 0.8, formula, fontsize=9, ha='center',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    
    fig2.savefig(os.path.join(PLOTS_DIR, 'fig2_calibration_scheme.pdf'))
    fig2.savefig(os.path.join(PLOTS_DIR, 'fig2_calibration_scheme.png'))
    plt.close(fig2)
    print("  [fig2] Calibration scheme diagram saved.")
    
    # ================================================================
    # Figure 3: Performance Comparison (ENOB / SFDR / SNR)
    # ================================================================
    fig3, axes = plt.subplots(1, 3, figsize=(15, 5.5))
    
    x = np.arange(len(scenarios))
    width = 0.35
    
    enob_cal, enob_unc = [], []
    sfdr_cal, sfdr_unc = [], []
    snr_cal,  snr_unc  = [], []
    
    for sc in scenarios:
        ek = "{}_{}".format(sc, "calon")
        uk = "{}_{}".format(sc, "caloff")
        em = perf.get(ek, {"ENOB": 0, "SFDR": 0, "SNR": 0})
        um = perf.get(uk, {"ENOB": 0, "SFDR": 0, "SNR": 0})
        enob_cal.append(em["ENOB"])
        enob_unc.append(um["ENOB"])
        sfdr_cal.append(em["SFDR"])
        sfdr_unc.append(um["SFDR"])
        snr_cal.append(em["SNR"])
        snr_unc.append(um["SNR"])
    
    colors_cal = '#2ecc71'
    colors_unc = '#e74c3c'
    
    # ENOB
    ax = axes[0]
    ax.bar(x - width/2, enob_cal, width, label='Calibrated', color=colors_cal, 
           edgecolor='black', lw=0.5)
    ax.bar(x + width/2, enob_unc, width, label='Uncalibrated', color=colors_unc, 
           edgecolor='black', lw=0.5)
    ax.set_ylabel('ENOB (bits)', fontweight='bold')
    ax.set_title('ENOB Comparison', fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(s_labels, fontsize=7)
    ax.legend(loc='lower right')
    ax.grid(axis='y', alpha=0.3)
    ax.axhline(y=12.0, color='gray', linestyle='--', alpha=0.5, lw=0.8)
    ax.text(0.02, 12.05, 'Ideal 12-bit', fontsize=6, color='gray', va='bottom')
    
    # SFDR
    ax = axes[1]
    ax.bar(x - width/2, sfdr_cal, width, label='Calibrated', color=colors_cal, 
           edgecolor='black', lw=0.5)
    ax.bar(x + width/2, sfdr_unc, width, label='Uncalibrated', color=colors_unc, 
           edgecolor='black', lw=0.5)
    ax.set_ylabel('SFDR (dB)', fontweight='bold')
    ax.set_title('SFDR Comparison', fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(s_labels, fontsize=7)
    ax.legend(loc='lower right')
    ax.grid(axis='y', alpha=0.3)
    
    # SNR
    ax = axes[2]
    ax.bar(x - width/2, snr_cal, width, label='Calibrated', color=colors_cal, 
           edgecolor='black', lw=0.5)
    ax.bar(x + width/2, snr_unc, width, label='Uncalibrated', color=colors_unc, 
           edgecolor='black', lw=0.5)
    ax.set_ylabel('SNR (dB)', fontweight='bold')
    ax.set_title('SNR Comparison', fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(s_labels, fontsize=7)
    ax.legend(loc='lower right')
    ax.grid(axis='y', alpha=0.3)
    
    fig3.suptitle('Calibrated vs. Uncalibrated Performance Across Mismatch Scenarios', 
                  fontweight='bold', fontsize=13)
    fig3.tight_layout()
    fig3.savefig(os.path.join(PLOTS_DIR, 'fig3_performance_comparison.pdf'))
    fig3.savefig(os.path.join(PLOTS_DIR, 'fig3_performance_comparison.png'))
    plt.close(fig3)
    print("  [fig3] Performance comparison saved.")
    
    # ================================================================
    # Figure 4: Calibrated Weight Error
    # ================================================================
    fig4, axes = plt.subplots(2, 3, figsize=(15, 9))
    axes = axes.flatten()
    
    weight_keys = ['w0', 'w1', 'w2', 'w3', 'w4', 'w5', 'w6']
    weight_labels = ['H32C', 'H16C', 'H8C', 'H4C', 'H2C', 'H1C-R', 'H1C-A']
    nom_vals = [NOMINAL_WEIGHTS[k] for k in weight_keys]
    
    for idx, sc in enumerate(scenarios[:6]):
        ax = axes[idx]
        key = "{}_{}".format(sc, "calon")
        result = all_results.get(key, {})
        weights = result.get("weights", {})
        
        if not weights:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes)
            ax.set_title(sc)
            continue
        
        cal_vals = [float(weights.get(k, nom_vals[i])) for i, k in enumerate(weight_keys)]
        errors = [(c - n) / n * 100 for c, n in zip(cal_vals, nom_vals)]
        
        bar_colors = ['#27ae60' if abs(e) < 1 else '#f39c12' if abs(e) < 5 else '#e74c3c' 
                     for e in errors]
        bars = ax.bar(range(len(weight_labels)), errors, color=bar_colors, 
                     edgecolor='black', lw=0.5)
        ax.axhline(y=0, color='black', lw=0.5)
        ax.set_xticks(range(len(weight_labels)))
        ax.set_xticklabels(weight_labels, fontsize=7, rotation=45)
        ax.set_ylabel('Weight Error (%)', fontsize=9)
        ax.set_title(SCENARIO_LABELS.get(sc, sc).replace('\n', ' '), fontsize=10)
        ax.grid(axis='y', alpha=0.3)
        
        # Add value labels on bars
        for bar, err in zip(bars, errors):
            if abs(err) > 0.5:
                ax.text(bar.get_x() + bar.get_width()/2, 
                       bar.get_height() + 0.3 * np.sign(err),
                       '{:.1f}%'.format(err), ha='center', fontsize=6)
    
    # Hide extra subplot if < 6 scenarios
    for idx in range(len(scenarios), len(axes)):
        axes[idx].set_visible(False)
    
    fig4.suptitle('Calibrated Weight Error vs. Nominal (High-Side Capacitors)', 
                  fontweight='bold', fontsize=13)
    fig4.tight_layout()
    fig4.savefig(os.path.join(PLOTS_DIR, 'fig4_weight_error.pdf'))
    fig4.savefig(os.path.join(PLOTS_DIR, 'fig4_weight_error.png'))
    plt.close(fig4)
    print("  [fig4] Weight error analysis saved.")
    
    # ================================================================
    # Figure 5: INL/DNL Curves
    # ================================================================
    fig5, axes = plt.subplots(2, 3, figsize=(16, 9))
    
    plot_scenarios = ['ideal', 'mild_2pct', 'sev_5pct']
    
    for col, sc in enumerate(plot_scenarios):
        # Calibrated INL/DNL
        cal_key = "{}_{}".format(sc, "calon")
        result = all_results.get(cal_key, {})
        weights = result.get("weights", {})
        
        if weights:
            inl_cal, dnl_cal = compute_inl_dnl(weights)
        else:
            inl_cal, dnl_cal = np.array([]), np.array([])
        
        # Uncalibrated INL/DNL
        inl_unc, dnl_unc = compute_inl_dnl(NOMINAL_WEIGHTS)
        
        # INL subplot
        ax_inl = axes[0, col]
        if len(inl_cal) > 0:
            ax_inl.plot(inl_cal, lw=0.5, color='#3498db', alpha=0.7, label='Calibrated')
        if len(inl_unc) > 0:
            ax_inl.plot(inl_unc, lw=0.5, color='#e74c3c', alpha=0.7, label='Uncalibrated')
        ax_inl.axhline(y=0, color='gray', linestyle='--', lw=0.5)
        ax_inl.set_ylabel('INL (LSB)', fontsize=9)
        ax_inl.set_title('INL - {}'.format(SCENARIO_LABELS.get(sc, sc).replace('\n', ' ')), 
                        fontsize=10)
        ax_inl.grid(alpha=0.3)
        ax_inl.legend(fontsize=7)
        
        # DNL subplot
        ax_dnl = axes[1, col]
        if len(dnl_cal) > 0:
            ax_dnl.plot(dnl_cal, lw=0.5, color='#3498db', alpha=0.7, label='Calibrated')
        if len(dnl_unc) > 0:
            ax_dnl.plot(dnl_unc, lw=0.5, color='#e74c3c', alpha=0.7, label='Uncalibrated')
        ax_dnl.axhline(y=0, color='gray', linestyle='--', lw=0.5)
        ax_dnl.set_ylabel('DNL (LSB)', fontsize=9)
        ax_dnl.set_xlabel('Code', fontsize=9)
        ax_dnl.set_title('DNL - {}'.format(SCENARIO_LABELS.get(sc, sc).replace('\n', ' ')), 
                        fontsize=10)
        ax_dnl.grid(alpha=0.3)
        ax_dnl.legend(fontsize=7)
    
    fig5.suptitle('INL/DNL Analysis: Calibrated vs. Uncalibrated', 
                  fontweight='bold', fontsize=13)
    fig5.tight_layout()
    fig5.savefig(os.path.join(PLOTS_DIR, 'fig5_inl_dnl.pdf'))
    fig5.savefig(os.path.join(PLOTS_DIR, 'fig5_inl_dnl.png'))
    plt.close(fig5)
    print("  [fig5] INL/DNL curves saved.")
    
    # ================================================================
    # Figure 6: Calibration Target Measurements
    # ================================================================
    fig6, axes = plt.subplots(2, 3, figsize=(15, 9))
    axes = axes.flatten()
    
    for idx, sc in enumerate(scenarios[:6]):
        ax = axes[idx]
        key = "{}_{}".format(sc, "calon")
        result = all_results.get(key, {})
        targets = result.get("targets", [])
        
        if not targets:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes)
            ax.set_title(sc)
            continue
        
        names = [t["name"] for t in targets]
        measured = [t["weight"] for t in targets]
        nominal = [t["wnom"] for t in targets]
        valid = [t["valid"] for t in targets]
        
        x = np.arange(len(names))
        w = 0.35
        
        bar_colors = ['#2ecc71' if v else '#e74c3c' for v in valid]
        bars = ax.bar(x - w/2, nominal, w, label='Nominal', color='#bdc3c7', 
                     edgecolor='black', lw=0.5)
        bars2 = ax.bar(x + w/2, measured, w, label='Measured', color=bar_colors, 
                      edgecolor='black', lw=0.5)
        
        ax.set_xticks(x)
        ax.set_xticklabels(names, fontsize=7, rotation=30)
        ax.set_ylabel('Weight (LSB)', fontsize=9)
        ax.set_title(SCENARIO_LABELS.get(sc, sc).replace('\n', ' '), fontsize=10)
        ax.legend(fontsize=7)
        ax.grid(axis='y', alpha=0.3)
        
        # Mark invalid targets
        for i, v in enumerate(valid):
            if not v:
                ax.annotate('FAIL', xy=(x[i] + w/2, measured[i]), 
                           xytext=(x[i] + w/2, measured[i] + max(nominal)*0.05),
                           fontsize=6, color='#e74c3c', ha='center',
                           arrowprops=dict(arrowstyle='->', color='#e74c3c', lw=0.5))
    
    fig6.suptitle('Calibration Target Measurements: Nominal vs. Measured', 
                  fontweight='bold', fontsize=13)
    fig6.tight_layout()
    fig6.savefig(os.path.join(PLOTS_DIR, 'fig6_calibration_targets.pdf'))
    fig6.savefig(os.path.join(PLOTS_DIR, 'fig6_calibration_targets.png'))
    plt.close(fig6)
    print("  [fig6] Calibration target measurements saved.")
    
    print("\nAll figures generated in: {}".format(PLOTS_DIR))


# ============================================================
# Performance Summary Table
# ============================================================

def generate_summary_table(all_results, perf):
    """Generate and print performance summary table."""
    print("\n" + "=" * 80)
    print("PERFORMANCE SUMMARY")
    print("=" * 80)
    header = "{:<14} {:>4} {:>8} {:>10} {:>9} {:>10}".format(
        "Scenario", "Cal", "ENOB", "SNDR(dB)", "SNR(dB)", "SFDR(dB)")
    print(header)
    print("-" * 80)
    
    table_rows = []
    
    for sc in SCENARIO_LABELS:
        for calbp, label in [(0, "ON"), (1, "OFF")]:
            key = "{}_{}".format(sc, "calon" if calbp == 0 else "caloff")
            m = perf.get(key, {"ENOB": 0, "SNDR": 0, "SNR": 0, "SFDR": 0})
            
            sc_display = SCENARIO_LABELS[sc].replace('\n', ' ') if label == "ON" else ""
            print("{:<14} {:>4} {:>8.2f} {:>10.2f} {:>9.2f} {:>10.2f}".format(
                sc_display, label, m["ENOB"], m["SNDR"], m["SNR"], m["SFDR"]))
            
            table_rows.append({
                "scenario": sc,
                "cal": label,
                "ENOB": m["ENOB"],
                "SNDR": m["SNDR"],
                "SNR": m["SNR"],
                "SFDR": m["SFDR"],
            })
    
    # Compute improvement
    print("\n--- Calibration Improvement ---")
    for sc in SCENARIO_LABELS:
        ck = "{}_{}".format(sc, "calon")
        uk = "{}_{}".format(sc, "caloff")
        ce = perf.get(ck, {"ENOB": 0})
        ue = perf.get(uk, {"ENOB": 0})
        delta = ce["ENOB"] - ue["ENOB"]
        print("  {}: delta_ENOB = {:+.2f} bits".format(
            SCENARIO_LABELS[sc].replace('\n', ' '), delta))
    
    # Save CSV
    csv_path = os.path.join(RESULTS_DIR, "performance_summary.csv")
    with open(csv_path, 'w') as f:
        f.write("Scenario,Calibration,ENOB,SNDR_dB,SNR_dB,SFDR_dB\n")
        for row in table_rows:
            f.write("{},{},{:.2f},{:.2f},{:.2f},{:.2f}\n".format(
                row["scenario"], row["cal"], row["ENOB"], row["SNDR"], 
                row["SNR"], row["SFDR"]))
    print("\nSummary saved to: {}".format(csv_path))


# ============================================================
# Main
# ============================================================

def main():
    print("=" * 60)
    print("SAR ADC Calibration Analysis & Plotting")
    print("=" * 60)
    
    # Load results
    print("\n[1] Loading simulation results...")
    all_results = load_all_results()
    print("  Loaded {} result sets.".format(len(all_results)))
    
    if not all_results:
        print("  No results found. Check sim_results/ directory.")
        # Generate plots with nominal data anyway
        all_results = {}
    
    # Compute dynamic performance
    print("\n[2] Computing dynamic performance...")
    perf = compute_all_dynamic(all_results)
    for k, v in sorted(perf.items()):
        print("  {}: ENOB={:.2f} SFDR={:.1f} SNR={:.1f}".format(
            k, v["ENOB"], v["SFDR"], v["SNR"]))
    
    # Generate plots
    print("\n[3] Generating academic-quality figures...")
    generate_all_plots(all_results, perf)
    
    # Summary table
    print("\n[4] Performance summary...")
    generate_summary_table(all_results, perf)
    
    print("\nDone.")


if __name__ == "__main__":
    main()
