// cal_fsm.sv 闁?Shen 2018 Calibration State Machine
`timescale 1ns / 1ps
//
// Controls the calibration sequence:
//   For each of 7 targets (H1C闁愁偅澧?2C):
//     For pair in 0..N_PAIRS-1:
//       Force-0 subconvert 闁?save signed sum
//       Force-1 subconvert 闁?save signed sum
//       Accumulate half-difference
//     Compute mean weight 闁?validate 闁?commit to register

module cal_fsm #(
  parameter int N_TARGETS     = 7,
  parameter int N_PAIRS       = 128,
  parameter int WEIGHT_WIDTH  = 16,
  parameter int ACCUM_WIDTH   = 32
) (
  input  logic                          clk,
  input  logic                          rst_n,
  input  logic                          start,
  input  logic                          subconv_done,
  input  logic signed [15:0]           subconv_signed_sum,
  output logic                          start_subconv,
  output logic [$clog2(N_TARGETS)-1:0]  target_idx,
  output logic [2:0]                    phase,         // 0=IDLE, 1=P0, 2=P1, 3=N0, 4=N1         // 0=IDLE, 1=P0, 2=P1, 3=N0, 4=N1
  output logic [$clog2(N_PAIRS)-1:0]    pair_cnt,
  // Accumulator interface
  output logic                          acc_valid,

  // Weight register interface
  output logic                          wreg_we,
  output logic [$clog2(N_TARGETS)-1:0]  wreg_addr,
  output logic [WEIGHT_WIDTH-1:0]       wreg_wp,
  output logic [WEIGHT_WIDTH-1:0]       wreg_wn,
  output logic                          cal_done
);

  // 闁冲厜鍋撻柍鍏夊亾 Calibration target definitions (mirror Python cal_targets) 闁冲厜鍋撻柍鍏夊亾
  // Order: H1C(stage=6)闁愁偅澧?C(5)闁愁偅澧?C(4)闁愁偅澧?C-R(3)闁愁偅澧?C-A(2)闁愁偅澧?6C(1)闁愁偅澧?2C(0)
  localparam int TARGET_STAGES [0:6] = '{6, 5, 4, 3, 2, 1, 0};
  localparam int TARGET_NOMINAL_Q0 [0:6] = '{67, 134, 268, 536, 536, 1072, 2144};
  localparam int WEIGHT_TOL_PCT = 20;  // 閸?0% validity check

  // FSM states
  typedef enum logic [3:0] {
    IDLE           = 4'h0,
    TARGET_SETUP   = 4'h1,
    P0_FORCE       = 4'h2,   // P-side force-0 subconversion
    P0_WAIT        = 4'h3,
    P1_FORCE       = 4'h4,   // P-side force-1 subconversion
    P1_WAIT        = 4'h5,
    N0_FORCE       = 4'h6,   // N-side force-0 subconversion
    N0_WAIT        = 4'h7,
    N1_FORCE       = 4'h8,   // N-side force-1 subconversion
    N1_WAIT        = 4'h9,
    ACCUMULATE     = 4'hA,
    TARGET_DONE    = 4'hB,
    TARGET_VALIDATE= 4'hC,
    TARGET_COMMIT  = 4'hD,
    NEXT_TARGET    = 4'hE,
    DONE           = 4'hF
  } state_t;

  state_t state, state_next;

  // Internal registers
  logic [$clog2(N_TARGETS)-1:0] tgt_idx;
  logic [$clog2(N_PAIRS)-1:0]   pair_idx;
  logic [ACCUM_WIDTH-1:0]       accum_wp, accum_wn;  // per-target accumulator
  logic [15:0]                  ss_p0, ss_p1, ss_n0, ss_n1;  // saved signed sums
  logic [15:0]                  ss_p0_q8, ss_p1_q8, ss_n0_q8, ss_n1_q8;
  logic [WEIGHT_WIDTH-1:0]      wp_avg, wn_avg;
  logic [WEIGHT_WIDTH-1:0]      target_nom_q8;
  logic                         valid;

  // Tolerances in Q8
  logic [WEIGHT_WIDTH-1:0] tol_low, tol_high;

  // =========================================================================
  //  FSM Sequential Logic
  // =========================================================================
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      state        <= IDLE;
      tgt_idx      <= '0;
      pair_idx     <= '0;
      accum_wp     <= '0;
      accum_wn     <= '0;
      ss_p0        <= '0;
      ss_p1        <= '0;
      ss_n0        <= '0;
      ss_n1        <= '0;
      wp_avg       <= '0;
      wn_avg       <= '0;
    end else begin
      state <= state_next;

      case (state)
        IDLE: begin
          if (start) begin
            tgt_idx  <= '0;
            pair_idx <= '0;
            accum_wp <= '0;
            accum_wn <= '0;
          end
        end

        P0_WAIT: if (subconv_done) ss_p0 <= subconv_signed_sum;
        P1_WAIT: if (subconv_done) ss_p1 <= subconv_signed_sum;
        N0_WAIT: if (subconv_done) ss_n0 <= subconv_signed_sum;
        N1_WAIT: if (subconv_done) ss_n1 <= subconv_signed_sum;

        ACCUMULATE: begin
          // W_P += (P0 - P1) / 2  闁? Q0 raw, convert to Q8 for accumulation
          // W_N += (N1 - N0) / 2
          ss_p0_q8 <= {{(16-WEIGHT_WIDTH+8){1'b0}}, ss_p0, 8'b0};  // Q0 闁?Q8
          ss_p1_q8 <= {{(16-WEIGHT_WIDTH+8){1'b0}}, ss_p1, 8'b0};
          ss_n0_q8 <= {{(16-WEIGHT_WIDTH+8){1'b0}}, ss_n0, 8'b0};
          ss_n1_q8 <= {{(16-WEIGHT_WIDTH+8){1'b0}}, ss_n1, 8'b0};

          if (pair_idx == 0) begin
            // First pair: initialize accumulator
            accum_wp <= (ss_p0 - ss_p1) >>> 1;
            accum_wn <= (ss_n1 - ss_n0) >>> 1;
          end else begin
            accum_wp <= accum_wp + ((ss_p0 - ss_p1) >>> 1);
            accum_wn <= accum_wn + ((ss_n1 - ss_n0) >>> 1);
          end

          if (pair_idx == N_PAIRS - 1) begin
            // Final pair: compute average (濮婂尒_PAIRS via shift)
            // N_PAIRS=128 闁?>>7, N_PAIRS=16 闁?>>4, N_PAIRS=4 闁?>>2
            wp_avg <= accum_wp >>> $clog2(N_PAIRS);
            wn_avg <= accum_wn >>> $clog2(N_PAIRS);
          end
          pair_idx <= pair_idx + 1'b1;
        end

        TARGET_VALIDATE: begin
          target_nom_q8 <= TARGET_NOMINAL_Q0[tgt_idx] << 8;
          tol_low  <= (TARGET_NOMINAL_Q0[tgt_idx] * (100 - WEIGHT_TOL_PCT) / 100) << 8;
          tol_high <= (TARGET_NOMINAL_Q0[tgt_idx] * (100 + WEIGHT_TOL_PCT) / 100) << 8;
          valid <= (wp_avg >= tol_low) && (wp_avg <= tol_high);
        end

        NEXT_TARGET: begin
          // Compute final average (now accum_wp has the last pair)
          wp_avg <= accum_wp >>> $clog2(N_PAIRS);
          wn_avg <= accum_wn >>> $clog2(N_PAIRS);
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

  // =========================================================================
  //  FSM Combinational Logic
  // =========================================================================
  always_comb begin
    state_next     = state;
    start_subconv  = 1'b0;
    wreg_we        = 1'b0;
    wreg_addr      = tgt_idx;
    wreg_wp        = wp_avg;
    wreg_wn        = wn_avg;
    cal_done       = 1'b0;
    acc_valid      = 1'b0;

    case (state)
      IDLE: begin
        if (start)
          state_next = TARGET_SETUP;
      end

      TARGET_SETUP: begin
        state_next = P0_FORCE;
      end

      P0_FORCE: begin
        start_subconv = 1'b1;
        state_next = P0_WAIT;
      end

      P0_WAIT: begin
        if (subconv_done)
          state_next = P1_FORCE;
      end

      P1_FORCE: begin
        start_subconv = 1'b1;
        state_next = P1_WAIT;
      end

      P1_WAIT: begin
        if (subconv_done)
          state_next = N0_FORCE;
      end

      N0_FORCE: begin
        start_subconv = 1'b1;
        state_next = N0_WAIT;
      end

      N0_WAIT: begin
        if (subconv_done)
          state_next = N1_FORCE;
      end

      N1_FORCE: begin
        start_subconv = 1'b1;
        state_next = N1_WAIT;
      end

      N1_WAIT: begin
        if (subconv_done) begin
          acc_valid = 1'b1;
          state_next = ACCUMULATE;
        end
      end

      ACCUMULATE: begin
        if (pair_idx == N_PAIRS - 1) begin
          state_next = TARGET_DONE;
        end else begin
          state_next = P0_FORCE;    // next pair
        end
      end

      TARGET_DONE: begin
        state_next = TARGET_VALIDATE;
      end

      TARGET_VALIDATE: begin
        if (valid)
          state_next = TARGET_COMMIT;
        else
          state_next = DONE;  // FAILED 闁?calibration stopped
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
      end

      default: state_next = IDLE;
    endcase
  end

  // 闁冲厜鍋撻柍鍏夊亾 Output assignments 闁冲厜鍋撻柍鍏夊亾
  assign target_idx = tgt_idx;
  assign pair_cnt   = pair_idx;
  assign phase      = (state == P0_FORCE || state == P0_WAIT) ? 2'b01 :
                      (state == P1_FORCE || state == P1_WAIT) ? 2'b10 :
                      (state == N0_FORCE || state == N0_WAIT) ? 2'b11 : 2'b00;

endmodule
