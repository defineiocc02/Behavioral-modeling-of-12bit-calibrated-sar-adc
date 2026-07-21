#!/usr/bin/env python
"""Run SAR ADC calibration campaign on VM. Python 2 compatible."""
import os, sys, subprocess, time

SIM_DIR = "/home/meow/jxy/trae_sandbox/sim_campaign"

SCENARIOS = {
    "ideal":       "md8=1.0 mu8=1.0 md9=1.0 mu9=1.0 md10=1.0 mu10=1.0 md11=1.0 mu11=1.0 md12=1.0 mu12=1.0 md13=1.0 mu13=1.0 md14=1.0 mu14=1.0",
    "mild_2pct":   "md8=1.020 mu8=0.980 md9=0.982 mu9=1.018 md10=1.016 mu10=0.984 md11=0.986 mu11=1.014 md12=1.012 mu12=0.988 md13=0.990 mu13=1.010 md14=1.008 mu14=0.992",
    "sev_5pct":    "md8=1.050 mu8=0.950 md9=0.955 mu9=1.045 md10=1.040 mu10=0.960 md11=0.965 mu11=1.035 md12=1.030 mu12=0.970 md13=0.975 mu13=1.025 md14=1.020 mu14=0.980",
    "sys_pos_2pct":"md8=1.020 mu8=1.020 md9=1.020 mu9=1.020 md10=1.020 mu10=1.020 md11=1.020 mu11=1.020 md12=1.020 mu12=1.020 md13=1.020 mu13=1.020 md14=1.020 mu14=1.020",
    "sys_neg_2pct":"md8=0.980 mu8=0.980 md9=0.980 mu9=0.980 md10=0.980 mu10=0.980 md11=0.980 mu11=0.980 md12=0.980 mu12=0.980 md13=0.980 mu13=0.980 md14=0.980 mu14=0.980",
}

def run_one(scenario, calbp):
    label = "calon" if calbp == 0 else "caloff"
    safe_name = "{}_{}".format(scenario, label)
    log_file = "log_{}.log".format(safe_name)
    raw_dir = "psf_{}".format(safe_name)
    params = SCENARIOS[scenario]
    
    # Skip if already done
    log_path = os.path.join(SIM_DIR, log_file)
    if os.path.exists(log_path):
        with open(log_path) as f:
            if "spectre completes with 0 errors" in f.read():
                print("  [{}] SKIP (already done)".format(safe_name))
                return safe_name, 0
    
    # Write params
    with open(os.path.join(SIM_DIR, "params.scs"), "w") as f:
        f.write("parameters vdd=1.8 cunit=4f calbp={} {}\n".format(calbp, params))
    
    # Run spectre
    print("  [{}] Running...".format(safe_name))
    sys.stdout.flush()
    t0 = time.time()
    cmd = (
        "cd {} && "
        "source /home/meow/.cshrc && "
        "rm -rf {} && "
        "spectre -64 tb_huang_cal_ramp.scs +escchars -format psfxl -raw {} +log {}"
    ).format(SIM_DIR, raw_dir, raw_dir, log_file)
    rc = subprocess.call(["csh", "-c", cmd])
    elapsed = time.time() - t0
    status = "OK" if rc == 0 else "FAIL(rc={})".format(rc)
    print("  [{}] {} ({:.0f}s)".format(safe_name, status, elapsed))
    sys.stdout.flush()
    return safe_name, rc

def main():
    os.chdir(SIM_DIR)
    print("=== SAR ADC Calibration Campaign ===")
    print("Start: {}".format(time.strftime("%Y-%m-%d %H:%M:%S")))
    print("Total: {} simulations".format(len(SCENARIOS)*2))
    
    results = []
    for scenario in SCENARIOS:
        print("\n--- {} ---".format(scenario))
        for calbp in [0, 1]:
            name, rc = run_one(scenario, calbp)
            results.append((name, rc))
    
    print("\n=== DONE at {} ===".format(time.strftime("%Y-%m-%d %H:%M:%S")))
    ok = sum(1 for _, rc in results if rc == 0)
    fail = len(results) - ok
    print("Passed: {}, Failed: {}".format(ok, fail))
    for name, rc in results:
        print("  {}: {}".format(name, "OK" if rc==0 else "FAIL({})".format(rc)))

if __name__ == "__main__":
    main()
