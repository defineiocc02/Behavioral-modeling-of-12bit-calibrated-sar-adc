#!/usr/bin/env python3
"""
SAR ADC Mismatch Calibration Campaign

Runs Spectre simulations for multiple mismatch scenarios with
calibration ON (CAL_BYPASS=0) and OFF (CAL_BYPASS=1), then
extracts calibration weights and performance metrics.

Usage:
    python run_mismatch_campaign.py [--quick] [--scenario SCENARIO]

Scenarios:
    ideal       - All capacitors nominal (baseline)
    mild_1pct   - Random ±1% mismatch on high-side caps
    mild_3pct   - Random ±3% mismatch on high-side caps  
    severe_5pct - Random ±5% mismatch on high-side caps
    systematic  - Systematic P/N differential mismatch (±5%)
    all         - Run all scenarios (default)
"""

import os
import sys
import json
import time
import argparse
import numpy as np
from pathlib import Path
from datetime import datetime

# Add project path
PROJECT_DIR = Path(__file__).resolve().parent.parent
SIM_DIR = PROJECT_DIR / "sim"
RESULTS_DIR = PROJECT_DIR / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# ==============================================================================
# Mismatch scenarios: (name, {param: value, ...})
# Each dict has the mismatch multipliers for high-side capacitors (md8-mu14)
# ==============================================================================

SCENARIOS = {
    "ideal": {
        "description": "Ideal capacitors (all nominal)",
        "params": {
            "md8": 1.0, "mu8": 1.0,
            "md9": 1.0, "mu9": 1.0,
            "md10": 1.0, "mu10": 1.0,
            "md11": 1.0, "mu11": 1.0,
            "md12": 1.0, "mu12": 1.0,
            "md13": 1.0, "mu13": 1.0,
            "md14": 1.0, "mu14": 1.0,
        }
    },
    "mild_1pct": {
        "description": "Mild ±1% random mismatch on high-side caps",
        "params": {
            # P-side: alternating +1%/-1%
            "md8": 1.01, "mu8": 0.99,
            "md9": 0.99, "mu9": 1.01,
            "md10": 1.01, "mu10": 0.99,
            "md11": 0.99, "mu11": 1.01,
            "md12": 1.01, "mu12": 0.99,
            "md13": 0.99, "mu13": 1.01,
            "md14": 1.01, "mu14": 0.99,
        }
    },
    "mild_3pct": {
        "description": "Moderate ±3% random mismatch on high-side caps",
        "params": {
            "md8": 1.03, "mu8": 0.97,
            "md9": 0.97, "mu9": 1.03,
            "md10": 1.03, "mu10": 0.97,
            "md11": 0.97, "mu11": 1.03,
            "md12": 1.03, "mu12": 0.97,
            "md13": 0.97, "mu13": 1.03,
            "md14": 1.03, "mu14": 0.97,
        }
    },
    "severe_5pct": {
        "description": "Severe ±5% random mismatch on high-side caps",
        "params": {
            "md8": 1.05, "mu8": 0.95,
            "md9": 0.95, "mu9": 1.05,
            "md10": 1.05, "mu10": 0.95,
            "md11": 0.95, "mu11": 1.05,
            "md12": 1.05, "mu12": 0.95,
            "md13": 0.95, "mu13": 1.05,
            "md14": 1.05, "mu14": 0.95,
        }
    },
    "systematic": {
        "description": "Systematic P/N differential mismatch (all P +5%, all N -5%)",
        "params": {
            "md8": 1.05, "mu8": 0.95,
            "md9": 1.05, "mu9": 0.95,
            "md10": 1.05, "mu10": 0.95,
            "md11": 1.05, "mu11": 0.95,
            "md12": 1.05, "mu12": 0.95,
            "md13": 1.05, "mu13": 0.95,
            "md14": 1.05, "mu14": 0.95,
        }
    },
}

# ==============================================================================
# Calibration weight extraction from log
# ==============================================================================

def parse_cal_weights(log_text):
    """Extract calibrated weights from Spectre log output."""
    weights = None
    valid = None
    sat = None
    
    for line in log_text.split('\n'):
        if 'CAL WEIGHTS={' in line:
            # Parse: CAL WEIGHTS={2088.5,1044.25,522.125,...}
            start = line.index('{') + 1
            end = line.index('}')
            vals = line[start:end].split(',')
            weights = [float(v.strip()) for v in vals]
        if 'VALID=' in line:
            try:
                valid = int(line.split('VALID=')[1].split()[0])
            except:
                pass
        if 'SAT=' in line:
            try:
                sat = int(line.split('SAT=')[1].split()[0])
            except:
                pass
    
    return weights, valid, sat


