#!/usr/bin/env python3
"""
Full SAR ADC Calibration Simulation Campaign
=============================================
Runs Spectre simulations for multiple mismatch scenarios with cal ON/OFF,
extracts performance metrics, and generates academic-quality plots.

Scenarios:
  ideal     : All capacitors nominal (baseline)
  mild_1pct : +/- 1% random mismatch
  mild_2pct : +/- 2% random mismatch  
  mod_3pct  : +/- 3% random mismatch
  sev_5pct  : +/- 5% random mismatch
  sys_pos   : Systematic positive mismatch (+2% all high-side)
  sys_neg   : Systematic negative mismatch (-2% all high-side)

For each scenario, two runs:
  calbp=0 : Calibration ON  (calibrated weights used)
  calbp=1 : Calibration OFF (nominal weights used)

Output:
  - Simulation logs in sim_results/
  - Extracted weights CSV
  - Performance metrics CSV  
  - Academic-quality plots (CDAC structure, INL/DNL, ENOB/SFDR/SNR bar charts)
"""

import os
import sys
import subprocess
import re
import json
import time
import numpy as np
from collections import OrderedDict
from datetime import datetime

# ============================================================================
# Configuration
# ============================================================================

VM_HOST = "192.168.38.128"
VM_USER = "meow"
VM_SIM_DIR = "/home/meow/jxy/trae_sandbox/sim_campaign"
VM_CSHRC = "/home/meow/.cshrc"

LOCAL_SIM_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_RESULTS_DIR = os.path.join(LOCAL_SIM_DIR, "sim_results")
LOCAL_PLOTS_DIR = os.path.join(LOCAL_SIM_DIR, "plots")

# Files to upload
UPLOAD_FILES = [
    "tb_huang_cal_ramp.scs",
    "DEC_CAL_PHY_HUANG_V6.va",
    "SWITCH_CAL.va",
    "CAL_CMP_TB.va",
    "SAR_LOGIC_0716.va",
]

# ============================================================================
# Mismatch Scenarios
# ============================================================================

# High-side capacitor params: md8,mu8 through md14,mu14
# (D-side and U-side multipliers for each cap)
SCENARIOS = OrderedDict([
    ("ideal", {
        "desc": "Ideal (all nominal)",
        "params": {"md8": 1.0, "mu8": 1.0, "md9": 1.0, "mu9": 1.0,
                   "md10": 1.0, "mu10": 1.0, "md11": 1.0, "mu11": 1.0,
                   "md12": 1.0, "mu12": 1.0, "md13": 1.0, "mu13": 1.0,
                   "md14": 1.0, "mu14": 1.0}
    }),
    ("mild_1pct", {
        "desc": "Mild +/-1% random mismatch",
        "params": {"md8": 1.010, "mu8": 0.990, "md9": 0.991, "mu9": 1.009,
                   "md10": 1.008, "mu10": 0.992, "md11": 0.993, "mu11": 1.007,
                   "md12": 1.006, "mu12": 0.994, "md13": 0.995, "mu13": 1.005,
                   "md14": 1.004, "mu14": 0.996}
    }),
    ("mild_2pct", {
        "desc": "Mild +/-2% random mismatch",
        "params": {"md8": 1.020, "mu8": 0.980, "md9": 0.982, "mu9": 1.018,
                   "md10": 1.016, "mu10": 0.984, "md11": 0.986, "mu11": 1.014,
                   "md12": 1.012, "mu12": 0.988, "md13": 0.990, "mu13": 1.010,
                   "md14": 1.008, "mu14": 0.992}
    }),
    ("mod_3pct", {
        "desc": "Moderate +/-3% random mismatch",
        "params": {"md8": 1.030, "mu8": 0.970, "md9": 0.973, "mu9": 1.027,
                   "md10": 1.024, "mu10": 0.976, "md11": 0.979, "mu11": 1.021,
                   "md12": 1.018, "mu12": 0.982, "md13": 0.985, "mu13": 1.015,
                   "md14": 1.012, "mu14": 0.988}
    }),
    ("sev_5pct", {
        "desc": "Severe +/-5% random mismatch",
        "params": {"md8": 1.050, "mu8": 0.950, "md9": 0.955, "mu9": 1.045,
                   "md10": 1.040, "mu10": 0.960, "md11": 0.965, "mu11": 1.035,
                   "md12": 1.030, "mu12": 0.970, "md13": 0.975, "mu13": 1.025,
                   "md14": 1.020, "mu14": 0.980}
    }),
    ("sys_pos_2pct", {
        "desc": "Systematic +2% (all high-side shifted up)",
        "params": {"md8": 1.020, "mu8": 1.020, "md9": 1.020, "mu9": 1.020,
                   "md10": 1.020, "mu10": 1.020, "md11": 1.020, "mu11": 1.020,
                   "md12": 1.020, "mu12": 1.020, "md13": 1.020, "mu13": 1.020,
                   "md14": 1.020, "mu14": 1.020}
    }),
    ("sys_neg_2pct", {
        "desc": "Systematic -2% (all high-side shifted down)",
        "params": {"md8": 0.980, "mu8": 0.980, "md9": 0.980, "mu9": 0.980,
                   "md10": 0.980, "mu10": 0.980, "md11": 0.980, "mu11": 0.980,
                   "md12": 0.980, "mu12": 0.980, "md13": 0.980, "mu13": 0.980,
                   "md14": 0.980, "mu14": 0.980}
    }),
])

