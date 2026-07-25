// cal_top.sv — Calibration Top-Level (Synthesizable RTL)
//
// Integrates: cal_fsm + cal_weight_reg + sar_subconverter
`timescale 1ns / 1ps
//
// Interface:
//   clk, rst_n       — system clock and reset
//   start             — calibration start pulse
//   cmp_out           — comparator result (1 bit)
//   cal_done          — calibration complete
//   sw_h[6:0]         — high-segment switch control (per cap: 00=hold, 01=VCM, 10=VREFN, 11=VREFP)
//   sw_l[6:0]         — low-segment switch control
//   weights_p[6:0]    — calibrated weights (Q8 fixed-point, 16-bit each)
//   weights_n[6:0]    — calibrated weights (Q8 fixed-point, 16-bit each)

module cal_top #(
  parameter int N_TARGETS     = 7,        // number of calibration targets
  parameter int N_PAIRS       = 128,      // averaging pairs
  parameter int N_LOWER_STAGES_MAX = 8,   // max lower stages per target
  parameter int WEIGHT_WIDTH  = 16,       // bit-width of weight registers
  parameter int ACCUM_WIDTH   = 32        // bit-width of accumulator
) (
  input  logic                          clk,
  input  logic                          rst_n,
  input  logic                          start,
  input  logic                          cmp_out,       // comparator output
  output logic                          cal_done,
  // Switch control: 2 bits per capacitor (14 caps × 2 sides)
  // {P_H[6:0], N_H[6:0], P_L[6:0], N_L[6:0]} each 2 bits
  output logic [1:0]                    sw_p_h [6:0],
  output logic [1:0]                    sw_n_h [6:0],
  output logic [1:0]                    sw_p_l [6:0],
  output logic [1:0]                    sw_n_l [6:0],
  // Calibrated weights output
  output logic [WEIGHT_WIDTH-1:0]       weights_p [N_TARGETS-1:0],
  output logic [WEIGHT_WIDTH-1:0]       weights_n [N_TARGETS-1:0]
);

  // ── Switch encoding ──
  // 2'b00 = hold (keep previous state)
  // 2'b01 = VCM (0.9V)
  // 2'b10 = VREFN (0V) — force-0
  // 2'b11 = VREFP (1.8V) — force-1
  localparam logic [1:0] SW_HOLD  = 2'b00;
  localparam logic [1:0] SW_VCM   = 2'b01;
  localparam logic [1:0] SW_VREFN = 2'b10;
  localparam logic [1:0] SW_VREFP = 2'b11;

  // ── Calibration target definitions ──
  // Target order: H1C(stage=6) -> H2C(stage=5) -> H4C(stage=4) ->
  //               H8C-R(stage=3) -> H8C-A(stage=2) -> H16C(stage=1) -> H32C(stage=0)
  localparam int TARGET_STAGES [0:6] = '{6, 5, 4, 3, 2, 1, 0};
  localparam int TARGET_NOMINAL_Q8 [0:6] = '{
    16'd67  << 8,   // H1C =  67 Q0 → Q8
    16'd134 << 8,   // H2C = 134 Q0
    16'd268 << 8,   // H4C = 268 Q0
    16'd536 << 8,   // H8C-R = 536 Q0
    16'd536 << 8,   // H8C-A = 536 Q0
    16'd1072 << 8,  // H16C = 1072 Q0
    16'd2144 << 8   // H32C = 2144 Q0
  };

  // ── FSM signals ──
  logic                                fsm_start_subconv;
  logic [$clog2(N_TARGETS)-1:0]        fsm_target_idx;
  logic [1:0]                          fsm_phase;  // 0=IDLE, 1=P0, 2=P1, 3=N0, 4=N1
  logic                                fsm_subconv_done;
  logic                                fsm_all_done;

  // ── SAR subconversion signals ──
  logic                                sar_start;
  logic                                sar_done;
  logic signed [15:0]                 sar_signed_sum;    // signed Q0 sum

  // ── Accumulator signals ──
  logic [$clog2(N_PAIRS)-1:0]          acc_pair_cnt;
  logic                                acc_valid;

  // ── Weight register signals ──
  logic [$clog2(N_TARGETS)-1:0]        wreg_addr;
  logic                                wreg_we;
  logic [WEIGHT_WIDTH-1:0]             wreg_wp_in, wreg_wn_in;

  // =========================================================================
  //  Calibration FSM
  // =========================================================================
  cal_fsm #(
    .N_TARGETS(N_TARGETS),
    .N_PAIRS(N_PAIRS)
  ) u_cal_fsm (
    .clk              (clk),
    .rst_n            (rst_n),
    .start            (start),
    .subconv_done     (sar_done),
    .subconv_signed_sum(sar_signed_sum),
    .start_subconv    (fsm_start_subconv),
    .target_idx       (fsm_target_idx),
    .phase            (fsm_phase),
    .pair_cnt         (acc_pair_cnt),
    .acc_valid        (acc_valid),
    .wreg_we          (wreg_we),
    .wreg_addr        (wreg_addr),
    .wreg_wp          (wreg_wp_in),
    .wreg_wn          (wreg_wn_in),
    .cal_done         (fsm_all_done)
  );

  // =========================================================================
  //  Weight Register File (7 entries × 2 sides)
  // =========================================================================
  cal_weight_reg #(
    .N_TARGETS(N_TARGETS),
    .WEIGHT_WIDTH(WEIGHT_WIDTH)
  ) u_weight_reg (
    .clk      (clk),
    .rst_n    (rst_n),
    .we       (wreg_we),
    .addr     (wreg_addr),
    .wp_in    (wreg_wp_in),
    .wn_in    (wreg_wn_in),
    .wp_out   (weights_p),
    .wn_out   (weights_n)
  );

  // =========================================================================
  //  SAR Subconversion Controller
  // =========================================================================
  sar_subconverter #(
    .N_LOWER_STAGES_MAX(N_LOWER_STAGES_MAX),
    .WEIGHT_WIDTH(WEIGHT_WIDTH)
  ) u_sar_subconv (
    .clk        (clk),
    .rst_n      (rst_n),
    .start      (fsm_start_subconv),
    .target_idx (fsm_target_idx),
    .phase      (fsm_phase),
    .cmp_out    (cmp_out),
    .sw_p_h     (sw_p_h),
    .sw_n_h     (sw_n_h),
    .sw_p_l     (sw_p_l),
    .sw_n_l     (sw_n_l),
    .done       (sar_done),
    .signed_sum (sar_signed_sum)
  );

  assign cal_done = fsm_all_done;

endmodule