def parse_cal_log(log_text):
    """Parse full calibration log to extract per-target measurements."""
    results = []
    for line in log_text.split('\n'):
        if 'CAL TARGET' in line and 'Wnom=' in line:
            parts = line.split()
            info = {}
            for p in parts:
                if '=' in p:
                    k, v = p.split('=')
                    info[k] = v
            results.append(info)
    return results


# ==============================================================================
# Performance metrics from analytical transfer function
# ==============================================================================

def compute_transfer_function(weights, vdd=1.8, n_bits=12):
    """
    Compute ADC transfer function for given weights.
    Returns array of code boundaries (in volts).
    """
    # weights: [w0(MSB), w1, ..., w13(terminal)]
    n_levels = 2 ** n_bits
    
    # Total weight span
    total_w = sum(weights)
    redundancy_offset = (total_w - (2**n_bits - 1)) / 2
    
    # Generate all possible code combos (too many for 14 bits! 16384 combos)
    # Use iterative approach: compute code for each input voltage
    
    # For efficiency, compute thresholds directly
    # Each code boundary is at: sum(w_i * r_i) - redundancy_offset
    # where r_i is the SAR decision pattern
    
    # Since we have 14 bits but only 12-bit output, we compute the 4096 thresholds
    # by iterating over all possible SAR decision patterns
    
    # Use DAC-like approach: compute ideal output for each code
    thresholds = np.zeros(n_levels + 1)
    
    # Simple approach: use SAR model
    for code in range(n_levels):
        # Compute the DAC output for this code
        dac_out = 0
        remaining = code
        # This is a rough approximation - proper model needs SAR decisions
        # For analytical comparison, use nominal transfer
        dac_out = code * (vdd / (2**n_bits))
        thresholds[code + 1] = dac_out
    
    return thresholds


def compute_inl_dnl_analytical(physical_weights, calibrated_weights, nominal_weights, n_bits=12):
    """
    Analytically compute INL/DNL from known physical weights vs calibrated/nominal weights.
    
    physical_weights: actual capacitor weights (from mismatch parameters)
    calibrated_weights: weights measured by calibration
    nominal_weights: ideal/nominal weights
    
    Returns: (inl_cal, dnl_cal, inl_nom, dnl_nom) arrays
    """
    n_levels = 2 ** n_bits
    
    # Total weight sums
    total_phys = sum(physical_weights)
    total_cal = sum(calibrated_weights)
    total_nom = sum(nominal_weights)
    
    # Redundancy offsets
    offset_phys = (total_phys - (n_levels - 1)) / 2
    offset_cal = (total_cal - (n_levels - 1)) / 2
    offset_nom = (total_nom - (n_levels - 1)) / 2
    
    # For 14-decision SAR, compute the actual transfer function
    # by simulating the SAR algorithm with each set of weights
    
    def sar_decode(weights, offset, n_decisions=14):
        """Generate all possible DAC outputs for given weights."""
        # This is brute force for 14 bits = 16384 combos
        n_combos = 1 << n_decisions
        dac_outputs = np.zeros(n_combos)
        for i in range(n_combos):
            dac = 0
            for j in range(n_decisions):
                if i & (1 << (n_decisions - 1 - j)):
                    dac += weights[j]
            dac_outputs[i] = (dac - offset)
        
        # Sort and remove duplicates to get the actual transfer function
        dac_sorted = np.sort(dac_outputs)
        
        # Map to 0..4095
        # The SAR decision space maps to a subset of 0..4095
        # Find thresholds that map codes to the output
        return dac_sorted
    
    phys_dac = sar_decode(physical_weights, offset_phys)
    cal_dac = sar_decode(calibrated_weights, offset_cal)
    nom_dac = sar_decode(nominal_weights, offset_nom)
    
    # Compute ideal LSB
    lsb_ideal = (phys_dac[-1] - phys_dac[0]) / (n_levels - 1)
    
    # For each code 0..4095, find closest DAC output and compute error
    inl_cal = np.zeros(n_levels)
    dnl_cal = np.zeros(n_levels)
    inl_nom = np.zeros(n_levels)
    dnl_nom = np.zeros(n_levels)
    
    # Simplified: use the dac outputs as code boundaries
    # This is approximate since 14-bit SAR maps non-uniformly to 12-bit output
    
    # Better approach: compute ideal ramp response
    ramp_codes_ideal = np.arange(n_levels, dtype=float)
    
    # For calibrated: use calibrated weights
    # For nominal: use nominal weights
    # Actual transfer function uses physical weights
    
    # Just compute the difference between decoded values
    # This gives a first-order INL estimate
    for code in range(n_levels):
        # Ideal LSB position
        ideal_val = code * lsb_ideal + phys_dac[0]
        
        # Find actual code that would be output for this input
        # with calibrated weights
        cal_decoded = ideal_val  # placeholder
        inl_cal[code] = 0  # placeholder
        inl_nom[code] = 0
    
    return inl_cal, dnl_cal, inl_nom, dnl_nom