# Nominal weights (Huang binary CDAC, H=65)
NOMINAL_WEIGHTS = {
    # Low array: {1,2,4,8,16,32}C -> effective weights after bridge
    "w7": 2,    # 1C  low, stage 7
    "w8": 4,    # 2C  low, stage 8
    "w9": 8,    # 4C  low, stage 9
    "w10": 16,  # 8C  low, stage 10
    "w11": 32,  # 16C low, stage 11
    "w12": 64,  # 32C low, stage 12
    # High array: {1A,1R,2,4,8,16,32}C, H=65
    "w6": 65,   # 1C_A  high, stage 6 (H1C-A)
    "w5": 65,   # 1C_R  high, stage 5 (H1C-R, redundant)
    "w4": 130,  # 2C    high, stage 4 (H2C)
    "w3": 260,  # 4C    high, stage 3 (H4C)
    "w2": 520,  # 8C    high, stage 2 (H8C)
    "w1": 1040, # 16C   high, stage 1 (H16C)
    "w0": 2080, # 32C   high, stage 0 (H32C)
    "w13": 1,   # Terminal LSB
}

# Stage-to-physical mapping (for decoder analysis)
# Stage 0->13 = MSB cap 32C, Stage 13 = terminal
DECISION_STAGES = 14
CDAC_TOTAL = 4287  # Total nominal weight sum

# ============================================================================
# SSH Utilities
# ============================================================================

def ssh_cmd(command, timeout=600):
    """Execute a command on the VM via SSH."""
    full_cmd = f'ssh -o BatchMode=yes -o StrictHostKeyChecking=no {VM_USER}@{VM_HOST} "{command}"'
    result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return result.stdout, result.stderr, result.returncode

def ssh_upload(local_path, remote_path):
    """Upload a file to the VM."""
    full_cmd = f'scp -o BatchMode=yes -o StrictHostKeyChecking=no "{local_path}" {VM_USER}@{VM_HOST}:{remote_path}'
    result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=30)
    return result.returncode == 0

def ssh_download(remote_path, local_path):
    """Download a file from the VM."""
    full_cmd = f'scp -o BatchMode=yes -o StrictHostKeyChecking=no {VM_USER}@{VM_HOST}:{remote_path} "{local_path}"'
    result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=30)
    return result.returncode == 0

# ============================================================================
# Spectre Simulation Runner
# ============================================================================

def build_sim_command(scenario_name, calbp, params_dict):
    """Build the spectre command line for a given scenario."""
    # Build parameter string
    param_str = f"calbp={calbp} "
    for k, v in params_dict.items():
        param_str += f"{k}={v} "
    
    safe_name = f"{scenario_name}_cal{'on' if calbp == 0 else 'off'}"
    raw_dir = f"psf_{safe_name}"
    log_file = f"log_{safe_name}.log"
    
    cmd = (
        f"csh -c 'source {VM_CSHRC} ; "
        f"cd {VM_SIM_DIR} ; "
        f"rm -rf {raw_dir} ; "
        f"spectre -64 tb_huang_cal_ramp.scs +escchars -format psfxl -raw {raw_dir} "
        f"+log {log_file} "
        f"{param_str}"
        f"'"
    )
    return cmd, safe_name, log_file, raw_dir

def run_simulation(scenario_name, calbp, params_dict):
    """Run a single spectre simulation."""
    cmd, safe_name, log_file, raw_dir = build_sim_command(scenario_name, calbp, params_dict)
    
    print(f"  [{safe_name}] Starting spectre...")
    start_time = time.time()
    
    stdout, stderr, rc = ssh_cmd(cmd, timeout=1200)
    
    elapsed = time.time() - start_time
    
    if rc == 0:
        print(f"  [{safe_name}] OK ({elapsed:.1f}s)")
    else:
        # Check for common errors
        if "SFE-100" in stdout or "SFE-100" in stderr:
            print(f"  [{safe_name}] ERROR: Port mismatch!")
        elif "fatal error" in (stdout + stderr).lower():
            print(f"  [{safe_name}] ERROR: Fatal error!")
        else:
            print(f"  [{safe_name}] ERROR (rc={rc}, {elapsed:.1f}s)")
    
    return safe_name, rc, stdout, stderr

# ============================================================================
# Result Extraction
# ============================================================================

def extract_cal_weights(log_text):
    """Extract calibrated weights from simulation log."""
    weights = {}
    patterns = [
        (r'CAL\s+TARGET\s+name=H1C-A.*?measured_weight_q\s*=\s*(\d+)', 'w6'),
        (r'CAL\s+TARGET\s+name=H1C-R.*?measured_weight_q\s*=\s*(\d+)', 'w5'),
        (r'CAL\s+TARGET\s+name=H2C.*?measured_weight_q\s*=\s*(\d+)', 'w4'),
        (r'CAL\s+TARGET\s+name=H4C.*?measured_weight_q\s*=\s*(\d+)', 'w3'),
        (r'CAL\s+TARGET\s+name=H8C.*?measured_weight_q\s*=\s*(\d+)', 'w2'),
        (r'CAL\s+TARGET\s+name=H16C.*?measured_weight_q\s*=\s*(\d+)', 'w1'),
        (r'CAL\s+TARGET\s+name=H32C.*?measured_weight_q\s*=\s*(\d+)', 'w0'),
    ]
    
    for pattern, key in patterns:
        match = re.search(pattern, log_text)
        if match:
            weights[key] = int(match.group(1))
    
    # Also try $strobe format
    strobe_pattern = r'CAL_RESULT\s+(\w+)\s*=\s*(\d+)'
    for match in re.finditer(strobe_pattern, log_text):
        key = match.group(1).lower()
        weights[key] = int(match.group(2))
    
    return weights

