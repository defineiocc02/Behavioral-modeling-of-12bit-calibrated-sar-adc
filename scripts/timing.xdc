# timing.xdc — Clock constraint for calibration RTL
# Target: 100 MHz (10 ns period) — typical for SAR ADC digital logic at 10 MS/s
# ASIC internal module: I/O delays model intra-die digital interfaces
create_clock -period 10.000 -name clk [get_ports clk]

# Generic clock-quality allowance used only by this FPGA synthesis proxy.
# This is not a target-PDK clock-tree or ASIC signoff number.
set_clock_uncertainty 0.200 -setup [get_clocks clk]
set_clock_uncertainty 0.100 -hold  [get_clocks clk]

# Input delay: 2 ns max / 0.5 ns min (intra-die digital interface)
# cal_top inputs: clk, rst_n, start, cmp_out
set_input_delay  -clock clk -max 2.0 [get_ports {rst_n start cmp_out}]
set_input_delay  -clock clk -min 0.5 [get_ports {rst_n start cmp_out}]

# Output delay: 2 ns max / 0.5 ns min
# cal_top outputs: status, switch controls, and 7×20-bit Q8 P/N weights
set_output_delay -clock clk -max 2.0 [get_ports {cal_done cal_failed sw_p_h[*] sw_n_h[*] sw_p_l[*] sw_n_l[*] weights_p[*] weights_n[*]}]
set_output_delay -clock clk -min 0.5 [get_ports {cal_done cal_failed sw_p_h[*] sw_n_h[*] sw_p_l[*] sw_n_l[*] weights_p[*] weights_n[*]}]