def compute_dynamic_perf_analytical(physical_weights, calibrated_weights, 
                                     nominal_weights, n_bits=12, n_samples=4096):
    """
    Analytically compute ENOB/SFDR/SNR from weight sets.
    Uses SAR ADC model with sine wave input.
    """
    # Generate sine wave input
    fs = 10e6  # 10 MHz sample rate
    fin = fs * 127 / n_samples  # Coherent sampling
    t = np.arange(n_samples) / fs
    vin = 0.9 * (1 + np.sin(2 * np.pi * fin * t)) / 2 * 1.8  # 0.9*VDD amplitude
    
    # Quantize with each weight set
    vref = 1.8
    
    def sar_quantize(v, weights):
        """Single-ended SAR ADC model."""
        n_decisions = len(weights)
        total_w = sum(weights)
        offset = (total_w - (2**n_bits - 1)) / 2
        
        codes = np.zeros(len(v), dtype=int)
        
        for i, vin_val in enumerate(v):
            # Normalize input to weight domain
            target = vin_val / vref * (2**n_bits - 1)
            
            # SAR binary search using weights
            # This is approximate - proper model needs actual CDAC equation
            dac_sum = 0
            for j in range(n_decisions):
                trial = dac_sum + weights[j]
                if trial - offset <= target:
                    dac_sum = trial
            
            code = int(dac_sum - offset)
            code = max(0, min(code, (2**n_bits) - 1))
            codes[i] = code
        
        return codes
    
    # Quantize with physical (actual), calibrated, and nominal weights
    codes_phys = sar_quantize(vin, physical_weights)
    codes_cal = sar_quantize(vin, calibrated_weights)
    codes_nom = sar_quantize(vin, nominal_weights)
    
    def compute_fft_metrics(codes, n_bits=12):
        """Compute ENOB, SFDR, SNR from ADC codes using FFT."""
        n = len(codes)
        
        # Remove DC
        codes_ac = codes - np.mean(codes)
        
        # Window (Hanning)
        window = np.hanning(n)
        codes_win = codes_ac * window
        
        # FFT
        fft = np.fft.rfft(codes_win) / (n / 2)
        mag = np.abs(fft)
        mag[0] = 0  # Remove DC
        
        # Signal power (find peak near fin)
        fin_bin = int(127)  # Coherent bin
        signal_power = mag[fin_bin] ** 2
        
        # Harmonic bins
        harmonic_bins = []
        for k in range(2, 8):
            h_bin = (k * 127) % n
            if h_bin <= n // 2:
                harmonic_bins.append(h_bin)
        
        harmonic_power = sum(mag[h] ** 2 for h in harmonic_bins if h < len(mag))
        
        # Noise power (all other bins)
        noise_bins = [i for i in range(1, len(mag)) 
                      if i != fin_bin and i not in harmonic_bins]
        noise_power = sum(mag[i] ** 2 for i in noise_bins)
        
        # Distortion = harmonic power
        distortion_power = harmonic_power
        
        # SNR, SFDR, SNDR
        if noise_power > 0:
            snr = 10 * np.log10(signal_power / noise_power)
        else:
            snr = 100
        
        if distortion_power > 0:
            sfdr = 10 * np.log10(signal_power / max(mag[h] ** 2 for h in harmonic_bins if h < len(mag)))
        else:
            sfdr = 100
        
        total_noise_dist = noise_power + distortion_power
        if total_noise_dist > 0:
            sndr = 10 * np.log10(signal_power / total_noise_dist)
        else:
            sndr = 100
        
        enob = (sndr - 1.76) / 6.02
        
        return {
            'SNR_dB': round(snr, 2),
            'SFDR_dB': round(sfdr, 2),
            'SNDR_dB': round(sndr, 2),
            'ENOB_bit': round(enob, 2),
        }
    
    metrics_phys = compute_fft_metrics(codes_phys)
    metrics_cal = compute_fft_metrics(codes_cal)
    metrics_nom = compute_fft_metrics(codes_nom)
    
    return {
        'physical_ideal': metrics_phys,
        'calibrated': metrics_cal,
        'nominal_uncal': metrics_nom,
    }


