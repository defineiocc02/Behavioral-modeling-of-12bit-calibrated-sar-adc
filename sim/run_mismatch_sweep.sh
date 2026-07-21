#!/bin/bash
# =============================================================================
# Mismatch sweep script for Huang V5 calibration
#
# Runs the calibration testbench with different single-cap mismatch values
# and collects the measured weights.
#
# Usage:
#   cd sim
#   ./run_mismatch_sweep.sh
#
# Requirements:
#   - Spectre simulator
#   - Verilog-A files linked in sim/ directory
# =============================================================================

set -e

TB="tb_huang_calibration.scs"
RESULTS_DIR="sweep_results"
LOG_FILE="${RESULTS_DIR}/sweep_summary.log"

mkdir -p ${RESULTS_DIR}
echo "Mismatch Sweep Summary" > ${LOG_FILE}
echo "======================" >> ${LOG_FILE}
echo "Date: $(date)" >> ${LOG_FILE}
echo "" >> ${LOG_FILE}

# Mismatch values to sweep
MISMATCH_VALUES="0.95 0.974 1.0 1.026 1.05"

# Physical capacitors to sweep (P-side and N-side)
# Format: "param_name  stage  nominal_weight  description"
CAPS=(
    "md8  5  122  high1"
    "md9  3  244  high2A"
    "md10 4  244  high2B"
    "md11 2  488  high4"
    "md12 1  976  high8"
    "md13 0  1952 high16"
)

echo "Running ideal reference..."
spectre ${TB} +md8=1.0 +mu8=1.0 +md9=1.0 +mu9=1.0 +md10=1.0 +mu10=1.0 \
    +md11=1.0 +mu11=1.0 +md12=1.0 +mu12=1.0 +md13=1.0 +mu13=1.0 \
    +cb_mult=1.05 \
    -format psfxl -raw ${RESULTS_DIR}/ideal.raw \
    > ${RESULTS_DIR}/ideal.log 2>&1

echo "Ideal reference complete." >> ${LOG_FILE}
echo "" >> ${LOG_FILE}

for cap_info in "${CAPS[@]}"; do
    read -r param stage nom_weight desc <<< "$cap_info"

    for side in "P" "N"; do
        if [ "$side" = "P" ]; then
            mu_param="mu${param#md}"
        else
            mu_param="${param/md/mu}"
            param="${param/md/mu}"
        fi

        for mismatch in ${MISMATCH_VALUES}; do
            # Reset all mismatches to ideal
            md8=1.0; mu8=1.0
            md9=1.0; mu9=1.0
            md10=1.0; mu10=1.0
            md11=1.0; mu11=1.0
            md12=1.0; mu12=1.0
            md13=1.0; mu13=1.0

            # Set the target mismatch
            if [ "$side" = "P" ]; then
                eval "${param}=${mismatch}"
            else
                eval "${param}=${mismatch}"
            fi

            case_name="${desc}_${side}_${mismatch}"
            echo "Running ${case_name}..."

            spectre ${TB} \
                +md8=${md8} +mu8=${mu8} \
                +md9=${md9} +mu9=${mu9} \
                +md10=${md10} +mu10=${mu10} \
                +md11=${md11} +mu11=${mu11} \
                +md12=${md12} +mu12=${mu12} \
                +md13=${md13} +mu13=${mu13} \
                +cb_mult=1.05 \
                -format psfxl -raw ${RESULTS_DIR}/${case_name}.raw \
                > ${RESULTS_DIR}/${case_name}.log 2>&1

            # Extract measured weight from log
            measured=$(grep "HUANGV5 measure.*target=.*stage=${stage}" \
                ${RESULTS_DIR}/${case_name}.log | \
                tail -1 | sed 's/.*W=\([0-9.]*\).*/\1/')
            valid=$(grep "HUANGV5 measure.*target=.*stage=${stage}" \
                ${RESULTS_DIR}/${case_name}.log | \
                tail -1 | sed 's/.*ok=\([0-9]*\).*/\1/')
            done_flag=$(grep "HUANGV5 DONE" \
                ${RESULTS_DIR}/${case_name}.log | wc -l)
            err_flag=$(grep "HUANGV5 ERROR" \
                ${RESULTS_DIR}/${case_name}.log | wc -l)

            expected=$(echo "scale=2; ${nom_weight} * ${mismatch}" | bc)

            echo "${case_name}: measured=${measured} expected=${expected} valid=${valid} done=${done_flag} err=${err_flag}" >> ${LOG_FILE}
        done
    done
done

echo "" >> ${LOG_FILE}
echo "Sweep complete. Results in ${RESULTS_DIR}/"
echo "Summary: ${LOG_FILE}"

cat ${LOG_FILE}
