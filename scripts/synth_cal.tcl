# synth_cal.tcl — portable Vivado synthesis with explicit timing evidence
#
# NOTE: cal_top exposes ASIC-internal switch controls and Q8 weights as parallel
# ports so that the calibration datapath is easy to inspect.  If this module is
# promoted directly to an FPGA package top, those internal wires become IOBs and
# over-utilize xc7z020clg400-1.  An FPGA prototype therefore needs a serialized
# or packed wrapper; this script deliberately preserves the raw integration
# interface and reports the resulting limitation.
set scr_dir  [file normalize [file dirname [info script]]]
set repo_dir [file normalize [file join $scr_dir ..]]
set rtl_dir  [file join $repo_dir rtl]

read_verilog -sv [list $rtl_dir/cal_fsm.sv $rtl_dir/cal_weight_reg.sv $rtl_dir/sar_subconverter.sv $rtl_dir/cal_top.sv]
read_xdc $scr_dir/timing.xdc

synth_design -top cal_top -part xc7z020clg400-1

report_utilization -file $scr_dir/synth_util.rpt
report_timing_summary -delay_type min_max -max_paths 10 -report_unconstrained \
  -file $scr_dir/synth_timing_summary.rpt
report_timing -delay_type max -max_paths 10 -file $scr_dir/synth_timing.rpt
report_timing -delay_type min -max_paths 10 -file $scr_dir/synth_hold.rpt
check_timing -verbose -file $scr_dir/synth_check_timing.rpt
puts "SYNTH DONE"
