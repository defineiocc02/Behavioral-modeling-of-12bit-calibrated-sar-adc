// cal_accumulator.sv — Calibration Weight Accumulator
//
// Accumulates subconversion signed sums over N_PAIRS pairs.
// Division by N_PAIRS is done via right-shift (N_PAIRS=128 → >>7).
//
// Each measurement cycle (P0/P1/N0/N1 completed):
//   W_P += (ss_P0 - ss_P1) / 2
//   W_N += (ss_N1 - ss_N0) / 2

module cal_accumulator #(
  parameter int N_PAIRS       = 128,
  parameter int WEIGHT_WIDTH  = 16,
  parameter int ACCUM_WIDTH   = 32
) (
  input  logic                          clk,
  input  logic                          rst_n,
  input  logic                          valid_in,
  input  logic [15:0]                   signed_sum,   // from subconversion (separate: we get 4 per pair)
  output logic [ACCUM_WIDTH-1:0]        wp_sum,
  output logic [ACCUM_WIDTH-1:0]        wn_sum,
  output logic [WEIGHT_WIDTH-1:0]       wp_out,
  output logic [WEIGHT_WIDTH-1:0]       wn_out
);

  // Internal: we accumulate the 4 subconversion results per pair
  logic [15:0] ss_p0, ss_p1, ss_n0, ss_n1;
  logic [1:0]  subconv_phase;   // 0=P0, 1=P1, 2=N0, 3=N1
  logic [$clog2(N_PAIRS)-1:0] pair_cnt;
  logic [ACCUM_WIDTH-1:0] accum_wp, accum_wn;

  // NOTE: This module accumulates over consecutive subconversion calls.
  // The FSM sends 4 valid_in pulses per pair (P0, P1, N0, N1).
  // After the 4th (N1), a complete pair is accumulated.

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      ss_p0    <= '0;
      ss_p1    <= '0;
      ss_n0    <= '0;
      ss_n1    <= '0;
      subconv_phase <= 2'd0;
      pair_cnt <= '0;
      accum_wp <= '0;
      accum_wn <= '0;
      wp_out   <= '0;
      wn_out   <= '0;
    end else if (valid_in) begin
      // Capture subconversion result
      case (subconv_phase)
        2'd0: ss_p0 <= signed_sum;
        2'd1: ss_p1 <= signed_sum;
        2'd2: ss_n0 <= signed_sum;
        2'd3: begin
          ss_n1 <= signed_sum;
          // Accumulate the pair:
          // W_P += (ss_p0 - ss_p1) / 2  (Q0 → Q8 accumulation)
          // W_N += (ss_n1 - ss_n0) / 2
          // Extend to ACCUM_WIDTH with Q8 scaling
          accum_wp <= accum_wp + ({{(ACCUM_WIDTH-24){1'b0}}, ss_p0, 8'b0}
                                - {{(ACCUM_WIDTH-24){1'b0}}, ss_p1, 8'b0}) / 2;
          accum_wn <= accum_wn + ({{(ACCUM_WIDTH-24){1'b0}}, ss_n1, 8'b0}
                                - {{(ACCUM_WIDTH-24){1'b0}}, ss_n0, 8'b0}) / 2;
          pair_cnt <= pair_cnt + 1'b1;
        end
      endcase

      subconv_phase <= (subconv_phase == 2'd3) ? 2'd0 : subconv_phase + 1'b1;
    end

    // Final averaging: ÷N_PAIRS at end of accumulation
    if (pair_cnt == N_PAIRS) begin
      // N_PAIRS = 128 → right shift by 7
      wp_out <= accum_wp[ACCUM_WIDTH-1 : ACCUM_WIDTH-WEIGHT_WIDTH] >>> 7;
      wn_out <= accum_wn[ACCUM_WIDTH-1 : ACCUM_WIDTH-WEIGHT_WIDTH] >>> 7;
    end
  end

  assign wp_sum = accum_wp;
  assign wn_sum = accum_wn;

endmodule
