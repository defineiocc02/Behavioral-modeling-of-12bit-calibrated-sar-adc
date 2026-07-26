#!/usr/bin/env bash
set -uo pipefail

ROOT="/home/meow/jxy/trae_sandbox/current_git_74e7366"
SPECTRE="/opt/cadence/SPECTRE231/tools.lnx86/spectre/bin/spectre"
XRUN="/opt/cadence/XCELIUM2309/tools.lnx86/inca/bin/64bit/xrun"
export CDS_LIC_FILE="/opt/cadence/IC618/share/license/license.dat"
export CDS_LIC_ONLY=1

STATUS="$ROOT/reports/run_status.txt"
: > "$STATUS"
overall_rc=0

mkdir -p "$ROOT/runs/va_cmp" "$ROOT/runs/va_cdac"
mkdir -p "$ROOT/runs/rtl_cal" "$ROOT/runs/rtl_sar" "$ROOT/runs/rtl_top_compile"
mkdir -p "$ROOT/reports"

cd "$ROOT/runs/va_cmp"
if "$SPECTRE" "$ROOT/tb/tb_strongarm_cmp.scs" +log spectre.log \
    -raw raw -format psfascii \
    && grep -q "spectre completes with 0 errors" spectre.log; then
    echo "VA_CMP=PASS" >> "$STATUS"
else
    echo "VA_CMP=FAIL" >> "$STATUS"
    overall_rc=1
fi

cd "$ROOT/runs/va_cdac"
if "$SPECTRE" "$ROOT/tb/tb_cdac_behavioral.scs" +log spectre.log \
    -raw raw -format psfascii \
    && grep -q "spectre completes with 0 errors" spectre.log; then
    echo "VA_CDAC=PASS" >> "$STATUS"
else
    echo "VA_CDAC=FAIL" >> "$STATUS"
    overall_rc=1
fi

cd "$ROOT/runs/rtl_cal"
"$XRUN" -64bit -sv -top tb_cal_rtl -xmlibdirname xcelium.d \
    -l xrun.log \
    "$ROOT/source/rtl/cal_fsm.sv" \
    "$ROOT/source/rtl/tb_cal_rtl.sv"
rtl_cal_rc=$?
if grep -q "PASS: 7/7 targets" xrun.log; then
    echo "RTL_CAL=PASS" >> "$STATUS"
elif grep -qE "NOLICI|NOLICN" xrun.log; then
    echo "RTL_CAL=BLOCKED_LICENSE" >> "$STATUS"
    overall_rc=2
else
    echo "RTL_CAL=FAIL_RC_${rtl_cal_rc}" >> "$STATUS"
    overall_rc=1
fi

cd "$ROOT/runs/rtl_sar"
"$XRUN" -64bit -sv -top tb_sar_subconverter -xmlibdirname xcelium.d \
    -l xrun.log \
    "$ROOT/source/rtl/sar_subconverter.sv" \
    "$ROOT/source/rtl/tb_sar_subconverter.sv"
rtl_sar_rc=$?
if grep -q "PASS: lower-SAR uses recursive side-specific Q8 register weights" xrun.log; then
    echo "RTL_SAR=PASS" >> "$STATUS"
elif grep -qE "NOLICI|NOLICN" xrun.log; then
    echo "RTL_SAR=BLOCKED_LICENSE" >> "$STATUS"
    overall_rc=2
else
    echo "RTL_SAR=FAIL_RC_${rtl_sar_rc}" >> "$STATUS"
    overall_rc=1
fi

cd "$ROOT/runs/rtl_top_compile"
if "$XRUN" -64bit -sv -elaborate -top cal_top -xmlibdirname xcelium.d \
    -l xrun.log \
    "$ROOT/source/rtl/cal_weight_reg.sv" \
    "$ROOT/source/rtl/cal_fsm.sv" \
    "$ROOT/source/rtl/sar_subconverter.sv" \
    "$ROOT/source/rtl/cal_top.sv"; then
    echo "RTL_TOP_COMPILE=PASS" >> "$STATUS"
else
    echo "RTL_TOP_COMPILE=FAIL" >> "$STATUS"
    overall_rc=1
fi

cd "$ROOT"
du -sh . > reports/sandbox_size_after_run.txt
exit "$overall_rc"