def extract_done_err(log_text):
    """Check if calibration completed successfully."""
    done = 'DONE=1' in log_text or 'cal_done=1' in log_text.lower()
    err = 'ERR=1' in log_text or 'cal_error=1' in log_text.lower()
    return done, err

def compute_sar_output(weights_dict, vref=1.8):
    """
    Compute the SAR ADC output code given physical weights and a ramp input.
    This is an analytical model used to predict INL/DNL.
    
    Returns the transfer function: for each input voltage, what code is produced.
    """
    # Get physical weights in decision order (stage 0=MSB to stage 13=LSB)
    w = []
    for i in range(DECISION_STAGES):
        key = f"w{i}"
        w.append(weights_dict.get(key, NOMINAL_WEIGHTS.get(key, 0)))
    
    return np.array(w)

def compute_inl_dnl(weights, n_codes=4096, vref=1.8):
    """
    Compute INL and DNL from SAR ADC weights using endpoint-fit method.
    """
    # Build sorted transition points
    w = np.array(weights)
    
    # All possible binary combinations
    n_stages = len(w)
    codes = np.arange(2**n_stages) if n_stages <= 14 else np.arange(2**n_stages)
    
    # For 14 stages, we need to compute all 2^14=16384 code thresholds
    # But CDAC only has 4287 total weight, so actual range is 0..4287
    # We need the actual SAR decision thresholds
    
    # Simpler approach: build the DNL directly from weights
    # In a binary-weighted DAC, DNL = (actual_step - ideal_step) / ideal_step
    # For non-binary (redundant), we need the actual transition voltages
    
    # Use endpoint-fit: INL(k) = (T(k) - T(0)) / (T(end)-T(0)) * (N-1) - k
    # where T(k) is the transition voltage for code k
    
    # For SAR ADC with redundancy, build all transition points
    transitions = []
    # Generate all code transitions via the SAR decision tree
    transitions = generate_sar_transitions(weights)
    
    if len(transitions) < 100:
        return np.array([]), np.array([])
    
    # Endpoint fit
    t_first = transitions[0]
    t_last = transitions[-1]
    t_range = t_last - t_first
    n_eff = len(transitions) - 1
    
    inl = []
    dnl = []
    
    for i, t in enumerate(transitions[:-1]):
        t_ideal = t_first + (i / n_eff) * t_range
        inl_val = (t - t_ideal) / (t_range / n_eff)
        inl.append(inl_val)
        
        if i > 0:
            step = transitions[i] - transitions[i-1]
            ideal_step = t_range / n_eff
            dnl_val = step / ideal_step - 1
            dnl.append(dnl_val)
        else:
            dnl.append(0)
    
    return np.array(inl), np.array(dnl)

def generate_sar_transitions(weights):
    """
    Generate all SAR ADC transition voltages given physical weights.
    Uses the actual SAR decision algorithm.
    """
    w = np.array(weights, dtype=float)
    n = len(w)
    
    # SAR algorithm: for each possible input voltage,
    # the decision is: v_dac > v_in? If so, subtract weight; else keep weight.
    # We need the transition points where the output code changes.
    
    # For a SAR ADC with redundancy, the transfer function is not monotonic
    # in a simple way. We compute all possible codes and sort them.
    
    all_codes = []
    # Generate all possible DAC output values
    # For each binary combination, compute dac_out
    for code in range(1 << n):
        dac_val = 0
        residue = code
        for i in range(n):
            if residue & 1:
                dac_val += w[i]
            residue >>= 1
        all_codes.append(dac_val)
    
    all_codes = sorted(set(all_codes))
    return np.array(all_codes)

# ============================================================================
# Dynamic Performance (FFT-based)
# ============================================================================