# ==============================================================================
# Main simulation campaign
# ==============================================================================

def build_param_string(params):
    """Build parameter string for Spectre command line."""
    parts = []
    for k, v in params.items():
        parts.append(f"+{k}={v}")
    return ' '.join(parts)


def run_calibration_simulation(scenario_name, scenario_info, cal_bypass=0):
    """
    Run calibration simulation for one scenario.
    Returns (success, weights, log_text).
    """
    from virtuoso_bridge.spectre.runner import SpectreSimulator, spectre_mode_args
    
    sim = SpectreSimulator.from_env(
        spectre_args=spectre_mode_args("ax"),
        work_dir=str(RESULTS_DIR / f"cal_{scenario_name}_{'off' if cal_bypass else 'on'}"),
    )
    
    # Build parameters
    params = dict(scenario_info["params"])
    params["cal_bypass"] = cal_bypass
    
    # Upload testbench and VA files
    va_files = [
        str(SIM_DIR / "DEC_CAL_PHY_HUANG_V6.va"),
        str(SIM_DIR / "SWITCH_CAL.va"),
        str(SIM_DIR / "CAL_CMP_TB.va"),
        str(SIM_DIR / "SAR_LOGIC_0716.va"),
    ]
    
    tb_file = str(SIM_DIR / "tb_huang_cal_ramp.scs")
    
    print(f"\n{'='*60}")
    print(f"Scenario: {scenario_name} | Cal {'ON' if cal_bypass==0 else 'OFF'}")
    print(f"Description: {scenario_info['description']}")
    print(f"{'='*60}")
    
    try:
        result = sim.run_simulation(tb_file, {
            "include_files": va_files,
            "params": params,
        })
        
        if result.ok:
            # Parse calibration weights from log
            log_file = Path(result.metadata.get("output_dir", "")) / "tb_huang_cal_ramp.log"
            if log_file.exists():
                log_text = log_file.read_text()
            else:
                log_text = ""
            
            weights, valid, sat = parse_cal_weights(log_text)
            
            if weights:
                print(f"  Weights: {[f'{w:.2f}' for w in weights]}")
                print(f"  VALID={valid} SAT={sat}")
            else:
                print(f"  Warning: No weight data found in log")
            
            return True, weights, log_text
        else:
            print(f"  Error: {result.errors}")
            return False, None, str(result.errors)
    
    except Exception as e:
        print(f"  Exception: {e}")
        return False, None, str(e)


def run_simulation_direct(scenario_name, scenario_info, cal_bypass=0):
    """
    Run simulation by uploading files to VM and executing spectre directly.
    This is a more robust fallback method.
    """
    import subprocess
    import tempfile
    
    print(f"\n{'='*60}")
    print(f"Scenario: {scenario_name} | Cal {'ON' if cal_bypass==0 else 'OFF'}")
    print(f"Description: {scenario_info['description']}")
    print(f"{'='*60}")
    
    # Build parameter arguments
    param_args = []
    for k, v in scenario_info["params"].items():
        param_args.append(f"+{k}={v}")
    param_args.append(f"+cal_bypass={cal_bypass}")
    
    # Build command
    work_dir = RESULTS_DIR / f"cal_{scenario_name}_{'off' if cal_bypass else 'on'}"
    work_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy files to work directory
    import shutil
    va_files = [
        "DEC_CAL_PHY_HUANG_V6.va",
        "SWITCH_CAL.va",
        "CAL_CMP_TB.va",
        "SAR_LOGIC_0716.va",
        "tb_huang_cal_ramp.scs",
    ]
    
    for f in va_files:
        src = SIM_DIR / f
        dst = work_dir / f
        if src.exists():
            shutil.copy2(src, dst)
    
    # Run spectre
    cmd = ["spectre", "tb_huang_cal_ramp.scs"] + param_args + [
        "+escchars", "-format", "psfxl",
        "-raw", str(work_dir / "psf"),
        "-log", str(work_dir / "tb_huang_cal_ramp.log")
    ]
    
    print(f"  Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=str(work_dir),
            capture_output=True,
            text=True,
            timeout=3600,  # 1 hour timeout
        )
        
        log_file = work_dir / "tb_huang_cal_ramp.log"
        if log_file.exists():
            log_text = log_file.read_text()
        else:
            log_text = result.stdout + "\n" + result.stderr
        
        weights, valid, sat = parse_cal_weights(log_text)
        
        if weights:
            print(f"  Weights: {[f'{w:.2f}' for w in weights]}")
            print(f"  VALID={valid} SAT={sat}")
        else:
            # Check for errors
            if "Error" in log_text or "ERROR" in log_text:
                error_lines = [l for l in log_text.split('\n') if 'rror' in l.lower()]
                print(f"  Errors: {error_lines[:5]}")
            print(f"  Warning: No weight data found in log")
        
        return result.returncode == 0, weights, log_text
    
    except subprocess.TimeoutExpired:
        print(f"  Error: Simulation timed out")
        return False, None, "TIMEOUT"
    except FileNotFoundError:
        print(f"  Error: spectre not found in PATH")
        return False, None, "SPECTRE_NOT_FOUND"
    except Exception as e:
        print(f"  Exception: {e}")
        return False, None, str(e)


