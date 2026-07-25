# synth_cal.tcl — Vivado synthesis script for calibration RTL
# Non-project mode, targets cal_top with N_TARGETS=7, N_PAIRS=128

set rtl_dir "C:/Users/Administrator/Desktop/SAR_ADC_IDEAL_CAL_REPLACEMENT_V6_CLEAN/rtl"

# Read synthesizable RTL (NOT cdac_model, NOT tb_cal_rtl)
read_verilog -sv [list \
  $rtl_dir/cal_fsm.sv \
  $rtl_dir/cal_weight_reg.sv \
  $rtl_dir/sar_subconverter.sv \
  $rtl_dir/cal_top.sv \
]

# Set top and parameters for production config
set_property generic N_TARGETS=7 [get_filesets sources_1]
set_property generic N_PAIRS=128 [get_filesets sources_1]

synth_design -top cal_top -part xc7z020clg400-1

report_utilization -file synth_utilization.rpt
report_timing -file synth_timing.rpt
puts "SYNTH COMPLETE"
