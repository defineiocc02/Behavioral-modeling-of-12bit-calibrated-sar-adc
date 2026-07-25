# synth_cal.tcl — Vivado synthesis with clock constraint
# NOTE: cal_top is an ASIC internal module with 285 ports (switches + weights).
# IOB over-utilization (285/125 on xc7z020) is EXPECTED for ASIC designs.
# These signals are internal metal wires in ASIC, not chip-level I/O pads.
# For FPGA prototyping, use synth_fpga.tcl with a serial wrapper + larger part.
set rtl_dir "C:/Users/Administrator/Desktop/SAR_ADC_IDEAL_CAL_REPLACEMENT_V6_CLEAN/rtl"
set scr_dir "C:/Users/Administrator/Desktop/SAR_ADC_IDEAL_CAL_REPLACEMENT_V6_CLEAN/scripts"

read_verilog -sv [list $rtl_dir/cal_fsm.sv $rtl_dir/cal_weight_reg.sv $rtl_dir/sar_subconverter.sv $rtl_dir/cal_top.sv]
read_xdc $scr_dir/timing.xdc

synth_design -top cal_top -part xc7z020clg400-1

report_utilization -file $scr_dir/synth_util.rpt
report_timing -file $scr_dir/synth_timing.rpt
puts "SYNTH DONE"
