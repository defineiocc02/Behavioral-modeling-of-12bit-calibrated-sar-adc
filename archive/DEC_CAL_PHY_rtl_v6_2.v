// Synthesizable RTL version of DEC_CAL_PHY.va (V6.2: 7-bit calDAC + w2 re-correction)
//
// V6: 7-bit calDAC (stages 6-12), range ±126, SAR 7 steps, DITHER_PAIR_EDGES=16
// V6.1: 4-target recursive calibration with w3+w4 joint measurement
// V6.2: w2 re-correction (add E back to w2 after measuring w3+w4) +
//       calDAC saturation detection (reject measurements where D+/D- hit endpoint)
//
// Converts the Verilog-A behavioral calibration engine + decoder into
// synthesizable Verilog-2001 RTL. All analog constructs (electrical,
// V(), transition(), @cross) are replaced with standard digital logic.
//
// Key changes from Verilog-A:
//   - electrical ports -> wire/reg; DGND/DVDD removed
//   - @cross(V(SIG)-vth,+1/-1) -> always @(posedge/negedge SIG)
//   - V(SIG)>vth -> direct digital signal
//   - transition() removed (digital signals switch natively)
//   - real parameters -> integer parameters
//   - float WEIGHT_TOL -> integer percent comparison (multiply-only)
//   - NORMALIZE_REDUNDANT_RANGE: requires hardware divider, kept but flagged
//   - avg_pairs division -> right shift (avg_pairs = 2^AVG_PAIRS_LOG2)
//   - Two RST1 posedge blocks merged into one (avoids simulation race)
//   - cmp_valid logic simplified (digital comparator output is always valid)
//
// Interface is pin-compatible with DEC_CAL_PHY.va for drop-in replacement
// in a mixed-signal testbench (digital side).