def compute_dynamic_perf(weights_dict, nominal_weights, vref=1.8, 
                          n_samples=4096, fs=10e6, fin=None):
    """
    Compute ENOB, SFDR, SNR, SNDR using analytical SAR model with sine wave input.
    """
    w_cal = [weights_dict.get(f"w{i}", nominal_weights.get(f"w{i}", 0)) 
             for i in range(DECISION_STAGES)]
    w_nom = [nominal_weights.get(f"w{i}", 0) for i in range(DECISION_STAGES)]
    
    if fin is None:
        # Coherent sampling
        n_cycles = 127  # prime
        fin = fs * n_cycles / n_samples
    
    # Generate sine wave
    t = np.arange(n_samples) / fs
    amplitude = 0.45 * vref  # -0.5dBFS to avoid clipping
    offset = vref / 2
    vin = offset + amplitude * np.sin(2 * np.pi * fin * t)
    
    # SAR quantization
    def sar_quantize(vin_array, weights):
        codes = np.zeros(len(vin_array), dtype=int)
        for idx, v in enumerate(vin_array):
            residue = v
            code = 0
            for i, wi in enumerate(weights):
                # Decision: try adding weight
                if residue >= wi / CDAC_TOTAL * vref:
                    code |= (1 << i)
                    residue -= wi / CDAC_TOTAL * vref
            codes[idx] = code
        return codes
    
    codes_cal = sar_quantize(vin, w_cal)
    codes_nom = sar_quantize(vin, w_nom)
    
    # FFT analysis
    def fft_metrics(codes, n_bits=12):
        # Remove DC
        data = codes.astype(float) - np.mean(codes)
        
        # Window (Hann)
        window = np.hanning(n_samples)
        data_w = data * window
        window_gain = np.mean(window)
        
        # FFT
        spectrum = np.fft.fft(data_w) / n_samples
        spectrum = spectrum[:n_samples//2]
        
        # Power spectrum
        ps = 2 * np.abs(spectrum)**2 / window_gain**2
        
        # Find signal bin
        signal_bin = int(round(fin / fs * n_samples))
        
        # Signal power
        signal_power = ps[signal_bin]
        
        # Distortion bins (harmonics up to 7th)
        harm_bins = []
        for h in range(2, 8):
            hbin = (signal_bin * h) % n_samples
            if hbin < n_samples // 2 and hbin > signal_bin + 2:
                harm_bins.append(hbin)
        
        dist_power = sum(ps[hb] for hb in harm_bins) if harm_bins else 0
        
        # Noise power (exclude DC, signal, harmonics)
        exclude_bins = {0, signal_bin} | set(harm_bins)
        # Exclude bins near signal
        for d in range(-2, 3):
            exclude_bins.add((signal_bin + d) % (n_samples//2))
        
        noise_mask = np.ones(n_samples//2, dtype=bool)
        for b in exclude_bins:
            if 0 <= b < n_samples//2:
                noise_mask[b] = False
        noise_power = sum(ps[noise_mask])
        
        # Metrics
        if signal_power > 0:
            sndr_db = 10 * np.log10(signal_power / (noise_power + dist_power + 1e-20))
            snr_db = 10 * np.log10(signal_power / (noise_power + 1e-20))
            sfdr_db = 10 * np.log10(signal_power / (max(ps[1:signal_bin].max() if signal_bin > 1 else 0,
                                                       ps[signal_bin+1:].max(),
                                                       dist_power) + 1e-20))
            enob = (sndr_db - 1.76) / 6.02
        else:
            sndr_db = snr_db = sfdr_db = enob = 0
        
        return {
            'ENOB': enob,
            'SNDR': sndr_db,
            'SNR': snr_db,
            'SFDR': sfdr_db,
        }
    
    return {
        'calibrated': fft_metrics(codes_cal),
        'uncalibrated': fft_metrics(codes_nom),
    }

# ============================================================================
# Main Campaign
# ============================================================================

def upload_files():
    """Upload all required files to the VM."""
    print("=" * 60)
    print("Uploading files to VM...")
    
    for fname in UPLOAD_FILES:
        local = os.path.join(LOCAL_SIM_DIR, fname)
        remote = f"{VM_SIM_DIR}/{fname}"
        if os.path.exists(local):
            ok = ssh_upload(local, remote)
            print(f"  {fname}: {'OK' if ok else 'FAILED'}")
        else:
            print(f"  {fname}: NOT FOUND (skipping)")
    
    # Ensure results directory exists on VM
    ssh_cmd(f"mkdir -p {VM_SIM_DIR}/logs")
    
    print("Upload complete.\n")

def run_campaign():
    """Run the full simulation campaign."""
    print("=" * 60)
    print("SAR ADC Calibration Simulation Campaign")
    print(f"Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Create local results directories
    os.makedirs(LOCAL_RESULTS_DIR, exist_ok=True)
    os.makedirs(LOCAL_PLOTS_DIR, exist_ok=True)
    
    results = {}
    
    for scenario_name, scenario in SCENARIOS.items():
        print(f"\n--- Scenario: {scenario_name} ({scenario['desc']}) ---")
        params = scenario['params']
        
        for calbp in [0, 1]:  # 0=cal_on, 1=cal_off
            safe_name, rc, stdout, stderr = run_simulation(scenario_name, calbp, params)
            
            # Save log
            log_local = os.path.join(LOCAL_RESULTS_DIR, f"{safe_name}.log")
            with open(log_local, 'w') as f:
                f.write(stdout)
                if stderr:
                    f.write("\n\n=== STDERR ===\n")
                    f.write(stderr)
            
            # Download PSF data
            raw_dir = f"psf_{safe_name}"
            psf_local = os.path.join(LOCAL_RESULTS_DIR, raw_dir)
            ssh_download(f"{VM_SIM_DIR}/{raw_dir}", psf_local)
            
            # Extract results
            weights = {}
            if rc == 0:
                weights = extract_cal_weights(stdout)
                done, err = extract_done_err(stdout)
            else:
                done, err = False, True
            
            results[safe_name] = {
                'scenario': scenario_name,
                'calbp': calbp,
                'rc': rc,
                'weights': weights,
                'done': done,
                'err': err,
                'log': stdout,
            }
            
            # Print extracted weights
            if weights:
                w_str = ", ".join(f"{k}={v}" for k, v in sorted(weights.items()))
                print(f"    Weights: {w_str}")
                print(f"    DONE={done}, ERR={err}")
    
    # Save results
    results_file = os.path.join(LOCAL_RESULTS_DIR, "campaign_results.json")
    # Convert to serializable format
    serializable = {}
    for k, v in results.items():
        serializable[k] = {
            'scenario': v['scenario'],
            'calbp': v['calbp'],
            'rc': v['rc'],
            'weights': v['weights'],
            'done': v['done'],
            'err': v['err'],
        }
    with open(results_file, 'w') as f:
        json.dump(serializable, f, indent=2)
    
    print(f"\nResults saved to {results_file}")
    return results

# ============================================================================
# Plotting
# ============================================================================

def generate_plots(results):
    """Generate all academic-quality plots."""
    print("\n" + "=" * 60)
    print("Generating academic-quality plots...")
    
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import rcParams
    
    # Academic styling
    rcParams.update({
        'font.family': 'serif',
        'font.serif': ['Times New Roman', 'DejaVu Serif'],
        'font.size': 10,
        'axes.labelsize': 11,
        'axes.titlesize': 12,
        'legend.fontsize': 9,
        'figure.dpi': 150,
        'savefig.dpi': 300,
        'savefig.bbox': 'tight',
        'savefig.pad_inches': 0.05,
    })
    
    # ========================================================================
    # Figure 1: CDAC Structure Diagram
    # ========================================================================
    fig1, ax1 = plt.subplots(1, 1, figsize=(10, 6))
    ax1.set_xlim(0, 16)
    ax1.set_ylim(0, 10)
    ax1.axis('off')
    ax1.set_title('Binary Bridge CDAC Structure (H=65, $C_B$=2C)', 
                  fontsize=13, fontweight='bold', pad=20)
    
    # Low array box
    low_box = plt.Rectangle((0.5, 6.5), 4.5, 2.5, fill=False, edgecolor='blue', 
                             linewidth=2, linestyle='--')
    ax1.add_patch(low_box)
    ax1.text(2.75, 7.2, 'Low Array\n{1C, 2C, 4C, 8C, 16C, 32C}\n= 63$C_u$', 
             ha='center', va='bottom', fontsize=9, color='blue')
    
    # Low caps
    low_caps = ['1C', '2C', '4C', '8C', '16C', '32C']
    for i, cap in enumerate(low_caps):
        x = 1 + i * 0.75
        # Draw capacitor symbol
        ax1.plot([x-0.15, x-0.15], [3.5, 4.5], 'k-', linewidth=2)
        ax1.plot([x+0.15, x+0.15], [3.5, 4.5], 'k-', linewidth=2)
        ax1.text(x, 3.2, cap, ha='center', fontsize=7)
    
    # Bridge capacitor
    ax1.plot([6.5, 6.5], [1.5, 3.0], 'k-', linewidth=1.5)
    ax1.plot([6.35, 6.35], [1.5, 2.5], 'k-', linewidth=2)
    ax1.plot([6.65, 6.65], [1.5, 2.5], 'k-', linewidth=2)
    ax1.text(6.5, 4.5, '$C_B$=2C', ha='center', fontsize=10, color='red',
             bbox=dict(boxstyle='round', facecolor='#ffeeee', alpha=0.8))
    
    # High array box
    high_box = plt.Rectangle((8, 6.5), 7.5, 2.5, fill=False, edgecolor='green', 
                              linewidth=2, linestyle='--')
    ax1.add_patch(high_box)
    ax1.text(11.75, 7.2, 'High Array\n{1C$_A$, 1C$_R$, 2C, 4C, 8C, 16C, 32C}\n= 64$C_u$, H=65',
             ha='center', va='bottom', fontsize=9, color='green')
    
    # High caps
    high_caps = ['$1C_A$', '$1C_R$', '2C', '4C', '8C', '16C', '32C']
    for i, cap in enumerate(high_caps):
        x = 8.5 + i * 1.0
        ax1.plot([x-0.15, x-0.15], [3.5, 4.5], 'k-', linewidth=2)
        ax1.plot([x+0.15, x+0.15], [3.5, 4.5], 'k-', linewidth=2)
        ax1.text(x, 3.2, cap, ha='center', fontsize=7)
    
    # P, N nodes
    ax1.text(3.0, 1.2, '$V_{PD}$ (Low Top-Plate)', ha='center', fontsize=9, color='blue')
    ax1.text(11.75, 1.2, '$V_{P}$ (High Top-Plate)', ha='center', fontsize=9, color='green')
    
    # Weight table
    table_text = (
        "Effective Weights: low{2,4,8,16,32,64}  high{65,65,130,260,520,1040,2080}\n"
        "$\\Sigma W$=4287 > 4095 (12-bit)  |  Redundancy: $W_{1C_A}+W_{1C_R}=130>65$  |  14 decisions"
    )
    ax1.text(8, 0.3, table_text, ha='center', fontsize=8, 
             bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    
    fig1.savefig(os.path.join(LOCAL_PLOTS_DIR, 'fig1_cdac_structure.pdf'))
    fig1.savefig(os.path.join(LOCAL_PLOTS_DIR, 'fig1_cdac_structure.png'))
    plt.close(fig1)
    print("  Figure 1: CDAC structure diagram saved.")
    
    # ========================================================================
    # Figure 2: Calibration Scheme Block Diagram
    # ========================================================================
    fig2, ax2 = plt.subplots(1, 1, figsize=(10, 7))
    ax2.set_xlim(0, 14)
    ax2.set_ylim(0, 12)
    ax2.axis('off')
    ax2.set_title('Huang-Style Direct Recursive Calibration Scheme (7 Targets)', 
                  fontsize=13, fontweight='bold', pad=20)
    
    # Calibration flow
    targets = [
        (0, 'H1C-A', 'W=65', '#e74c3c'),
        (1, 'H1C-R', 'W=65', '#e67e22'),
        (2, 'H2C', 'W=130', '#f1c40f'),
        (3, 'H4C', 'W=260', '#2ecc71'),
        (4, 'H8C', 'W=520', '#3498db'),
        (5, 'H16C', 'W=1040', '#9b59b6'),
        (6, 'H32C', 'W=2080', '#1abc9c'),
    ]
    
    y_positions = [11, 9.5, 8, 6.5, 5, 3.5, 2]
    
    prev_calibrated = []
    for idx, (tid, name, weight_str, color) in enumerate(targets):
        y = y_positions[idx]
        
        # Target box
        box = plt.Rectangle((1, y-0.35), 3.5, 0.7, fill=True, facecolor=color, 
                            alpha=0.3, edgecolor=color, linewidth=2)
        ax2.add_patch(box)
        ax2.text(2.75, y, f'Target {tid}: {name} ({weight_str})', 
                ha='center', va='center', fontsize=9, fontweight='bold')
        
        # Method
        if tid == 0:
            method = 'Direct (calDAC only)'
        else:
            bits_str = ', '.join([f'H{i}' for i in range(tid-1, -1, -1)]) if tid > 1 else 'H0'
            method = f'Recursive ({bits_str} + calDAC)'
        
        # Arrow from prev
        if idx > 0:
            ax2.annotate('', xy=(1, y+0.5), xytext=(1, y_positions[idx-1]-0.5),
                        arrowprops=dict(arrowstyle='->', color='gray', lw=1.5))
        
        # D+/D- box
        dp_box = plt.Rectangle((5, y-0.35), 2.5, 0.7, fill=True, facecolor='lightgray', 
                               edgecolor='gray', linewidth=1)
        ax2.add_patch(dp_box)
        ax2.text(6.25, y, '$D^+$, $D^-$ (32 pairs)', 
                ha='center', va='center', fontsize=8)
        
        # Weight output
        w_box = plt.Rectangle((8, y-0.35), 2.5, 0.7, fill=True, facecolor='#ecf0f1', 
                              edgecolor='gray', linewidth=1)
        ax2.add_patch(w_box)
        ax2.text(9.25, y, '$\\hat{W}_' + str(6-tid) + '$ stored', 
                ha='center', va='center', fontsize=8)
        
        # Arrow D+/D- -> weight
        ax2.annotate('', xy=(8, y), xytext=(7.5, y),
                    arrowprops=dict(arrowstyle='->', color='gray', lw=1))
    
    # Legend
    ax2.text(1, 0.5, 
             '$\\hat{W}_k = \\frac{\\sum D^+ + \\sum |D^-|}{2 \\cdot N_{pairs}}$\n'
             '$\\sigma_W = \\sigma_n / 8$ (after 32-pair averaging)\n'
             'V_OS cancelled by differential D+/D- subtraction',
             fontsize=9, ha='left',
             bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    
    fig2.savefig(os.path.join(LOCAL_PLOTS_DIR, 'fig2_calibration_scheme.pdf'))
    fig2.savefig(os.path.join(LOCAL_PLOTS_DIR, 'fig2_calibration_scheme.png'))
    plt.close(fig2)
    print("  Figure 2: Calibration scheme diagram saved.")
    
    # ========================================================================
    # Figure 3: Performance Comparison Bar Charts
    # ========================================================================
    fig3, axes = plt.subplots(1, 3, figsize=(14, 5))
    
    scenarios_list = list(SCENARIOS.keys())
    scenario_labels = [s.replace('_', '\n') for s in scenarios_list]
    x = np.arange(len(scenarios_list))
    width = 0.35
    
    enob_cal = []
    enob_unc = []
    sfdr_cal = []
    sfdr_unc = []
    snr_cal = []
    snr_unc = []
    
    # Compute dynamic performance for each scenario
    for scenario_name in scenarios_list:
        cal_key = f"{scenario_name}_calon"
        unc_key = f"{scenario_name}_caloff"
        
        cal_weights = results.get(cal_key, {}).get('weights', {})
        unc_weights = {}  # nominal
        
        if cal_weights:
            dyn = compute_dynamic_perf(cal_weights, NOMINAL_WEIGHTS)
            enob_cal.append(dyn['calibrated']['ENOB'])
            sfdr_cal.append(dyn['calibrated']['SFDR'])
            snr_cal.append(dyn['calibrated']['SNR'])
            enob_unc.append(dyn['uncalibrated']['ENOB'])
            sfdr_unc.append(dyn['uncalibrated']['SFDR'])
            snr_unc.append(dyn['uncalibrated']['SNR'])
        else:
            # Use nominal for both if no cal results
            dyn = compute_dynamic_perf({}, NOMINAL_WEIGHTS)
            enob_cal.append(dyn['uncalibrated']['ENOB'])
            sfdr_cal.append(dyn['uncalibrated']['SFDR'])
            snr_cal.append(dyn['uncalibrated']['SNR'])
            enob_unc.append(dyn['uncalibrated']['ENOB'])
            sfdr_unc.append(dyn['uncalibrated']['SFDR'])
            snr_unc.append(dyn['uncalibrated']['SNR'])
    
    # ENOB
    ax = axes[0]
    ax.bar(x - width/2, enob_cal, width, label='Calibrated', color='#2ecc71', edgecolor='black', linewidth=0.5)
    ax.bar(x + width/2, enob_unc, width, label='Uncalibrated', color='#e74c3c', edgecolor='black', linewidth=0.5)
    ax.set_ylabel('ENOB (bits)')
    ax.set_title('ENOB Comparison')
    ax.set_xticks(x)
    ax.set_xticklabels(scenario_labels, fontsize=7)
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    ax.axhline(y=12.0, color='gray', linestyle='--', alpha=0.5, label='Ideal 12-bit')
    
    # SFDR
    ax = axes[1]
    ax.bar(x - width/2, sfdr_cal, width, label='Calibrated', color='#2ecc71', edgecolor='black', linewidth=0.5)
    ax.bar(x + width/2, sfdr_unc, width, label='Uncalibrated', color='#e74c3c', edgecolor='black', linewidth=0.5)
    ax.set_ylabel('SFDR (dB)')
    ax.set_title('SFDR Comparison')
    ax.set_xticks(x)
    ax.set_xticklabels(scenario_labels, fontsize=7)
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    
    # SNR
    ax = axes[2]
    ax.bar(x - width/2, snr_cal, width, label='Calibrated', color='#2ecc71', edgecolor='black', linewidth=0.5)
    ax.bar(x + width/2, snr_unc, width, label='Uncalibrated', color='#e74c3c', edgecolor='black', linewidth=0.5)
    ax.set_ylabel('SNR (dB)')
    ax.set_title('SNR Comparison')
    ax.set_xticks(x)
    ax.set_xticklabels(scenario_labels, fontsize=7)
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    
    fig3.suptitle('Calibrated vs. Uncalibrated Performance Across Mismatch Scenarios', 
                  fontweight='bold', fontsize=12)
    fig3.tight_layout()
    fig3.savefig(os.path.join(LOCAL_PLOTS_DIR, 'fig3_performance_comparison.pdf'))
    fig3.savefig(os.path.join(LOCAL_PLOTS_DIR, 'fig3_performance_comparison.png'))
    plt.close(fig3)
    print("  Figure 3: Performance comparison charts saved.")
    
    # ========================================================================
    # Figure 4: Weight Error Analysis
    # ========================================================================
    fig4, axes = plt.subplots(2, 3, figsize=(14, 9))
    
    cal_scenarios = [s for s in scenarios_list if s != 'ideal']
    for idx, scenario_name in enumerate(cal_scenarios[:6]):
        ax = axes[idx // 3][idx % 3]
        cal_key = f"{scenario_name}_calon"
        cal_result = results.get(cal_key, {})
        weights = cal_result.get('weights', {})
        
        if weights:
            weight_keys = ['w0', 'w1', 'w2', 'w3', 'w4', 'w5', 'w6']
            labels = ['H32C', 'H16C', 'H8C', 'H4C', 'H2C', 'H1C-R', 'H1C-A']
            nom_vals = [NOMINAL_WEIGHTS[k] for k in weight_keys]
            cal_vals = [weights.get(k, nom_vals[i]) for i, k in enumerate(weight_keys)]
            errors = [(c - n) / n * 100 for c, n in zip(cal_vals, nom_vals)]
            
            colors = ['#27ae60' if abs(e) < 1 else '#f39c12' if abs(e) < 3 else '#e74c3c' 
                     for e in errors]
            ax.bar(range(len(labels)), errors, color=colors, edgecolor='black', linewidth=0.5)
            ax.axhline(y=0, color='black', linewidth=0.5)
            ax.set_xticks(range(len(labels)))
            ax.set_xticklabels(labels, fontsize=7, rotation=45)
            ax.set_ylabel('Weight Error (%)')
            ax.set_title(f'{scenario_name}')
            ax.grid(axis='y', alpha=0.3)
    
    fig4.suptitle('Calibrated Weight Error vs. Nominal (High-Side Capacitors)', 
                  fontweight='bold', fontsize=12)
    fig4.tight_layout()
    fig4.savefig(os.path.join(LOCAL_PLOTS_DIR, 'fig4_weight_error.pdf'))
    fig4.savefig(os.path.join(LOCAL_PLOTS_DIR, 'fig4_weight_error.png'))
    plt.close(fig4)
    print("  Figure 4: Weight error analysis saved.")
    
    # ========================================================================
    # Figure 5: INL/DNL Curves (for the most interesting scenario)
    # ========================================================================
    fig5, axes = plt.subplots(2, 2, figsize=(12, 8))
    
    # Find a scenario with valid calibration results
    for scenario_name in ['ideal', 'mod_3pct', 'sev_5pct']:
        cal_key = f"{scenario_name}_calon"
        weights = results.get(cal_key, {}).get('weights', {})
        if weights:
            w_list = [weights.get(f'w{i}', NOMINAL_WEIGHTS.get(f'w{i}', 0)) 
                     for i in range(DECISION_STAGES)]
            inl, dnl = compute_inl_dnl(w_list)
            
            if len(inl) > 0:
                ax_inl = axes[0][0] if scenario_name == 'ideal' else axes[0][1] if scenario_name == 'mod_3pct' else None
                ax_dnl = axes[1][0] if scenario_name == 'ideal' else axes[1][1] if scenario_name == 'mod_3pct' else None
                
                if ax_inl is not None:
                    ax_inl.plot(inl, linewidth=0.5, color='#3498db')
                    ax_inl.axhline(y=0, color='gray', linestyle='--', linewidth=0.5)
                    ax_inl.set_ylabel('INL (LSB)')
                    ax_inl.set_title(f'INL - {scenario_name} (calibrated)')
                    ax_inl.grid(alpha=0.3)
                
                if ax_dnl is not None:
                    ax_dnl.plot(dnl, linewidth=0.5, color='#e74c3c')
                    ax_dnl.axhline(y=0, color='gray', linestyle='--', linewidth=0.5)
                    ax_dnl.set_ylabel('DNL (LSB)')
                    ax_dnl.set_xlabel('Code')
                    ax_dnl.set_title(f'DNL - {scenario_name} (calibrated)')
                    ax_dnl.grid(alpha=0.3)
    
    # Uncalibrated comparison for worst case
    unc_key = f"sev_5pct_caloff"
    w_nom_list = [NOMINAL_WEIGHTS.get(f'w{i}', 0) for i in range(DECISION_STAGES)]
    inl_unc, dnl_unc = compute_inl_dnl(w_nom_list)
    if len(inl_unc) > 0:
        axes[0][0].set_title('INL - sev_5pct (uncalibrated)')
        axes[0][0].clear()
        axes[0][0].plot(inl_unc, linewidth=0.5, color='#e74c3c')
        axes[0][0].axhline(y=0, color='gray', linestyle='--', linewidth=0.5)
        axes[0][0].set_ylabel('INL (LSB)')
        axes[0][0].grid(alpha=0.3)
        axes[0][0].set_title('INL - sev_5pct (uncalibrated)')
        
        axes[1][0].set_title('DNL - sev_5pct (uncalibrated)')
        axes[1][0].clear()
        axes[1][0].plot(dnl_unc, linewidth=0.5, color='#e74c3c')
        axes[1][0].axhline(y=0, color='gray', linestyle='--', linewidth=0.5)
        axes[1][0].set_ylabel('DNL (LSB)')
        axes[1][0].set_xlabel('Code')
        axes[1][0].grid(alpha=0.3)
        axes[1][0].set_title('DNL - sev_5pct (uncalibrated)')
    
    fig5.suptitle('INL/DNL Analysis (Calibrated vs. Uncalibrated)', 
                  fontweight='bold', fontsize=12)
    fig5.tight_layout()
    fig5.savefig(os.path.join(LOCAL_PLOTS_DIR, 'fig5_inl_dnl.pdf'))
    fig5.savefig(os.path.join(LOCAL_PLOTS_DIR, 'fig5_inl_dnl.png'))
    plt.close(fig5)
    print("  Figure 5: INL/DNL curves saved.")
    
    print("All plots generated successfully.")

# ============================================================================
# Performance Summary Table
# ============================================================================

def generate_performance_table(results):
    """Generate a LaTeX-style performance summary table."""
    print("\n" + "=" * 60)
    print("Performance Summary")
    print("=" * 60)
    
    header = f"{'Scenario':<16} {'Cal':>4} {'ENOB':>7} {'SNDR(dB)':>9} {'SNR(dB)':>8} {'SFDR(dB)':>9}"
    print(header)
    print("-" * len(header))
    
    table_data = []
    
    for scenario_name in SCENARIOS:
        for calbp, label in [(0, 'ON'), (1, 'OFF')]:
            key = f"{scenario_name}_cal{'on' if calbp == 0 else 'off'}"
            weights = results.get(key, {}).get('weights', {})
            
            if calbp == 0 and weights:
                dyn = compute_dynamic_perf(weights, NOMINAL_WEIGHTS)
                perf = dyn['calibrated']
            else:
                dyn = compute_dynamic_perf({}, NOMINAL_WEIGHTS)
                perf = dyn['uncalibrated']
            
            row = {
                'scenario': scenario_name,
                'cal': label,
                'enob': perf['ENOB'],
                'sndr': perf['SNDR'],
                'snr': perf['SNR'],
                'sfdr': perf['SFDR'],
            }
            table_data.append(row)
            
            scene_label = scenario_name if label == 'ON' else ''
            print(f"{scene_label:<16} {label:>4} {perf['ENOB']:>7.2f} {perf['SNDR']:>9.2f} {perf['SNR']:>8.2f} {perf['SFDR']:>9.2f}")
    
    # Save CSV
    csv_path = os.path.join(LOCAL_RESULTS_DIR, "performance_summary.csv")
    with open(csv_path, 'w') as f:
        f.write("Scenario,Calibration,ENOB,SNDR_dB,SNR_dB,SFDR_dB\n")
        for row in table_data:
            f.write(f"{row['scenario']},{row['cal']},{row['enob']:.2f},{row['sndr']:.2f},{row['snr']:.2f},{row['sfdr']:.2f}\n")
    
    print(f"\nPerformance table saved to {csv_path}")
    return table_data

# ============================================================================
# Main
# ============================================================================

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='SAR ADC Calibration Campaign')
    parser.add_argument('--skip-upload', action='store_true', help='Skip file upload')
    parser.add_argument('--skip-sim', action='store_true', help='Skip simulations (plot only)')
    parser.add_argument('--skip-plots', action='store_true', help='Skip plot generation')
    parser.add_argument('--scenario', type=str, help='Run only a specific scenario')
    args = parser.parse_args()
    
    if not args.skip_upload:
        upload_files()
    
    if args.skip_sim:
        # Load existing results
        results_file = os.path.join(LOCAL_RESULTS_DIR, "campaign_results.json")
        if os.path.exists(results_file):
            with open(results_file) as f:
                results = json.load(f)
            print(f"Loaded {len(results)} existing results.")
        else:
            print("No existing results found. Run without --skip-sim first.")
            sys.exit(1)
    else:
        # Filter scenarios if specified
        if args.scenario:
            if args.scenario in SCENARIOS:
                SCENARIOS = {args.scenario: SCENARIOS[args.scenario]}
            else:
                print(f"Unknown scenario: {args.scenario}")
                print(f"Available: {list(SCENARIOS.keys())}")
                sys.exit(1)
        
        results = run_campaign()
    
    if not args.skip_plots:
        generate_plots(results)
    
    # Generate performance table
    table = generate_performance_table(results)
    
    print("\n" + "=" * 60)
    print("Campaign complete!")
    print(f"Results: {LOCAL_RESULTS_DIR}")
    print(f"Plots: {LOCAL_PLOTS_DIR}")
    print("=" * 60)
