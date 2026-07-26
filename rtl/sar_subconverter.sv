// sar_subconverter.sv — Lower-SAR Subconversion Controller (Synthesizable)
`timescale 1ns / 1ps
//
// Performs a subconversion on lower stages below the calibration target.
// This is NOT the full SAR ADC controller — it only handles the calibration
// subconversion with force-0/force-1 states.
//
// Operation (per subconversion):
//   1. Apply force state: target cap to VREFN or VREFP, higher caps to VCM
//   2. Run SAR trial on lower stages (descending nominal weight order)
//   3. Return decisions[15] and the side-specific signed Q8 sum
//
// Previously calibrated high-segment weights are read from the register file.
// Low-segment and terminal weights remain the nominal base ruler, matching the
// Python recursive calibration path.

module sar_subconverter #(
  parameter int N_STAGES           = 15,
  parameter int N_LOWER_STAGES_MAX = 14,
  parameter int WEIGHT_WIDTH       = 20,
  parameter int SUBSUM_WIDTH       = 24
) (
  input  logic                     clk,
  input  logic                     rst_n,
  input  logic                     start,
  input  logic [2:0]               target_idx,    // 0..6 → target stage
  input  logic [2:0]               phase,         // 1=P0, 2=P1, 3=N0, 4=N1
  input  logic                     cmp_out,       // comparator result
  input  logic [WEIGHT_WIDTH-1:0]  weights_p [6:0],
  input  logic [WEIGHT_WIDTH-1:0]  weights_n [6:0],
  output logic [1:0]               sw_p_h [6:0],
  output logic [1:0]               sw_n_h [6:0],
  output logic [1:0]               sw_p_l [6:0],
  output logic [1:0]               sw_n_l [6:0],
  output logic                     done,
  output logic signed [SUBSUM_WIDTH-1:0] signed_sum
);

  // ── Switch encoding ──
  localparam logic [1:0] SW_HOLD  = 2'b00;
  localparam logic [1:0] SW_VCM   = 2'b01;
  localparam logic [1:0] SW_VREFN = 2'b10;
  localparam logic [1:0] SW_VREFP = 2'b11;

  // ── Stage-to-capacitor mapping ──
  // Stage  0: high_32c (H32C, NCU=32)
  // Stage  1: high_16c (H16C, NCU=16)
  // Stage  2: high_8c_a (H8C-A, NCU=8)
  // Stage  3: high_8c_r (H8C-R, NCU=8)
  // Stage  4: high_4c  (H4C,  NCU=4)
  // Stage  5: high_2c  (H2C,  NCU=2)
  // Stage  6: high_1c  (H1C,  NCU=1)
  // Stage  7: low_32c  (L32C, NCU=32)
  // Stage  8: low_16c  (L16C, NCU=16)
  // Stage  9: low_8c   (L8C,  NCU=8)
  // Stage 10: low_4c   (L4C,  NCU=4)
  // Stage 11: low_2c_a (L2C-A, NCU=2)
  // Stage 12: low_2c_r (L2C-R, NCU=2)
  // Stage 13: low_1c   (L1C,  NCU=1)
  // Stage 14: terminal  (digital only, no cap)

  // ── Calibration targets → stages ──
  localparam int TARGET_STAGES [0:6] = '{6, 5, 4, 3, 2, 1, 0};
  localparam int TARGET_CAPS   [0:6] = '{6, 5, 4, 3, 2, 1, 0};  // index into sw_h

  // ── Nominal weights (Q0) ──
  localparam logic [15:0] NOM_Q0 [0:14] = '{
    2144, 1072, 536, 536, 268, 134, 67,    // high
    64, 32, 16, 8, 4, 4, 2,                // low
    1                                       // terminal
  };

  // ── Lower stages for each target (sorted descending by nominal weight) ──
  // Generated from Python SHEN_LOWER_STAGES
  // H1C(stage=6): lower = [7,8,9,10,11,12,13,14]
  // H2C(stage=5): lower = [6,7,8,9,10,11,12,13,14]
  // H4C(stage=4): lower = [5,6,7,8,9,10,11,12,13,14]
  // H8C-R(stage=3): lower = [4,5,6,7,8,9,10,11,12,13,14]
  // H8C-A(stage=2): lower = [3,4,5,6,7,8,9,10,11,12,13,14]
  // H16C(stage=1):  lower = [2,3,4,5,6,7,8,9,10,11,12,13,14]
  // H32C(stage=0):  lower = [1,2,3,4,5,6,7,8,9,10,11,12,13,14]
  //
  // We precompute the sorted lower stages for each target.
  // Stages are sorted by descending nominal weight.

  // Precomputed sorted lower stage lists (compact ROM)
  // Format: {count[3:0], stage[3:0] × N_LOWER_STAGES_MAX}
  // H1C: 8 lower stages in order: 7,8,9,10,11,12,13,14
  // H2C: 9 lower stages: 6,7,8,9,10,11,12,13,14
  // H4C: 10 lower stages: 5,6,7,8,9,10,11,12,13,14
  // H8C-R: 11 lower stages: 4,5,6,7,8,9,10,11,12,13,14
  // H8C-A: 12 lower stages: 3,4,5,6,7,8,9,10,11,12,13,14
  // H16C: 13 lower stages: 2,3,4,5,6,7,8,9,10,11,12,13,14
  // H32C: 14 lower stages: 1,2,3,4,5,6,7,8,9,10,11,12,13,14

  // Compact storage: 8 entries per target (4-bit stage index × 8)
  logic [3:0] lower_stages [0:6][0:13];  // 7 targets × up to 14 stages
  logic [3:0] n_lower [0:6];             // number of lower stages per target

  // SAR state
  typedef enum logic [2:0] {
    SAR_IDLE, SAR_SAMPLE, SAR_TRIAL, SAR_COMMIT, SAR_DONE
  } sar_state_t;
  sar_state_t sar_state;

  logic [3:0] trial_idx;        // index into lower_stages[tgt]
  logic [3:0] trial_stage;      // current stage being trialed
  logic [3:0] n_lower_cur;      // number of lower stages for current target

  // Accumulated signed sum
  logic signed [SUBSUM_WIDTH-1:0] accum_sum;
  logic [3:0] selected_trial_stage;
  logic signed [SUBSUM_WIDTH-1:0] selected_weight_p_q8;
  logic signed [SUBSUM_WIDTH-1:0] selected_weight_n_q8;

  // Force state for current phase
  logic [1:0] force_rail;       // VREFN or VREFP
  logic       force_is_p;       // 1=P-side, 0=N-side

  // ── Initialize lower stages ROM ──
  initial begin
    // H1C (target stage 6): lower = [7->14]
    lower_stages[0] = '{4'd7, 4'd8, 4'd9, 4'd10, 4'd11, 4'd12, 4'd13, 4'd14, 4'd0, 4'd0, 4'd0, 4'd0, 4'd0, 4'd0};
    n_lower[0] = 4'd8;
    // H2C (target stage 5): lower = [6->14]
    lower_stages[1] = '{4'd6, 4'd7, 4'd8, 4'd9, 4'd10, 4'd11, 4'd12, 4'd13, 4'd14, 4'd0, 4'd0, 4'd0, 4'd0, 4'd0};
    n_lower[1] = 4'd9;
    // H4C (target stage 4): lower = [5->14]
    lower_stages[2] = '{4'd5, 4'd6, 4'd7, 4'd8, 4'd9, 4'd10, 4'd11, 4'd12, 4'd13, 4'd14, 4'd0, 4'd0, 4'd0, 4'd0};
    n_lower[2] = 4'd10;
    // H8C-R (target stage 3): lower = [4->14]
    lower_stages[3] = '{4'd4, 4'd5, 4'd6, 4'd7, 4'd8, 4'd9, 4'd10, 4'd11, 4'd12, 4'd13, 4'd14, 4'd0, 4'd0, 4'd0};
    n_lower[3] = 4'd11;
    // H8C-A (target stage 2): lower = [3->14]
    lower_stages[4] = '{4'd3, 4'd4, 4'd5, 4'd6, 4'd7, 4'd8, 4'd9, 4'd10, 4'd11, 4'd12, 4'd13, 4'd14, 4'd0, 4'd0};
    n_lower[4] = 4'd12;
    // H16C (target stage 1): lower = [2->14]
    lower_stages[5] = '{4'd2, 4'd3, 4'd4, 4'd5, 4'd6, 4'd7, 4'd8, 4'd9, 4'd10, 4'd11, 4'd12, 4'd13, 4'd14, 4'd0};
    n_lower[5] = 4'd13;
    // H32C (target stage 0): lower = [1->14]
    lower_stages[6] = '{4'd1, 4'd2, 4'd3, 4'd4, 4'd5, 4'd6, 4'd7, 4'd8, 4'd9, 4'd10, 4'd11, 4'd12, 4'd13, 4'd14};
    n_lower[6] = 4'd14;
  end

  // ── Helper: set single switch ──
  function automatic void set_sw(output logic [1:0] sw_arr [6:0],
                                  input int idx, input logic [1:0] val);
    for (int i = 0; i < 7; i++)
      sw_arr[i] = (i == idx) ? val : sw_arr[i];
  endfunction

  // ── Helper: high index → sw index (reverse map) ──
  // h_idx 0=H32C(stage0), 1=H16C(stage1), ..., 6=H1C(stage6)
  // sw_h[0]=H32C(32Cu), sw_h[1]=H16C(16Cu), ..., sw_h[6]=H1C(1Cu)
  // So h_idx == sw_h index
  // ── Helper: low index → sw_l index ──
  // stage 7=L32C→l_idx0, 8=L16C→l_idx1, 9=L8C→l_idx2,
  //       10=L4C→l_idx3, 11=L2C-A→l_idx4, 12=L2C-R→l_idx5, 13=L1C→l_idx6
  function automatic int low_stage_to_lidx(input int stage);
    return stage - 7;
  endfunction

  always_comb begin
    selected_trial_stage = lower_stages[target_idx][trial_idx];
    if (selected_trial_stage < 7) begin
      // Register index 0 is H1(stage 6), index 6 is H32(stage 0).
      selected_weight_p_q8 = $signed({
        {(SUBSUM_WIDTH-WEIGHT_WIDTH){1'b0}},
        weights_p[6-selected_trial_stage]
      });
      selected_weight_n_q8 = $signed({
        {(SUBSUM_WIDTH-WEIGHT_WIDTH){1'b0}},
        weights_n[6-selected_trial_stage]
      });
    end else begin
      selected_weight_p_q8 = $signed({
        {(SUBSUM_WIDTH-16){1'b0}}, NOM_Q0[selected_trial_stage]
      }) <<< 8;
      selected_weight_n_q8 = $signed({
        {(SUBSUM_WIDTH-16){1'b0}}, NOM_Q0[selected_trial_stage]
      }) <<< 8;
    end
  end

  // synthesis translate_off
  initial begin
    if (SUBSUM_WIDTH < WEIGHT_WIDTH || SUBSUM_WIDTH < 24)
      $error("SUBSUM_WIDTH must be >= max(WEIGHT_WIDTH, 24)");
  end
  // synthesis translate_on

  // ── SAR FSM ──
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      sar_state   <= SAR_IDLE;
      done        <= 1'b0;
      trial_idx   <= '0;
      accum_sum   <= '0;
      force_is_p  <= 1'b0;
      force_rail  <= SW_VCM;
      n_lower_cur <= '0;
      trial_stage <= '0;
      signed_sum  <= '0;
      for (int i = 0; i < 7; i++) begin
        sw_p_h[i] <= SW_VCM;
        sw_n_h[i] <= SW_VCM;
        sw_p_l[i] <= SW_VCM;
        sw_n_l[i] <= SW_VCM;
      end
    end else begin
      case (sar_state)
        SAR_IDLE: begin
          done <= 1'b0;
          if (start) begin
            // Determine force rail
            force_is_p <= (phase == 3'd1 || phase == 3'd2);  // P0, P1 → force P side
            force_rail <= (phase == 3'd1 || phase == 3'd3) ? SW_VREFN : SW_VREFP;
            // P0: P→VREFN | P1: P→VREFP | N0: N→VREFN | N1: N→VREFP
            n_lower_cur <= n_lower[target_idx];
            trial_idx   <= '0;
            accum_sum   <= '0;
            sar_state   <= SAR_SAMPLE;
          end
        end

        SAR_SAMPLE: begin
          // Apply force state:
          // - Target cap and higher caps: fixed
          //   - Target: force_rail (P or N side), opposite side stays VCM
          //   - Higher caps: VCM (no participate in subconversion)
          // - Lower caps: VCM (will be trialed)
          // - Terminal: digital only

          // Reset all switches to VCM
          for (int i = 0; i < 7; i++) begin
            sw_p_h[i] <= SW_VCM;
            sw_n_h[i] <= SW_VCM;
            sw_p_l[i] <= SW_VCM;
            sw_n_l[i] <= SW_VCM;
          end

          // Set force on target cap
          if (force_is_p) begin
            // Force P-side target
            sw_p_h[TARGET_CAPS[target_idx]] <= force_rail;
          end else begin
            // Force N-side target
            sw_n_h[TARGET_CAPS[target_idx]] <= force_rail;
          end

          // Set higher caps to VCM (already done by reset above)

          sar_state <= SAR_TRIAL;
        end

        SAR_TRIAL: begin
          // Trial: P side AND N side both toggle current lower cap to VREFP
          trial_stage <= selected_trial_stage;

          if (selected_trial_stage == 4'd14) begin
            // Terminal stage: compare directly without switching
            sar_state <= SAR_COMMIT;
          end else begin
            // Determine if trial stage is high or low
            if (selected_trial_stage < 7) begin
              // High cap trial: toggle both sides
              sw_p_h[selected_trial_stage] <= SW_VREFP;
              sw_n_h[selected_trial_stage] <= SW_VREFP;
            end else begin
              // Low cap trial
              sw_p_l[low_stage_to_lidx(selected_trial_stage)] <= SW_VREFP;
              sw_n_l[low_stage_to_lidx(selected_trial_stage)] <= SW_VREFP;
            end
            sar_state <= SAR_COMMIT;
          end
        end

        SAR_COMMIT: begin
          // Read comparator: cmp_out=1 → VTOP_P > VTOP_N
          // Convention:
          //   cmp_out=0 (VTOP_P < VTOP_N): P side kept VREFP → Vdiff INCREASES → +weight
          //   cmp_out=1 (VTOP_P > VTOP_N): N side kept VREFP → Vdiff DECREASES → -weight
          // signed_sum_Q8 = sum(+W_P for P) + sum(-W_N for N).
          if (cmp_out) begin
            // VTOP_P > VTOP_N: keep N side at VREFP, P side back to VCM
            // N side contributes → negative signed sum
            if (trial_stage < 7) begin
              sw_p_h[trial_stage] <= SW_VCM;    // P side back to VCM
            end else if (trial_stage != 4'd14) begin
              sw_p_l[low_stage_to_lidx(trial_stage)] <= SW_VCM;
            end
            accum_sum <= accum_sum - selected_weight_n_q8;
          end else begin
            // VTOP_P < VTOP_N: keep P side at VREFP, N side back to VCM
            // P side contributes → positive signed sum
            if (trial_stage < 7) begin
              sw_n_h[trial_stage] <= SW_VCM;    // N side back to VCM
            end else if (trial_stage != 4'd14) begin
              sw_n_l[low_stage_to_lidx(trial_stage)] <= SW_VCM;
            end
            accum_sum <= accum_sum + selected_weight_p_q8;
          end

          if (trial_idx >= n_lower_cur - 1) begin
            sar_state <= SAR_DONE;
          end else begin
            trial_idx <= trial_idx + 1'b1;
            sar_state <= SAR_TRIAL;
          end
        end

        SAR_DONE: begin
          done <= 1'b1;
          signed_sum <= accum_sum;
          sar_state <= SAR_IDLE;
        end

        default: sar_state <= SAR_IDLE;
      endcase
    end
  end

endmodule
