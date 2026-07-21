// Synthesizable RTL version of DEC_CAL_PHY.va
// V6.3: Identifiability-fixed 3-target calibration with implicit gauge.
//
// HISTORY:
//   V6:   3-target (w2, w1, w0), 7-bit calDAC.
//   V6.1: 4-target (+ w3+w4 joint). E propagation reduced to 1/1/1x.
//   V6.2: + w2 re-correction + saturation flag. DEFECT (user-identified):
//         w2 re-correction is mathematically invalid (reciprocal
//         measurement yields measured=512 identically).
//   V6.3: This version. Fixes V6.2 identifiability bug and all P0 issues.
//
// V6.3 DESIGN (see doc/PROOF_V6_3_IDENTIFIABILITY.md):
//   1) W3+W4 := 512 (implicit gauge, layout matching, |e3+e4| < ~1%).
//   2) 3-target recursive calibration: W2, W1, W0.
//      Earlier V6.3 comments claimed "w1/w0 exact under gauge". Independent
//      review found a sign error in that derivation. The actual propagation:
//      - target 2: W2,    wall = W3+W4 (gauge=512)
//                   R = e2 - E    →    w2 = 512 + (e2 - E)    [residual -E]
//      - target 1: W1,    wall = w2 + 512 = 1024 + (e2 - E)
//                   R = e1 - e2 - E
//                   w1 = 1024 + e1 - 2E                        [residual -2E]
//      - target 0: W0,    wall = w1 + w2 + 512 = 2048 + e1 + e2 - 3E
//                   R = e0 - e1 - e2 - E
//                   w0 = 2048 + e0 - 4E                        [residual -4E]
//      Net: E propagates as (-E, -2E, -4E) to (w2, w1, w0). This matches
//      V6 (no gauge) — V6.3 does NOT improve E propagation over V6.
//   3) Does NOT calibrate W5 (proven unmeasurable with ±126 calDAC).
//   4) Does NOT measure common-mode gain (all walls are differential).
//
// P0/P1 BUG FIXES vs V6.2 (including V6.3 review P0-2/P1-1/P1-2/P1-4):
//   a) wall_weight_q initialized in initial block (was only set on CAL_RST
//      negedge; broken if CAL_RST starts low at t=0).
//   b) Single RST1 posedge handler (P0-2): direction-finish runs FIRST
//      and may set finish_pending_i on the last target; handoff runs as
//      an INDEPENDENT if (not else-if) so DONE fires on the SAME RST1
//      edge (no extra frame needed).
//   c) REJECT now sets cal_degraded_i; if any target rejected, ERR=1 at
//      finish and downstream targets continue with nominal weights.
//      Normal decoder does NOT apply partial calibrated weights when
//      ERR=1 — it falls back to nominal weights (P1-4 safe fail policy).
//   d) saturate_flag (single-bit) replaced by per-pair saturate_count
//      (P1-1). A pair is saturated if EITHER D+ OR D- hits the calDAC
//      endpoint; per-pair OR is evaluated at D- completion so each pair
//      contributes at most 1 (was 2 per pair, max 2*avg_pairs, before).
//      Saturated pairs are EXCLUDED from accum_d_plus/accum_d_minus
//      (P1-2); residual_q is computed over valid_pair_count only.
//      A target is rejected if saturate_count*100 > SAT_RATIO_PCT*AP
//      OR if valid_pair_count == 0 (all pairs saturated).
//   e) Dead parameter NORMALIZE_REDUNDANT_RANGE removed (also
//      REMOVE_REDUNDANCY_OFFSET — never gated any logic).
//
// Converts the Verilog-A behavioral calibration engine + decoder into
// synthesizable Verilog-2001 RTL. All analog constructs (electrical,
// V(), transition(), @cross) are replaced with standard digital logic.
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
    // V6.3 review fix R3-N: removed dead parameter REMOVE_REDUNDANCY_OFFSET
    // (was declared but never gated any logic; offset removal is always-on).
    parameter CMP_SWAP         = 1;
    parameter WEIGHT_TOL_PCT   = 35;  // 35% tolerance (integer percent)
    parameter FRAC_BITS        = 6;   // Q-format fractional bits
    parameter RAW_INVERT       = 0;
    parameter FIRST_INVERT     = 0;
    parameter SAT_RATIO_PCT    = 50;  // V6.3: sat reject threshold (%)
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
    reg        cal_degraded_i;   // V6.3: any target rejected
    reg        finish_pending_i;
    reg        frame_active_i;
    reg        zero_force_i;
    integer    invalid_count;
    // V6.3 review P1-1/P1-2: per-pair saturation accounting.
    //   d_plus_saturated  : set when D+ code hits calDAC endpoint.
    //   pair_saturated    : OR of D+ and D- saturation for current pair.
    //   saturate_count    : number of saturated pairs (0..avg_pairs).
    //   valid_pair_count  : number of non-saturated pairs accumulated.
    // Saturated pairs are excluded from accum_d_plus/accum_d_minus; the
    // residual is computed over valid_pair_count only.
    reg        d_plus_saturated;
    reg        pair_saturated;
    integer    saturate_count;
    integer    valid_pair_count;
    integer    target_rejected;  // V6.3: current target rejection flag

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
    integer    adc_code_int;   // V6.3 review fix: wide temp for clip
    reg [11:0] adc_code;

    reg        cmp_p_gt_n;

    // ============================================================
    // Initialization
    // ============================================================
    initial begin
        cal_state        = CAL_IDLE;
        sar_step         = 0;
        trial_mask       = 0;
        switched_mask    = 0;
        switched_sum     = 0;
        d_plus_code      = 0;
        d_minus_code     = 0;
        direction        = 0;
        target_idx       = 2;        // V6.3: 3-target, start at W2
        target_mask      = 4;
        wall_mask        = 24;
        d_mask           = 0;
        u_mask           = 0;
        repeat_idx       = 0;
        accum_d_plus     = 0;
        accum_d_minus    = 0;

        cal_mode_i       = 1'b0;
        cal_done_i       = (CAL_BYPASS != 0) ? 1'b1 : 1'b0;
        cal_error_i      = 1'b0;
        cal_degraded_i   = 1'b0;
        finish_pending_i = 1'b0;
        frame_active_i   = 1'b0;
        zero_force_i     = 1'b0;
        invalid_count    = 0;
        saturate_count   = 0;
        target_rejected  = 0;
        d_plus_saturated = 1'b0;
        pair_saturated   = 1'b0;
        valid_pair_count = 0;

        w0  = 2048*QS; w1  = 1024*QS; w2  = 512*QS;
        w3  = 256*QS;  w4  = 256*QS;  w5  = 128*QS;
        w6  = 48*QS;   w7  = 32*QS;   w8  = 20*QS;
        w9  = 12*QS;   w10 = 8*QS;    w11 = 4*QS;
        w12 = 2*QS;    w13 = QS;

        measured_weight_q = 0;
        // V6.3 P0 fix: initialize wall here (not only on CAL_RST negedge).
        wall_weight_q     = w3 + w4;
        residual_q        = 0;
        adc_code_int      = 0;   // V6.3 review fix: init wide temp
        adc_code          = 12'd0;
    end

    // ============================================================
    // CAL_RST rising: reset all state
    // ============================================================
    always @(posedge CAL_RST) begin
        cal_state        = CAL_IDLE;
        sar_step         = 0;
        trial_mask       = 0;
        switched_mask    = 0;
        switched_sum     = 0;
        d_plus_code      = 0;
        d_minus_code     = 0;
        direction        = 0;
        target_idx       = 2;        // V6.3: 3-target
        target_mask      = 4;
        wall_mask        = 24;
        d_mask           = 0;
        u_mask           = 0;
        repeat_idx       = 0;
        accum_d_plus     = 0;
        accum_d_minus    = 0;

        cal_mode_i       = 1'b0;
        cal_done_i       = (CAL_BYPASS != 0) ? 1'b1 : 1'b0;
        cal_error_i      = 1'b0;
        cal_degraded_i   = 1'b0;
        finish_pending_i = 1'b0;
        frame_active_i   = 1'b0;
        zero_force_i     = 1'b0;
        invalid_count    = 0;
        saturate_count   = 0;
        target_rejected  = 0;
        d_plus_saturated = 1'b0;
        pair_saturated   = 1'b0;
        valid_pair_count = 0;

        w0  = 2048*QS; w1  = 1024*QS; w2  = 512*QS;
        w3  = 256*QS;  w4  = 256*QS;  w5  = 128*QS;
        w6  = 48*QS;   w7  = 32*QS;   w8  = 20*QS;
        w9  = 12*QS;   w10 = 8*QS;    w11 = 4*QS;
        w12 = 2*QS;    w13 = QS;

        wall_weight_q = w3 + w4;
        adc_code      = 12'd0;
    end

    // ============================================================
    // CAL_RST falling: start calibration
    // ============================================================
    always @(negedge CAL_RST) begin
        if (CAL_BYPASS == 0) begin
            cal_state        = CAL_IDLE;
            sar_step         = 0;
            trial_mask       = 0;
            switched_mask    = 0;
            switched_sum     = 0;
            d_plus_code      = 0;
            d_minus_code     = 0;
            direction        = 0;
            target_idx       = 2;        // V6.3: 3-target
            target_mask      = 4;
            wall_mask        = 24;
            d_mask           = 0;
            u_mask           = 0;
            repeat_idx       = 0;
            accum_d_plus     = 0;
            accum_d_minus    = 0;

            cal_mode_i       = 1'b1;
            cal_done_i       = 1'b0;
            cal_error_i      = 1'b0;
            cal_degraded_i   = 1'b0;
            finish_pending_i = 1'b0;
            frame_active_i   = 1'b0;
            zero_force_i     = 1'b0;
            invalid_count    = 0;
            saturate_count   = 0;
            target_rejected  = 0;
            d_plus_saturated = 1'b0;
            pair_saturated   = 1'b0;
            valid_pair_count = 0;
            wall_weight_q    = w3 + w4;

            if (DEBUG != 0)
                $display("OFFSAR start avg_pairs=%0d Q=%0d targets=3 (gauge W3+W4=512)",
                    AP, FB);
        end
    end

    // ============================================================
    // RST1 falling: start frame
    // ============================================================
    always @(negedge RST1) begin
        if (cal_mode_i && !finish_pending_i) begin
            frame_active_i   = 1'b1;
            d_mask           = 0;
            u_mask           = 0;
            cal_state        = CAL_PRECHARGE;
            sar_step         = 0;
            trial_mask       = 0;
            switched_mask    = 0;
            switched_sum     = 0;
            zero_force_i     = 1'b0;
            if (DEBUG > 1)
                $display("OFFSAR frame start target=%0d dir=%0d pair=%0d",
                    target_idx, direction, repeat_idx);
        end
    end

    // ============================================================
    // CAL_CLK rising: set up trial
    // ============================================================
    always @(posedge CAL_CLK) begin
        if (cal_mode_i && frame_active_i && !finish_pending_i) begin

            if (cal_state == CAL_PRECHARGE) begin
                switched_mask = 0;
                switched_sum  = 0;
                sar_step      = 0;
                cal_state     = CAL_SAR_TRIAL;
                trial_mask    = 64;  // stage 6 = C7, weight 48
            end else if (cal_state == CAL_SAR_TRIAL) begin
                case (sar_step)
                    0: trial_mask = 64;
                    1: trial_mask = 128;
                    2: trial_mask = 256;
                    3: trial_mask = 512;
                    4: trial_mask = 1024;
                    5: trial_mask = 2048;
                    6: trial_mask = 4096;
                    default: trial_mask = 0;
                endcase
            end

            if (direction == 0) begin
                d_mask = target_mask |
                         (CALDAC_MASK & ~(switched_mask | trial_mask));
                u_mask = wall_mask | switched_mask | trial_mask;
            end else begin
                d_mask = wall_mask |
                         (CALDAC_MASK & ~(switched_mask | trial_mask));
                u_mask = target_mask | switched_mask | trial_mask;
            end
        end
    end

    // ============================================================
    // CAL_CLK falling: latch comparator, decide keep/undo
    //   R3 review note: the VA reference also models an invalid_count
    //   path that triggers cal_error_i/finish_pending_i when the
    //   comparator output is metastable or below CMP_VALID_FRACTION for
    //   more than MAX_INVALID samples (with a ZERO_ON_INVALID_PHASE0
    //   fallback that forces a default decision). This RTL assumes the
    //   digital comparator always produces a valid 1-of-2 result on
    //   CAL_CLK negedge (COMP^COMN == 1). If the upstream comparator
    //   can be invalid, the user must add an equivalent guard externally
    //   — the calibration result is undefined when the assumption breaks.
    // ============================================================
    always @(negedge CAL_CLK) begin
        if (cal_mode_i && frame_active_i && !finish_pending_i &&
            (cal_state != CAL_PRECHARGE)) begin

            // Digital comparator: COMP=1 means P>N, COMN=1 means N>P.
            // With CMP_SWAP, polarity is inverted.
            // V6.3 review fix R2-A: only flip on a real update. The original
            // code unconditionally flipped even when COMP==COMN (no update),
            // corrupting the held cmp_p_gt_n value.
            if (COMP ^ COMN) begin
                cmp_p_gt_n = COMP;
                if (CMP_SWAP != 0)
                    cmp_p_gt_n = ~cmp_p_gt_n;
            end

            if (cal_state == CAL_SAR_TRIAL) begin
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
                    cal_state = CAL_TERMINAL;
            end else if (cal_state == CAL_TERMINAL) begin
                // Terminal bit: b_T = cmp_p_gt_n
                // Code value in 0..127.
                if (direction == 0) begin
                    d_plus_code  = switched_sum + (cmp_p_gt_n ? 1 : 0);
                    // V6.3 review P1-1: track D+ saturation as a per-pair
                    // flag (counter incremented at D- completion in the
                    // RST1 posedge handler).
                    d_plus_saturated = (d_plus_code >= 126 ||
                                        d_plus_code <= 1) ? 1'b1 : 1'b0;
                    if (d_plus_saturated && (DEBUG != 0))
                        $display("OFFSAR SATURATE target=%0d dir=+ code=%0d",
                            target_idx, d_plus_code);
                    if (DEBUG > 1)
                        $display("OFFSAR code target=%0d dir=+ D+=%0d",
                            target_idx, d_plus_code);
                end else begin
                    d_minus_code = switched_sum + (cmp_p_gt_n ? 1 : 0);
                    // D- saturation flag is folded into pair_saturated at
                    // D- completion (RST1 posedge). No counter here.
                    if ((d_minus_code >= 126 || d_minus_code <= 1) &&
                        (DEBUG != 0))
                        $display("OFFSAR SATURATE target=%0d dir=- code=%0d",
                            target_idx, d_minus_code);
                    if (DEBUG > 1)
                        $display("OFFSAR code target=%0d dir=- D-=%0d",
                            target_idx, d_minus_code);
                end

                cal_state = CAL_FINISH_DIR;
            end
        end
    end

    // ============================================================
    // RST1 rising: end frame, finish direction, handoff
    //   V6.3 P0-2 fix: direction-finish runs FIRST and may set
    //   finish_pending_i on the last target; handoff is then run by
    //   an INDEPENDENT if (not else-if) so DONE fires on the SAME
    //   RST1 edge (no extra frame needed).
    // ============================================================
    always @(posedge RST1) begin
        frame_active_i = 1'b0;
        d_mask = 0;
        u_mask = 0;

        // (A) Direction finish: compute weight or switch direction.
        //     Guard with !finish_pending_i so we don't re-enter after
        //     a CMP_INVALID path or a previous target already set it.
        if (cal_mode_i && !finish_pending_i &&
            (cal_state == CAL_FINISH_DIR)) begin
            if (direction == 0) begin
                // D+ done, start D-.
                direction = 1;
                cal_state = CAL_IDLE;
            end else begin
                // Both directions done, finalize one pair.
                // V6.3 review P1-1: per-pair saturation OR.
                // V6.3 review P1-2: saturated pairs excluded from accum
                //                    and from the residual divisor.
                pair_saturated = d_plus_saturated ||
                    (d_minus_code >= 126 || d_minus_code <= 1);
                if (!pair_saturated) begin
                    accum_d_plus  = accum_d_plus  + d_plus_code;
                    accum_d_minus = accum_d_minus + d_minus_code;
                    valid_pair_count = valid_pair_count + 1;
                end else begin
                    saturate_count = saturate_count + 1;
                end
                repeat_idx = repeat_idx + 1;
                d_plus_saturated = 1'b0;

                if (DEBUG > 1)
                    $display("OFFSAR pair tgt=%0d D+=%0d D-=%0d pair=%0d sat_pairs=%0d valid=%0d",
                        target_idx, d_plus_code, d_minus_code,
                        repeat_idx, saturate_count, valid_pair_count);

                if (repeat_idx >= AP) begin
                    // Q-format: R_Q = round(QS * (sum_D+ - sum_D-) / N)
                    // Divisor is valid_pair_count (non-saturated pairs).
                    // V6.3 review fix R2-46: use / instead of >> to match VA
                    // semantics for negative dividends (>> is arithmetic shift
                    // rounding toward -inf; / rounds toward zero like C and
                    // like the VA reference).
                    if (valid_pair_count == 0) begin
                        target_rejected = 1;
                        residual_q = 0;
                        measured_weight_q = wall_weight_q;
                        if (DEBUG != 0)
                            $display("OFFSAR REJECT tgt=%0d all_pairs_saturated sat=%0d/%0d",
                                target_idx, saturate_count, AP);
                    end else begin
                        if ((accum_d_plus - accum_d_minus) >= 0)
                            rounding_term = valid_pair_count / 2;
                        else
                            rounding_term = -valid_pair_count / 2;
                        residual_q = (QS * (accum_d_plus - accum_d_minus)
                                     + rounding_term) / valid_pair_count;

                        measured_weight_q = wall_weight_q + residual_q;

                        if (DEBUG != 0)
                            $display("OFFSAR measure tgt=%0d wall_q=%0d R_q=%0d measured_q=%0d valid=%0d/%0d",
                                target_idx, wall_weight_q, residual_q,
                                measured_weight_q, valid_pair_count, AP);

                        // V6.3 review P1-1: per-pair saturation test.
                        if (saturate_count * 100 > SAT_RATIO_PCT * AP) begin
                            target_rejected = 1;
                            if (DEBUG != 0)
                                $display("OFFSAR REJECT tgt=%0d measured_q=%0d sat_pairs=%0d/%0d",
                                    target_idx, measured_weight_q,
                                    saturate_count, AP);
                        end else begin
                            // Tolerance check: |measured - target| <= target * tol%
                            // Rewrite as multiply-only:
                            //   measured * 100 >= target_q * (100 - TOL)
                            //   measured * 100 <= target_q * (100 + TOL)
                            case (target_idx)
                                2: begin
                                    if ((measured_weight_q * 100 >= 512*QS*(100 - WEIGHT_TOL_PCT)) &&
                                        (measured_weight_q * 100 <= 512*QS*(100 + WEIGHT_TOL_PCT))) begin
                                        w2 = measured_weight_q;
                                        if (DEBUG != 0)
                                            $display("OFFSAR ACCEPT tgt=2 w2=%0d", w2);
                                    end else
                                        target_rejected = 1;
                                end
                                1: begin
                                    if ((measured_weight_q * 100 >= 1024*QS*(100 - WEIGHT_TOL_PCT)) &&
                                        (measured_weight_q * 100 <= 1024*QS*(100 + WEIGHT_TOL_PCT))) begin
                                        w1 = measured_weight_q;
                                        if (DEBUG != 0)
                                            $display("OFFSAR ACCEPT tgt=1 w1=%0d", w1);
                                    end else
                                        target_rejected = 1;
                                end
                                0: begin
                                    if ((measured_weight_q * 100 >= 2048*QS*(100 - WEIGHT_TOL_PCT)) &&
                                        (measured_weight_q * 100 <= 2048*QS*(100 + WEIGHT_TOL_PCT))) begin
                                        w0 = measured_weight_q;
                                        if (DEBUG != 0)
                                            $display("OFFSAR ACCEPT tgt=0 w0=%0d", w0);
                                    end else
                                        target_rejected = 1;
                                end
                                default: target_rejected = 1;
                            endcase
                            if (target_rejected && (DEBUG != 0))
                                $display("OFFSAR REJECT tgt=%0d measured_q=%0d tol=%0d%%",
                                    target_idx, measured_weight_q, WEIGHT_TOL_PCT);
                        end
                    end

                    // V6.3: mark degraded if rejected.
                    if (target_rejected) begin
                        cal_degraded_i  = 1'b1;
                        target_rejected = 0;
                    end

                    // Advance to next target.
                    target_idx = target_idx - 1;
                    repeat_idx = 0;
                    accum_d_plus = 0;
                    accum_d_minus = 0;
                    saturate_count = 0;
                    valid_pair_count = 0;
                    d_plus_saturated = 1'b0;
                    pair_saturated = 1'b0;

                    case (target_idx)
                        1: begin
                            // Next: W1, wall = W2+W3+W4
                            target_mask = 2;
                            wall_mask   = 28;
                            wall_weight_q = w2 + w3 + w4;
                        end
                        0: begin
                            // Next: W0, wall = W1+W2+W3+W4
                            target_mask = 1;
                            wall_mask   = 30;
                            wall_weight_q = w1 + w2 + w3 + w4;
                        end
                        default: begin
                            finish_pending_i = 1'b1;
                            target_idx = -1;
                        end
                    endcase
                    direction = 0;
                end else begin
                    direction = 0;
                end
                cal_state = CAL_IDLE;
            end
        end

        // (B) Handoff: calibration complete. Independent if (NOT else-if)
        //     so it can fire on the SAME RST1 edge where the last target
        //     just set finish_pending_i = 1 in step (A) above.
        if (cal_mode_i && finish_pending_i) begin
            cal_mode_i  = 1'b0;
            if (cal_error_i) begin
                // Hard error: restore nominal weights.
                w0  = 2048*QS; w1  = 1024*QS; w2  = 512*QS;
                w3  = 256*QS;  w4  = 256*QS;  w5  = 128*QS;
                w6  = 48*QS;   w7  = 32*QS;   w8  = 20*QS;
                w9  = 12*QS;   w10 = 8*QS;    w11 = 4*QS;
                w12 = 2*QS;    w13 = QS;
            end
            // V6.3: degraded → ERR=1. The normal decoder (see SOUT handler)
            // gates calibrated weight application on !cal_error_i, so a
            // degraded run causes the decoder to fall back to nominal
            // weights (no partial-cal application). This makes "caller can
            // decide" actually true: ERR=1 → decoder uses nominal.
            if (cal_degraded_i)
                cal_error_i = 1'b1;
            cal_done_i = 1'b1;
            if (DEBUG != 0) begin
                $display("OFFSAR finish done=%0d err=%0d degraded=%0d",
                    cal_done_i, cal_error_i, cal_degraded_i);
                $display("OFFSAR weights_q={%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d} Q=%0d",
                    w0, w1, w2, w3, w4, w5, w6, w7, w8,
                    w9, w10, w11, w12, w13, FB);
            end
        end
    end

    // ============================================================
    // Normal decoder: latch one completed RAW conversion on SOUT
    // ============================================================
    always @(posedge SOUT) begin
        if ((CAL_BYPASS != 0) ||
            (cal_done_i && !cal_mode_i)) begin
            r0  = BP[13];
            r1  = BP[12];
            r2  = BP[11];
            r3  = BP[10];
            r4  = BP[9];
            r5  = BP[8];
            r6  = BP[7];
            r7  = BP[6];
            r8  = BP[5];
            r9  = BP[4];
            r10 = BP[3];
            r11 = BP[2];
            r12 = BP[1];
            r13 = BP[0];

            if (RAW_INVERT != 0) begin
                r1 = 1-r1;   r2 = 1-r2;   r3 = 1-r3;
                r4 = 1-r4;   r5 = 1-r5;   r6 = 1-r6;
                r7 = 1-r7;   r8 = 1-r8;   r9 = 1-r9;
                r10 = 1-r10; r11 = 1-r11; r12 = 1-r12;
                r13 = 1-r13;
            end
            if (FIRST_INVERT != 0)
                r0 = 1-r0;

            // V6.3 review P1-4: decoder fail policy. Calibrated weights
            // are applied ONLY when (a) the user has enabled APPLY_CAL_WEIGHT
            // AND (b) calibration completed without error (!cal_error_i).
            // If ERR=1 (degraded or hard error), the decoder falls back to
            // nominal weights — partial calibration is NOT silently applied.
            // This makes the "caller can decide" contract honest: ERR=1
            // means the decoder is using nominal weights, not partial.
            if ((APPLY_CAL_WEIGHT != 0) && (cal_error_i == 1'b0)) begin
                dec_w0 = w0; dec_w1 = w1; dec_w2 = w2;
            end else begin
                dec_w0 = 2048*QS;
                dec_w1 = 1024*QS;
                dec_w2 = 512*QS;
            end

            raw_sum = r0*dec_w0 + r1*dec_w1 + r2*dec_w2 +
                r3*w3 + r4*w4 + r5*w5 + r6*w6 + r7*w7 +
                r8*w8 + r9*w9 + r10*w10 + r11*w11 +
                r12*w12 + r13*w13;

            total_weight_q = dec_w0 + dec_w1 + dec_w2 +
                w3 + w4 + w5 + w6 + w7 + w8 + w9 +
                w10 + w11 + w12 + w13;

            // Symmetric redundancy offset removal.
            // V6.3 review fix R2-46: use / instead of >> to match VA semantics.
            // Verilog integer / rounds toward zero (like C), while >> on a
            // signed value is arithmetic shift (rounds toward -inf). The two
            // diverge for negative dividends; the VA reference uses /, so we
            // use / here as well.
            redundancy_offset_q = total_weight_q - 4095*QS;
            if (redundancy_offset_q >= 0)
                redundancy_offset_q = (redundancy_offset_q + 1) / 2;
            else
                redundancy_offset_q = (redundancy_offset_q - 1) / 2;
            centered_sum = raw_sum - redundancy_offset_q;

            // V6.3 review fix: compute in wide integer, then clip, then
            // narrow to 12-bit. Prevents 12-bit overflow wrap-around that
            // would bypass the > 4095 clip check.
            if (centered_sum >= 0)
                adc_code_int = (centered_sum + QS/2) / QS;
            else
                adc_code_int = (centered_sum - QS/2) / QS;

            if (adc_code_int < 0)
                adc_code_int = 0;
            else if (adc_code_int > 4095)
                adc_code_int = 4095;
            adc_code = adc_code_int[11:0];
        end
    end

    // ============================================================
    // Output drivers
    // ============================================================
    assign CAL  = cal_mode_i;
    assign DONE = cal_done_i;
    assign ERR  = cal_error_i;
    assign CLK  = cal_mode_i ? (frame_active_i & CAL_CLK)
                             : CLK_SAR;

    assign Bit[0]  = adc_code[0];
    assign Bit[1]  = adc_code[1];
    assign Bit[2]  = adc_code[2];
    assign Bit[3]  = adc_code[3];
    assign Bit[4]  = adc_code[4];
    assign Bit[5]  = adc_code[5];
    assign Bit[6]  = adc_code[6];
    assign Bit[7]  = adc_code[7];
    assign Bit[8]  = adc_code[8];
    assign Bit[9]  = adc_code[9];
    assign Bit[10] = adc_code[10];
    assign Bit[11] = adc_code[11];

    genvar g;
    generate
        for (g = 0; g <= 12; g = g + 1) begin : gen_bitd
            assign BITD_CAL[g] = cal_mode_i & ((d_mask >> g) & 1);
            assign BITU_CAL[g] = cal_mode_i & ((u_mask >> g) & 1);
        end
    endgenerate

endmodule
