// cal_fsm.sv — Shen-derived calibration state machine
`timescale 1ns / 1ps
//
// For each target and each pair:
//   P0, P1, N0, N1 lower-SAR subconversions
//   raw_delta_P = P0_Q8 - P1_Q8
//   raw_delta_N = N1_Q8 - N0_Q8
// After N_PAIRS:
//   W_P,Q8 = sum(raw_delta_P) / (2*N_PAIRS)
//   W_N,Q8 = sum(raw_delta_N) / (2*N_PAIRS)
//
// N_PAIRS must be a power of two.  The default Q8 weights require 20 bits:
// H32 = 2144 * 256 = 548864.

module cal_fsm #(
  parameter int N_TARGETS    = 7,
  parameter int N_PAIRS      = 128,
  parameter int WEIGHT_WIDTH = 20,
  parameter int ACCUM_WIDTH  = 32,
  parameter int SUBSUM_WIDTH = 24,
  parameter int FRAC_BITS    = 8
) (
  input  logic                          clk,
  input  logic                          rst_n,
  input  logic                          start,
  input  logic                          subconv_done,
  input  logic signed [SUBSUM_WIDTH-1:0] subconv_signed_sum,
  output logic                          start_subconv,
  output logic [$clog2(N_TARGETS)-1:0]  target_idx,
  output logic [2:0]                    phase,
  output logic [$clog2(N_PAIRS)-1:0]    pair_cnt,
  output logic                          acc_valid,
  output logic                          wreg_we,
  output logic [$clog2(N_TARGETS)-1:0]  wreg_addr,
  output logic [WEIGHT_WIDTH-1:0]       wreg_wp,
  output logic [WEIGHT_WIDTH-1:0]       wreg_wn,
  output logic                          cal_done,
  output logic                          cal_failed
);

  localparam int WEIGHT_TOL_PCT = 20;
  localparam int AVG_DIV_SHIFT = $clog2(N_PAIRS) + 1;

  localparam logic [WEIGHT_WIDTH-1:0] TOL_LOW_Q8 [0:6] = '{
    (67   * (100-WEIGHT_TOL_PCT) / 100) << FRAC_BITS,
    (134  * (100-WEIGHT_TOL_PCT) / 100) << FRAC_BITS,
    (268  * (100-WEIGHT_TOL_PCT) / 100) << FRAC_BITS,
    (536  * (100-WEIGHT_TOL_PCT) / 100) << FRAC_BITS,
    (536  * (100-WEIGHT_TOL_PCT) / 100) << FRAC_BITS,
    (1072 * (100-WEIGHT_TOL_PCT) / 100) << FRAC_BITS,
    (2144 * (100-WEIGHT_TOL_PCT) / 100) << FRAC_BITS
  };
  localparam logic [WEIGHT_WIDTH-1:0] TOL_HIGH_Q8 [0:6] = '{
    (67   * (100+WEIGHT_TOL_PCT) / 100) << FRAC_BITS,
    (134  * (100+WEIGHT_TOL_PCT) / 100) << FRAC_BITS,
    (268  * (100+WEIGHT_TOL_PCT) / 100) << FRAC_BITS,
    (536  * (100+WEIGHT_TOL_PCT) / 100) << FRAC_BITS,
    (536  * (100+WEIGHT_TOL_PCT) / 100) << FRAC_BITS,
    (1072 * (100+WEIGHT_TOL_PCT) / 100) << FRAC_BITS,
    (2144 * (100+WEIGHT_TOL_PCT) / 100) << FRAC_BITS
  };

  typedef enum logic [3:0] {
    IDLE            = 4'h0,
    TARGET_SETUP    = 4'h1,
    P0_FORCE        = 4'h2,
    P0_WAIT         = 4'h3,
    P1_FORCE        = 4'h4,
    P1_WAIT         = 4'h5,
    N0_FORCE        = 4'h6,
    N0_WAIT         = 4'h7,
    N1_FORCE        = 4'h8,
    N1_WAIT         = 4'h9,
    ACCUMULATE      = 4'hA,
    TARGET_DONE     = 4'hB,
    TARGET_VALIDATE = 4'hC,
    TARGET_COMMIT   = 4'hD,
    NEXT_TARGET     = 4'hE,
    DONE            = 4'hF
  } state_t;

  state_t state, state_next;
  logic [$clog2(N_TARGETS)-1:0] tgt_idx;
  logic [$clog2(N_PAIRS)-1:0] pair_idx;
  logic signed [ACCUM_WIDTH-1:0] accum_wp, accum_wn;
  logic signed [SUBSUM_WIDTH-1:0] ss_p0, ss_p1, ss_n0, ss_n1;
  logic [WEIGHT_WIDTH-1:0] wp_avg, wn_avg;
  logic failure_latched;

  logic signed [SUBSUM_WIDTH:0] delta_wp, delta_wn;
  logic signed [ACCUM_WIDTH-1:0] delta_wp_ext, delta_wn_ext;
  logic signed [ACCUM_WIDTH-1:0] pair_wp_total, pair_wn_total;
  logic weights_in_range;

  assign delta_wp = $signed({ss_p0[SUBSUM_WIDTH-1], ss_p0})
                  - $signed({ss_p1[SUBSUM_WIDTH-1], ss_p1});
  assign delta_wn = $signed({ss_n1[SUBSUM_WIDTH-1], ss_n1})
                  - $signed({ss_n0[SUBSUM_WIDTH-1], ss_n0});
  assign delta_wp_ext = {
    {(ACCUM_WIDTH-SUBSUM_WIDTH-1){delta_wp[SUBSUM_WIDTH]}}, delta_wp
  };
  assign delta_wn_ext = {
    {(ACCUM_WIDTH-SUBSUM_WIDTH-1){delta_wn[SUBSUM_WIDTH]}}, delta_wn
  };
  assign pair_wp_total = (
    pair_idx == 0 ? delta_wp_ext : accum_wp + delta_wp_ext
  );
  assign pair_wn_total = (
    pair_idx == 0 ? delta_wn_ext : accum_wn + delta_wn_ext
  );

  function automatic logic [WEIGHT_WIDTH-1:0] sum_to_q8(
    input logic signed [ACCUM_WIDTH-1:0] raw_sum
  );
    logic signed [ACCUM_WIDTH-1:0] scaled;
    begin
      // Each lower-SAR sum is already Q8.  Divide only by 2*N_PAIRS.
      scaled = raw_sum >>> AVG_DIV_SHIFT;
      sum_to_q8 = scaled[WEIGHT_WIDTH-1:0];
    end
  endfunction

  assign weights_in_range =
    (wp_avg >= TOL_LOW_Q8[tgt_idx])
    && (wp_avg <= TOL_HIGH_Q8[tgt_idx])
    && (wn_avg >= TOL_LOW_Q8[tgt_idx])
    && (wn_avg <= TOL_HIGH_Q8[tgt_idx]);

  // synthesis translate_off
  initial begin
    if (N_PAIRS < 2 || (1 << $clog2(N_PAIRS)) != N_PAIRS)
      $error("N_PAIRS must be a power of two and at least 2");
    if (WEIGHT_WIDTH < 20)
      $error("WEIGHT_WIDTH must be >=20 for H32 Q8");
    if (ACCUM_WIDTH <= SUBSUM_WIDTH)
      $error("ACCUM_WIDTH must exceed SUBSUM_WIDTH");
  end
  // synthesis translate_on

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      state           <= IDLE;
      tgt_idx         <= '0;
      pair_idx        <= '0;
      accum_wp        <= '0;
      accum_wn        <= '0;
      ss_p0           <= '0;
      ss_p1           <= '0;
      ss_n0           <= '0;
      ss_n1           <= '0;
      wp_avg          <= '0;
      wn_avg          <= '0;
      failure_latched <= 1'b0;
    end else begin
      state <= state_next;
      case (state)
        IDLE: begin
          if (start) begin
            tgt_idx         <= '0;
            pair_idx        <= '0;
            accum_wp        <= '0;
            accum_wn        <= '0;
            failure_latched <= 1'b0;
          end
        end

        P0_WAIT: if (subconv_done) ss_p0 <= subconv_signed_sum;
        P1_WAIT: if (subconv_done) ss_p1 <= subconv_signed_sum;
        N0_WAIT: if (subconv_done) ss_n0 <= subconv_signed_sum;
        N1_WAIT: if (subconv_done) ss_n1 <= subconv_signed_sum;

        ACCUMULATE: begin
          accum_wp <= pair_wp_total;
          accum_wn <= pair_wn_total;
          if (pair_idx == N_PAIRS - 1) begin
            // pair_*_total includes the current, final pair.
            wp_avg <= sum_to_q8(pair_wp_total);
            wn_avg <= sum_to_q8(pair_wn_total);
          end
          pair_idx <= pair_idx + 1'b1;
        end

        TARGET_VALIDATE: begin
          if (!weights_in_range)
            failure_latched <= 1'b1;
        end

        NEXT_TARGET: begin
          pair_idx <= '0;
          accum_wp <= '0;
          accum_wn <= '0;
          if (tgt_idx < N_TARGETS - 1)
            tgt_idx <= tgt_idx + 1'b1;
        end

        default: ;
      endcase
    end
  end

  always_comb begin
    state_next    = state;
    start_subconv = 1'b0;
    wreg_we       = 1'b0;
    wreg_addr     = tgt_idx;
    wreg_wp       = wp_avg;
    wreg_wn       = wn_avg;
    cal_done      = 1'b0;
    cal_failed    = failure_latched;
    acc_valid     = 1'b0;

    case (state)
      IDLE: if (start) state_next = TARGET_SETUP;
      TARGET_SETUP: state_next = P0_FORCE;
      P0_FORCE: begin
        start_subconv = 1'b1;
        state_next = P0_WAIT;
      end
      P0_WAIT: if (subconv_done) state_next = P1_FORCE;
      P1_FORCE: begin
        start_subconv = 1'b1;
        state_next = P1_WAIT;
      end
      P1_WAIT: if (subconv_done) state_next = N0_FORCE;
      N0_FORCE: begin
        start_subconv = 1'b1;
        state_next = N0_WAIT;
      end
      N0_WAIT: if (subconv_done) state_next = N1_FORCE;
      N1_FORCE: begin
        start_subconv = 1'b1;
        state_next = N1_WAIT;
      end
      N1_WAIT: if (subconv_done) begin
        acc_valid = 1'b1;
        state_next = ACCUMULATE;
      end
      ACCUMULATE: begin
        if (pair_idx == N_PAIRS - 1)
          state_next = TARGET_DONE;
        else
          state_next = P0_FORCE;
      end
      TARGET_DONE: state_next = TARGET_VALIDATE;
      TARGET_VALIDATE: begin
        if (weights_in_range)
          state_next = TARGET_COMMIT;
        else
          state_next = DONE;
      end
      TARGET_COMMIT: begin
        wreg_we = 1'b1;
        state_next = NEXT_TARGET;
      end
      NEXT_TARGET: begin
        if (tgt_idx >= N_TARGETS - 1)
          state_next = DONE;
        else
          state_next = TARGET_SETUP;
      end
      DONE: begin
        cal_done = 1'b1;
        cal_failed = failure_latched;
      end
      default: state_next = IDLE;
    endcase
  end

  assign target_idx = tgt_idx;
  assign pair_cnt = pair_idx;
  assign phase = (state == P0_FORCE || state == P0_WAIT) ? 3'd1 :
                 (state == P1_FORCE || state == P1_WAIT) ? 3'd2 :
                 (state == N0_FORCE || state == N0_WAIT) ? 3'd3 :
                 (state == N1_FORCE || state == N1_WAIT) ? 3'd4 :
                 3'd0;

endmodule