module DEC_CAL_PHY_rtl (
    output [11:0] Bit,
    input  [0:13] BP,
    input         SOUT,
    input         COMP, COMN,
    input         RST1, CAL_RST,
    input         CLK_SAR, CLK00,
    input         CAL_CLK,
    output        CLK,
    output [0:12] BITD_CAL, BITU_CAL,
    output        CAL, DONE, ERR
);

    // ============================================================
    // Parameters (user-editable, all integer for synthesizability)
    // ============================================================
    parameter CAL_BYPASS       = 0;   // 0=run cal, 1=bypass
    parameter AVG_PAIRS_LOG2   = 5;   // 2^5 = 32 pairs
    parameter ENFORCE_MIN_AVG  = 1;   // clamp to MIN_AVG_PAIRS_LOG2
    parameter MIN_AVG_PAIRS_LOG2 = 5;
    parameter APPLY_CAL_WEIGHT = 1;
    parameter REMOVE_REDUNDANCY_OFFSET = 1;
    parameter NORMALIZE_REDUNDANT_RANGE = 0; // NOTE: needs hardware divider
    parameter CMP_SWAP         = 1;
    parameter WEIGHT_TOL_PCT   = 35;  // 35% tolerance (integer percent)
    parameter FRAC_BITS        = 6;   // Q-format fractional bits
    parameter RAW_INVERT       = 0;
    parameter FIRST_INVERT     = 0;
    parameter DEBUG            = 1;   // 0=quiet, 1=basic, 2=verbose

    // ============================================================
    // Local parameters
    // ============================================================
    localparam FB   = (FRAC_BITS < 6) ? 6 : FRAC_BITS;
    localparam QS   = (1 << FB);                          // Q-scale = 64
    localparam AP   = (ENFORCE_MIN_AVG &&
                       (AVG_PAIRS_LOG2 < MIN_AVG_PAIRS_LOG2))
                       ? (1 << MIN_AVG_PAIRS_LOG2)
                       : (1 << AVG_PAIRS_LOG2);           // avg_pairs = 32

    localparam CAL_IDLE       = 3'd0;
    localparam CAL_PRECHARGE  = 3'd1;
    localparam CAL_SAR_TRIAL  = 3'd2;
    localparam CAL_TERMINAL   = 3'd3;
    localparam CAL_FINISH_DIR = 3'd4;

    // calDAC mask: stages 6..12 = bits 6..12 = 0x1FC0 = 8128
    localparam CALDAC_MASK = 13'h1FC0;

    // ============================================================
    // Weight registers (Q-format integers, 32-bit signed)
    // ============================================================
    integer w0, w1, w2, w3, w4, w5, w6;
    integer w7, w8, w9, w10, w11, w12, w13;

    // ============================================================
    // Calibration state
    // ============================================================
    reg [2:0]  cal_state;
    integer    sar_step;
    integer    trial_mask;
    integer    switched_mask;
    integer    switched_sum;
    integer    d_plus_code, d_minus_code;
    integer    direction;
    integer    target_idx;
    integer    target_mask;
    integer    wall_mask;
    integer    d_mask, u_mask;
    integer    repeat_idx;
    integer    accum_d_plus, accum_d_minus;

    reg        cal_mode_i;
    reg        cal_done_i;
    reg        cal_error_i;
    reg        cal_armed_i;
    reg        cal_started_i;
    reg        finish_pending_i;
    reg        frame_active_i;
    reg        saturate_flag;   // V6.2: set when D+/D- hits endpoint (>=126 or <=1)

    integer    measured_weight_q;
    integer    wall_weight_q;
    integer    residual_q;
    integer    rounding_term;

    // ============================================================
    // Decoder
    // ============================================================
    integer    r0, r1, r2, r3, r4, r5, r6;
    integer    r7, r8, r9, r10, r11, r12, r13;
    integer    raw_sum;
    integer    total_weight_q;
    integer    dec_w0, dec_w1, dec_w2;
    integer    redundancy_offset_q;
    integer    centered_sum;
    reg [11:0] adc_code;

    reg        cmp_p_gt_n;

    // ============================================================
    // Initialization
    // ============================================================
    initial begin
        cal_state    = CAL_IDLE;
        sar_step     = 0;
        trial_mask   = 0;
        switched_mask= 0;
        switched_sum = 0;
        d_plus_code  = 0;
        d_minus_code = 0;
        direction    = 0;
        target_idx   = 3;
        target_mask  = 4;
        wall_mask    = 24;
        d_mask       = 0;
        u_mask       = 0;
        repeat_idx   = 0;
        accum_d_plus = 0;
        accum_d_minus= 0;

        cal_mode_i    = 1'b0;
        cal_done_i    = (CAL_BYPASS != 0) ? 1'b1 : 1'b0;
        cal_error_i   = 1'b0;
        cal_armed_i   = 1'b0;
        cal_started_i = 1'b0;
        finish_pending_i = 1'b0;
        frame_active_i   = 1'b0;
        saturate_flag    = 1'b0;

        w0  = 2048*QS; w1  = 1024*QS; w2  = 512*QS;
        w3  = 256*QS;  w4  = 256*QS;  w5  = 128*QS;
        w6  = 48*QS;   w7  = 32*QS;   w8  = 20*QS;
        w9  = 12*QS;   w10 = 8*QS;    w11 = 4*QS;
        w12 = 2*QS;    w13 = QS;

        measured_weight_q = 0;
        wall_weight_q     = 0;
        residual_q        = 0;
        adc_code          = 12'd0;
    end

    // ============================================================
    // CAL_RST rising: reset all state
    // ============================================================
    always @(posedge CAL_RST) begin
        cal_state    = CAL_IDLE;
        sar_step     = 0;
        trial_mask   = 0;
        switched_mask= 0;
        switched_sum = 0;
        d_plus_code  = 0;
        d_minus_code = 0;
        direction    = 0;
        target_idx   = 3;
        target_mask  = 4;
        wall_mask    = 24;
        d_mask       = 0;
        u_mask       = 0;
        repeat_idx   = 0;
        accum_d_plus = 0;
        accum_d_minus= 0;

        cal_mode_i       = 1'b0;
        cal_done_i       = (CAL_BYPASS != 0) ? 1'b1 : 1'b0;
        cal_error_i      = 1'b0;
        cal_armed_i      = 1'b0;
        cal_started_i    = 1'b0;
        finish_pending_i = 1'b0;
        frame_active_i   = 1'b0;
        saturate_flag    = 1'b0;

        w0  = 2048*QS; w1  = 1024*QS; w2  = 512*QS;
        w3  = 256*QS;  w4  = 256*QS;  w5  = 128*QS;
        w6  = 48*QS;   w7  = 32*QS;   w8  = 20*QS;
        w9  = 12*QS;   w10 = 8*QS;    w11 = 4*QS;
        w12 = 2*QS;    w13 = QS;
        adc_code = 12'd0;
    end

    // ============================================================
    // CAL_RST falling: start calibration
    // ============================================================
    always @(negedge CAL_RST) begin
        if (CAL_BYPASS == 0) begin
            cal_state    = CAL_IDLE;
            sar_step     = 0;
            trial_mask   = 0;
            switched_mask= 0;
            switched_sum = 0;
            d_plus_code  = 0;
            d_minus_code = 0;
            direction    = 0;
            target_idx   = 3;
            target_mask  = 4;
            wall_mask    = 24;
            d_mask       = 0;
            u_mask       = 0;
            repeat_idx   = 0;
            accum_d_plus = 0;
            accum_d_minus= 0;

            cal_mode_i       = 1'b1;
            cal_done_i       = 1'b0;
            cal_error_i      = 1'b0;
            cal_armed_i      = 1'b1;
            cal_started_i    = 1'b0;
            finish_pending_i = 1'b0;
            frame_active_i   = 1'b0;
            saturate_flag    = 1'b0;

            wall_weight_q = w3 + w4;
            if (DEBUG != 0)
                $display("OFFSAR start avg_pairs=%0d Q=%0d", AP, FB);
        end
    end

    // ============================================================
    // RST1 rising: merge of frame-end/handoff AND direction-finish
    //   (Verilog-A had two @cross(+1) blocks; merged to avoid race)
    // ============================================================
    always @(posedge RST1) begin
        frame_active_i <= 1'b0;
        cal_started_i  <= 1'b0;
        d_mask <= 0;
        u_mask <= 0;

        // --- Block A: calibration finished, handoff to normal mode ---
        if (cal_mode_i && finish_pending_i) begin
            cal_mode_i    <= 1'b0;
            cal_armed_i   <= 1'b0;
            cal_started_i <= 1'b0;
            d_mask <= 0;
            u_mask <= 0;
            if (cal_error_i) begin
                w0  = 2048*QS; w1  = 1024*QS; w2  = 512*QS;
                w3  = 256*QS;  w4  = 256*QS;  w5  = 128*QS;
                w6  = 48*QS;   w7  = 32*QS;   w8  = 20*QS;
                w9  = 12*QS;   w10 = 8*QS;    w11 = 4*QS;
                w12 = 2*QS;    w13 = QS;
            end
            cal_done_i <= 1'b1;
            if (DEBUG != 0) begin
                $display("OFFSAR finish done=%0d err=%0d", cal_done_i, cal_error_i);
                $display("OFFSAR weights_q={%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d} Q=%0d",
                    w0, w1, w2, w3, w4, w5, w6, w7, w8,
                    w9, w10, w11, w12, w13, FB);
            end
        end

        // --- Block B: one direction finished, compute weight or switch ---
        if (cal_mode_i && (cal_state == CAL_FINISH_DIR)) begin
            if (direction == 0) begin
                // D+ done, start D-
                direction  <= 1;
                cal_state  <= CAL_IDLE;
            end else begin
                // Both directions done, accumulate
                accum_d_plus  = accum_d_plus + d_plus_code;
                accum_d_minus = accum_d_minus + d_minus_code;
                repeat_idx    = repeat_idx + 1;

                if (DEBUG > 1)
                    $display("OFFSAR pair tgt=%0d D+=%0d D-=%0d pair=%0d",
                        target_idx, d_plus_code, d_minus_code, repeat_idx);

                if (repeat_idx >= AP) begin
                    // Q-format: R_Q = round(QS * (sum_D+ - sum_D-) / N)
                    // N = 2^AVG_PAIRS_LOG2, use right-shift instead of divide
                    if ((accum_d_plus - accum_d_minus) >= 0)
                        rounding_term = AP / 2;
                    else
                        rounding_term = -AP / 2;
                    residual_q = (QS * (accum_d_plus - accum_d_minus)
                                 + rounding_term) >> AVG_PAIRS_LOG2;

                    measured_weight_q = wall_weight_q + residual_q;

                    if (DEBUG != 0)
                        $display("OFFSAR measure tgt=%0d wall_q=%0d R_q=%0d measured_q=%0d",
                            target_idx, wall_weight_q, residual_q, measured_weight_q);

                    // Tolerance check: |measured - target| <= target * tol%
                    //   Rewrite as multiply-only to avoid division:
                    //   measured * 100 >= target_q * (100 - TOL)
                    //   measured * 100 <= target_q * (100 + TOL)
                    case (target_idx)
                        3: begin
                            // w2 (C10, w=512), wall=w3+w4
                            if (!saturate_flag &&
                                (measured_weight_q * 100 >= 512*QS*(100 - WEIGHT_TOL_PCT)) &&
                                (measured_weight_q * 100 <= 512*QS*(100 + WEIGHT_TOL_PCT)))
                                w2 = measured_weight_q;
                            else if (DEBUG != 0)
                                $display("OFFSAR REJECT tgt=C10 measured_q=%0d sat=%0d",
                                    measured_weight_q, saturate_flag);
                        end
                        2: begin
                            // w3+w4 joint (C8+C9, w=256+256=512), wall=w2
                            if (!saturate_flag &&
                                (measured_weight_q * 100 >= 512*QS*(100 - WEIGHT_TOL_PCT)) &&
                                (measured_weight_q * 100 <= 512*QS*(100 + WEIGHT_TOL_PCT))) begin
                                w3 = measured_weight_q / 2;
                                w4 = measured_weight_q / 2;
                                // V6.2: w2 re-correction.
                                // w2_measured = 512+e2-E (wall was nominal w3+w4).
                                // measured_34 = 512+E (true W3+W4).
                                // w2_corrected = w2 + E = 512+e2 (exact).
                                w2 = w2 + (measured_weight_q - 512*QS);
                            end else if (DEBUG != 0)
                                $display("OFFSAR REJECT tgt=C8C9joint measured_q=%0d sat=%0d",
                                    measured_weight_q, saturate_flag);
                        end
                        1: begin
                            if (!saturate_flag &&
                                (measured_weight_q * 100 >= 1024*QS*(100 - WEIGHT_TOL_PCT)) &&
                                (measured_weight_q * 100 <= 1024*QS*(100 + WEIGHT_TOL_PCT)))
                                w1 = measured_weight_q;
                            else if (DEBUG != 0)
                                $display("OFFSAR REJECT tgt=C11 measured_q=%0d sat=%0d",
                                    measured_weight_q, saturate_flag);
                        end
                        0: begin
                            if (!saturate_flag &&
                                (measured_weight_q * 100 >= 2048*QS*(100 - WEIGHT_TOL_PCT)) &&
                                (measured_weight_q * 100 <= 2048*QS*(100 + WEIGHT_TOL_PCT)))
                                w0 = measured_weight_q;
                            else if (DEBUG != 0)
                                $display("OFFSAR REJECT tgt=C12 measured_q=%0d sat=%0d",
                                    measured_weight_q, saturate_flag);
                        end
                    endcase

                    target_idx    = target_idx - 1;
                    repeat_idx    = 0;
                    accum_d_plus  = 0;
                    accum_d_minus = 0;
                    saturate_flag = 1'b0;  // reset for next target

                    case (target_idx)
                        2: begin
                            // Next: w3+w4 joint, wall=w2_measured
                            target_mask    = 24;       // stages 3,4 joint
                            wall_mask      = 4;        // stage 2
                            wall_weight_q  = w2;       // just measured
                        end
                        1: begin
                            target_mask    = 2;
                            wall_mask      = 28;
                            wall_weight_q  = w2 + w3 + w4;
                        end
                        0: begin
                            target_mask    = 1;
                            wall_mask      = 30;
                            wall_weight_q  = w1 + w2 + w3 + w4;
                        end
                        default: begin
                            finish_pending_i <= 1'b1;
                            target_idx       = -1;
                        end
                    endcase
                    direction <= 0;
                end else begin
                    direction <= 0;
                end
                cal_state <= CAL_IDLE;
            end
        end
    end

    // ============================================================
    // RST1 falling: start frame
    // ============================================================
    always @(negedge RST1) begin
        if (cal_mode_i && !finish_pending_i) begin
            frame_active_i  <= 1'b1;
            cal_started_i   <= 1'b0;
            d_mask <= 0;
            u_mask <= 0;
            cal_state       <= CAL_PRECHARGE;
            sar_step        <= 0;
            trial_mask      <= 0;
            switched_mask   <= 0;
            switched_sum    <= 0;
            if (DEBUG > 1)
                $display("OFFSAR frame start tgt=%0d dir=%0d pair=%0d",
                    target_idx, direction, repeat_idx);
        end
    end

    // ============================================================
    // CAL_CLK rising: set up trial
    // ============================================================
    always @(posedge CAL_CLK) begin
        if (cal_mode_i && frame_active_i && !finish_pending_i) begin

            if (cal_state == CAL_PRECHARGE) begin
                switched_mask <= 0;
                switched_sum  <= 0;
                sar_step      <= 0;
                cal_state     <= CAL_SAR_TRIAL;
                trial_mask    = 64;   // stage 6, C7, w=48
            end else if (cal_state == CAL_SAR_TRIAL) begin
                case (sar_step)
                    0: trial_mask = 64;    // C7, w=48
                    1: trial_mask = 128;   // C6, w=32
                    2: trial_mask = 256;   // C5, w=20
                    3: trial_mask = 512;   // C4, w=12
                    4: trial_mask = 1024;  // C3, w=8
                    5: trial_mask = 2048;  // C2, w=4
                    6: trial_mask = 4096;  // C1, w=2
                    default: trial_mask = 0;
                endcase
            end

            // Update d_mask/u_mask for offset-binary SAR
            if (direction == 0) begin
                // D+: F+ = +Wtarget - Wwall + 126 - 2*S
                d_mask = target_mask |
                         (CALDAC_MASK & ~(switched_mask | trial_mask));
                u_mask = wall_mask | switched_mask | trial_mask;
            end else begin
                // D-: F- = -Wtarget + Wwall + 126 - 2*S
                d_mask = wall_mask |
                         (CALDAC_MASK & ~(switched_mask | trial_mask));
                u_mask = target_mask | switched_mask | trial_mask;
            end
        end
    end

    // ============================================================
    // CAL_CLK falling: latch comparator, decide keep/undo
    // ============================================================
    always @(negedge CAL_CLK) begin
        if (cal_mode_i && frame_active_i && !finish_pending_i
            && (cal_state != CAL_PRECHARGE)) begin

            // Read comparator (digital: COMP/COMN are 1-bit)
            // Original: cmp_p_gt_n = (COMP < COMN) ? 1 : 0
            //   COMP=0, COMN=1 -> P<N -> cmp_p_gt_n=1
            //   CMP_SWAP=1 inverts
            cmp_p_gt_n = (~COMP & COMN) ? 1'b1 : 1'b0;
            if (CMP_SWAP != 0)
                cmp_p_gt_n = ~cmp_p_gt_n;

            if (cal_state == CAL_SAR_TRIAL) begin
                // offset-binary SAR: P>N (cmp_p_gt_n=1) -> KEEP switch
                if (cmp_p_gt_n) begin
                    switched_mask = switched_mask | trial_mask;
                    case (sar_step)
                        0: switched_sum = switched_sum + 48;
                        1: switched_sum = switched_sum + 32;
                        2: switched_sum = switched_sum + 20;
                        3: switched_sum = switched_sum + 12;
                        4: switched_sum = switched_sum + 8;
                        5: switched_sum = switched_sum + 4;
                        6: switched_sum = switched_sum + 2;
                    endcase
                end

                sar_step   = sar_step + 1;
                trial_mask = 0;

                if (sar_step >= 7)
                    cal_state <= CAL_TERMINAL;
            end else if (cal_state == CAL_TERMINAL) begin
                // Terminal bit
                if (direction == 0) begin
                    d_plus_code = switched_sum + (cmp_p_gt_n ? 1 : 0);
                    // V6.2: Saturation detection for D+
                    if (d_plus_code >= 126 || d_plus_code <= 1) begin
                        saturate_flag <= 1'b1;
                        if (DEBUG != 0)
                            $display("OFFSAR SATURATE tgt=%0d dir=+ code=%0d (endpoint hit)",
                                target_idx, d_plus_code);
                    end
                    if (DEBUG > 1)
                        $display("OFFSAR code tgt=%0d dir=+ D+=%0d",
                            target_idx, d_plus_code);
                end else begin
                    d_minus_code = switched_sum + (cmp_p_gt_n ? 1 : 0);
                    // V6.2: Saturation detection for D-
                    if (d_minus_code >= 126 || d_minus_code <= 1) begin
                        saturate_flag <= 1'b1;
                        if (DEBUG != 0)
                            $display("OFFSAR SATURATE tgt=%0d dir=- code=%0d (endpoint hit)",
                                target_idx, d_minus_code);
                    end
                    if (DEBUG > 1)
                        $display("OFFSAR code tgt=%0d dir=- D-=%0d",
                            target_idx, d_minus_code);
                end

                cal_state <= CAL_FINISH_DIR;
            end
        end
    end

    // ============================================================
    // SOUT rising: normal decoder (latch one complete RAW code)
    // ============================================================
    always @(posedge SOUT) begin
        if (CAL_BYPASS || (cal_done_i && !cal_mode_i)) begin
            r0  = BP[13]; r1  = BP[12]; r2  = BP[11]; r3  = BP[10];
            r4  = BP[9];  r5  = BP[8];  r6  = BP[7];  r7  = BP[6];
            r8  = BP[5];  r9  = BP[4];  r10 = BP[3];  r11 = BP[2];
            r12 = BP[1];  r13 = BP[0];

            if (RAW_INVERT != 0) begin
                r1=~r1; r2=~r2; r3=~r3; r4=~r4; r5=~r5; r6=~r6;
                r7=~r7; r8=~r8; r9=~r9; r10=~r10; r11=~r11;
                r12=~r12; r13=~r13;
            end
            if (FIRST_INVERT != 0)
                r0 = ~r0;

            // Select calibrated or ideal weights
            if (APPLY_CAL_WEIGHT != 0) begin
                dec_w0 = w0; dec_w1 = w1; dec_w2 = w2;
            end else begin
                dec_w0 = 2048*QS; dec_w1 = 1024*QS; dec_w2 = 512*QS;
            end

            raw_sum = r0*dec_w0 + r1*dec_w1 + r2*dec_w2 +
                r3*w3 + r4*w4 + r5*w5 + r6*w6 + r7*w7 +
                r8*w8 + r9*w9 + r10*w10 + r11*w11 +
                r12*w12 + r13*w13;

            total_weight_q = dec_w0 + dec_w1 + dec_w2 +
                w3 + w4 + w5 + w6 + w7 + w8 + w9 +
                w10 + w11 + w12 + w13;

            if (NORMALIZE_REDUNDANT_RANGE != 0) begin
                // Requires hardware divider — may not synthesize on all tools
                if (total_weight_q > 0)
                    adc_code = (raw_sum * 4095) / total_weight_q;
                else
                    adc_code = 0;
            end else begin
                if (REMOVE_REDUNDANCY_OFFSET != 0) begin
                    redundancy_offset_q = total_weight_q - 4095*QS;
                    if (redundancy_offset_q >= 0)
                        redundancy_offset_q = (redundancy_offset_q + 1) / 2;
                    else
                        redundancy_offset_q = (redundancy_offset_q - 1) / 2;
                    centered_sum = raw_sum - redundancy_offset_q;
                end else begin
                    centered_sum = raw_sum;
                end
                // Q-to-integer with rounding
                if (centered_sum >= 0)
                    adc_code = (centered_sum + QS/2) / QS;
                else
                    adc_code = (centered_sum - QS/2) / QS;
            end

            // Clip to [0, 4095]
            if (adc_code < 0)
                adc_code = 0;
            else if (adc_code > 4095)
                adc_code = 4095;
        end
    end

    // ============================================================
    // Combinational outputs
    // ============================================================

    // Clock mux: normal mode passes CLK_SAR, cal mode passes CAL_CLK
    // (only while frame_active)
    assign CLK  = cal_mode_i ? (frame_active_i & CAL_CLK) : CLK_SAR;
    assign CAL  = cal_mode_i;
    assign DONE = cal_done_i;
    assign ERR  = cal_error_i;
    assign Bit  = adc_code;

    // BITD_CAL / BITU_CAL: gated by cal_mode_i
    genvar g;
    generate
        for (g = 0; g <= 12; g = g + 1) begin : cal_drive
            assign BITD_CAL[g] = cal_mode_i & d_mask[g];
            assign BITU_CAL[g] = cal_mode_i & u_mask[g];
        end
    endgenerate

endmodule