# ==============================================================================
# Nominal weights for H=65 CDAC
# ==============================================================================
NOMINAL_WEIGHTS = [
    2080.0,  # w0:  H32C (stage 0)
    1040.0,  # w1:  H16C (stage 1)
    520.0,   # w2:  H8C  (stage 2)
    260.0,   # w3:  H4C  (stage 3)
    130.0,   # w4:  H2C  (stage 4)
    65.0,    # w5:  H1C-R (stage 5)
    65.0,    # w6:  H1C-A (stage 6)
    64.0,    # w7:  L32C (stage 7, calDAC)
    32.0,    # w8:  L16C (stage 8)
    16.0,    # w9:  L8C  (stage 9)
    8.0,     # w10: L4C  (stage 10)
    4.0,     # w11: L2C  (stage 11)
    2.0,     # w12: L1C  (stage 12)
    1.0,     # w13: terminal
]

def compute_actual_weights(scenario_params):
    """
    Compute actual physical weights from mismatch parameters.
    
    Capacitor mapping:
        md8/mu8:  H1C-A  (unity, effective weight 65)
        md9/mu9:  H1C-R  (unity, effective weight 65)
        md10/mu10: H2C   (2*C, effective weight 130)
        md11/mu11: H4C   (4*C, effective weight 260)
        md12/mu12: H8C   (8*C, effective weight 520)
        md13/mu13: H16C  (16*C, effective weight 1040)
        md14/mu14: H32C  (32*C, effective weight 2080)
    
    Differential effective weight = (P_cap + N_cap) / 2 * nominal_weight
    where P_cap is the P-side mismatch multiplier, N_cap is the N-side multiplier
    """
    p = scenario_params
    
    # Compute differential multiplier for each cap pair
    actual = list(NOMINAL_WEIGHTS)
    
    # High-side caps (index 0..6 map to weight positions)
    # w6 = H1C-A: md8/mu8
    actual[6] = NOMINAL_WEIGHTS[6] * (p["md8"] + p["mu8"]) / 2
    
    # w5 = H1C-R: md9/mu9
    actual[5] = NOMINAL_WEIGHTS[5] * (p["md9"] + p["mu9"]) / 2
    
    # w4 = H2C: md10/mu10
    actual[4] = NOMINAL_WEIGHTS[4] * (p["md10"] + p["mu10"]) / 2
    
    # w3 = H4C: md11/mu11
    actual[3] = NOMINAL_WEIGHTS[3] * (p["md11"] + p["mu11"]) / 2
    
    # w2 = H8C: md12/mu12
    actual[2] = NOMINAL_WEIGHTS[2] * (p["md12"] + p["mu12"]) / 2
    
    # w1 = H16C: md13/mu13
    actual[1] = NOMINAL_WEIGHTS[1] * (p["md13"] + p["mu13"]) / 2
    
    # w0 = H32C: md14/mu14
    actual[0] = NOMINAL_WEIGHTS[0] * (p["md14"] + p["mu14"]) / 2
    
    # Low-side caps (calDAC, w7..w12) and terminal (w13) are assumed ideal
    # (they're not part of mismatch sweep)
    
    return actual


def run_full_campaign(scenarios=None, quick=False):
    """Run full mismatch campaign."""
    if scenarios is None:
        scenarios = list(SCENARIOS.keys())
    elif isinstance(scenarios, str):
        scenarios = [scenarios]
    
    results = {}
    
    for scenario_name in scenarios:
        if scenario_name not in SCENARIOS:
            print(f"Unknown scenario: {scenario_name}")
            continue
        
        scenario_info = SCENARIOS[scenario_name]
        
        # Run calibration ON and OFF
        for cal_mode, cal_label in [(0, "ON"), (1, "OFF")]:
            success, weights, log_text = run_simulation_direct(
                scenario_name, scenario_info, cal_bypass=cal_mode
            )
            
            key = f"{scenario_name}_cal_{cal_label.lower()}"
            results[key] = {
                "scenario": scenario_name,
                "cal_mode": cal_label,
                "success": success,
                "weights": weights,
                "description": scenario_info["description"],
            }
        
        # Compute actual physical weights
        actual_weights = compute_actual_weights(scenario_info["params"])
        
        # Get calibrated weights from the CAL ON run
        cal_weights = results.get(f"{scenario_name}_cal_on", {}).get("weights")
        
        if cal_weights and actual_weights:
            # Compute weight errors
            print(f"\n--- Weight Analysis: {scenario_name} ---")
            labels = [
                "w0(H32C)", "w1(H16C)", "w2(H8C)", "w3(H4C)",
                "w4(H2C)", "w5(H1C-R)", "w6(H1C-A)", 
                "w7(L32C)", "w8(L16C)", "w9(L8C)",
                "w10(L4C)", "w11(L2C)", "w12(L1C)", "w13(term)"
            ]
            
            print(f"{'Weight':<12} {'Nominal':>8} {'Actual':>8} {'Calibrated':>10} {'Cal Err':>8}")
            print("-" * 56)
            for i in range(min(14, len(cal_weights), len(actual_weights), len(NOMINAL_WEIGHTS))):
                nom = NOMINAL_WEIGHTS[i]
                act = actual_weights[i]
                cal = cal_weights[i]
                cal_err = cal - act
                print(f"{labels[i]:<12} {nom:>8.2f} {act:>8.2f} {cal:>10.4f} {cal_err:>+8.4f}")
            
            # Compute performance
            perf = compute_dynamic_perf_analytical(
                actual_weights, cal_weights, NOMINAL_WEIGHTS
            )
            
            print(f"\n--- Performance: {scenario_name} ---")
            print(f"{'Metric':<12} {'Ideal':>8} {'Cal ON':>8} {'Cal OFF':>8}")
            print("-" * 42)
            for metric in ['ENOB_bit', 'SNDR_dB', 'SFDR_dB', 'SNR_dB']:
                ideal = perf['physical_ideal'].get(metric, 'N/A')
                cal = perf['calibrated'].get(metric, 'N/A')
                nom = perf['nominal_uncal'].get(metric, 'N/A')
                print(f"{metric:<12} {ideal:>8} {cal:>8} {nom:>8}")
            
            results[f"{scenario_name}_perf"] = perf
    
    # Save results
    output_file = RESULTS_DIR / f"campaign_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    # Convert numpy values to native Python for JSON serialization
    def sanitize(obj):
        if isinstance(obj, dict):
            return {k: sanitize(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [sanitize(v) for v in obj]
        elif isinstance(obj, (np.integer,)):
            return int(obj)
        elif isinstance(obj, (np.floating,)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return obj
    
    with open(output_file, 'w') as f:
        json.dump(sanitize(results), f, indent=2, default=str)
    
    print(f"\nResults saved to: {output_file}")
    
    return results


# ==============================================================================
# CLI
# ==============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SAR ADC Mismatch Calibration Campaign")
    parser.add_argument("--scenario", type=str, default="all",
                        choices=["all", "ideal", "mild_1pct", "mild_3pct", 
                                "severe_5pct", "systematic"],
                        help="Scenario to run")
    parser.add_argument("--quick", action="store_true",
                        help="Quick mode: calibration only, skip ramp")
    parser.add_argument("--analyze-only", type=str, default=None,
                        help="Analyze existing results JSON file")
    
    args = parser.parse_args()
    
    if args.analyze_only:
        with open(args.analyze_only, 'r') as f:
            results = json.load(f)
        print(f"Loaded {len(results)} results from {args.analyze_only}")
        # Print summary
        for key, val in results.items():
            if key.endswith("_perf"):
                print(f"\n{key}:")
                for metric, v in val.items():
                    print(f"  {metric}: {v}")
    else:
        if args.scenario == "all":
            scenarios = list(SCENARIOS.keys())
        else:
            scenarios = [args.scenario]
        
        results = run_full_campaign(scenarios, quick=args.quick)
