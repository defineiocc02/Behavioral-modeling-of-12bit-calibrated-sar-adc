// cdac_model.sv — Behavioral CDAC Model for Simulation (NOT synthesizable)
//
// Models the 138 Cu/side split-CDAC with charge conservation.
// Includes per-side mismatch parameters for calibration verification.
//
// This module is for RTL testbench use only — it provides the analog behavior
// that the calibration FSM interacts with through switch control signals.
//
// Topology:  High[7 caps, 71 Cu] — Bridge[2 Cu] — Low[7 caps, 65 Cu]
// Capacitor mapping:
//   sw_h[6:0] = {H1C(1Cu), H2C(2Cu), H4C(4Cu), H8C-R(8Cu), H8C-A(8Cu), H16C(16Cu), H32C(32Cu)}
//   sw_l[6:0] = {L1C(1Cu), L2C-R(2Cu), L2C-A(2Cu), L4C(4Cu), L8C(8Cu), L16C(16Cu), L32C(32Cu)}

`timescale 1ns / 1ps

module cdac_model #(
  parameter real VCM    = 0.9,
  parameter real VREFP  = 1.8,
  parameter real VREFN  = 0.0,
  parameter real CU_F   = 4.0e-15    // 4 fF
) (
  input  logic [1:0] sw_p_h [6:0],   // P-side high switches
  input  logic [1:0] sw_n_h [6:0],   // N-side high switches
  input  logic [1:0] sw_p_l [6:0],   // P-side low switches
  input  logic [1:0] sw_n_l [6:0],   // N-side low switches
  input  logic       sample,          // sample strobe
  input  real        vinp,            // P-side input during sample
  input  real        vinn,            // N-side input during sample
  output real        vdiff            // VTOP_P - VTOP_N
);

  // ── Switch voltage decode ──
  // 2'b01=VCM, 2'b10=VREFN, 2'b11=VREFP
  function automatic real sw2v(input logic [1:0] sw, input real vin);
    case (sw)
      2'b01: return VCM;
      2'b10: return VREFN;
      2'b11: return VREFP;
      default: return VCM;
    endcase
  endfunction

  // ── Per-side capacitance (with mismatch) ──
  // High: H32(32), H16(16), H8A(8), H8R(8), H4(4), H2(2), H1(1) = 71 Cu
  // Bridge: 2 Cu
  // Low:   L32(32), L16(16), L8(8), L4(4), L2A(2), L2R(2), L1(1) = 65 Cu
  //
  // sw_h index: 0=H32C, 1=H16C, 2=H8C-A, 3=H8C-R, 4=H4C, 5=H2C, 6=H1C
  // sw_l index: 0=L32C, 1=L16C, 2=L8C, 3=L4C, 4=L2C-A, 5=L2C-R, 6=L1C

  real ch_nom [6:0] = '{32.0, 16.0, 8.0, 8.0, 4.0, 2.0, 1.0};
  real cl_nom [6:0] = '{32.0, 16.0, 8.0, 4.0, 2.0, 2.0, 1.0};
  real cb_nom = 2.0;

  // ── Mismatch factors (set from testbench) ──
  real p_mc_h [6:0] = '{1.02, 1.02, 1.02, 1.02, 1.02, 1.02, 1.02};
  real p_mc_l [6:0] = '{1.02, 1.02, 1.02, 1.02, 1.02, 1.02, 1.02};
  real p_mc_b = 1.02;
  real n_mc_h [6:0] = '{0.98, 0.98, 0.98, 0.98, 0.98, 0.98, 0.98};
  real n_mc_l [6:0] = '{0.98, 0.98, 0.98, 0.98, 0.98, 0.98, 0.98};
  real n_mc_b = 0.98;

  // ── Computed capacitances ──
  real p_ch [6:0], p_cl [6:0], p_cb;
  real n_ch [6:0], n_cl [6:0], n_cb;
  real p_ch_total, p_cl_total;
  real n_ch_total, n_cl_total;

  // Matrix coefficients
  real p_a11, p_a12, p_a21, p_a22, p_det;
  real p_ai11, p_ai12, p_ai21, p_ai22;
  real n_a11, n_a12, n_a21, n_a22, n_det;
  real n_ai11, n_ai12, n_ai21, n_ai22;

  // Sampled charge
  real q_top_p, q_bridge_p;
  real q_top_n, q_bridge_n;

  // Solved voltages
  real vtop_p_val, vbridge_p_val;
  real vtop_n_val, vbridge_n_val;

  // Internal
  real b1_p, b2_p, b1_n, b2_n;
  real vh_p [6:0], vh_n [6:0], vl_p [6:0], vl_n [6:0];

  // ── Initialization ──
  initial begin
    for (int i = 0; i < 7; i++) begin
      p_ch[i] = CU_F * ch_nom[i] * p_mc_h[i];
      p_cl[i] = CU_F * cl_nom[i] * p_mc_l[i];
      n_ch[i] = CU_F * ch_nom[i] * n_mc_h[i];
      n_cl[i] = CU_F * cl_nom[i] * n_mc_l[i];
    end
    p_cb = CU_F * cb_nom * p_mc_b;
    n_cb = CU_F * cb_nom * n_mc_b;

    p_ch_total = p_ch[0] + p_ch[1] + p_ch[2] + p_ch[3] + p_ch[4] + p_ch[5] + p_ch[6];
    p_cl_total = p_cl[0] + p_cl[1] + p_cl[2] + p_cl[3] + p_cl[4] + p_cl[5] + p_cl[6];
    n_ch_total = n_ch[0] + n_ch[1] + n_ch[2] + n_ch[3] + n_ch[4] + n_ch[5] + n_ch[6];
    n_cl_total = n_cl[0] + n_cl[1] + n_cl[2] + n_cl[3] + n_cl[4] + n_cl[5] + n_cl[6];

    // Precompute inverse matrices
    p_a11 = p_ch_total + p_cb;  p_a12 = -p_cb;
    p_a21 = -p_cb;              p_a22 = p_cl_total + p_cb;
    p_det = p_a11 * p_a22 - p_a12 * p_a21;
    p_ai11 =  p_a22 / p_det;    p_ai12 = -p_a12 / p_det;
    p_ai21 = -p_a21 / p_det;    p_ai22 =  p_a11 / p_det;

    n_a11 = n_ch_total + n_cb;  n_a12 = -n_cb;
    n_a21 = -n_cb;              n_a22 = n_cl_total + n_cb;
    n_det = n_a11 * n_a22 - n_a12 * n_a21;
    n_ai11 =  n_a22 / n_det;    n_ai12 = -n_a12 / n_det;
    n_ai21 = -n_a21 / n_det;    n_ai22 =  n_a11 / n_det;
  end

  // ── Main solve loop ──
  always @(*) begin
    // Decode switch states to voltages
    for (int i = 0; i < 7; i++) begin
      vh_p[i] = sw2v(sw_p_h[i], vinp);
      vh_n[i] = sw2v(sw_n_h[i], vinn);
      vl_p[i] = sw2v(sw_p_l[i], vinp);
      vl_n[i] = sw2v(sw_n_l[i], vinn);
    end

    // Compute RHS: b = Q + sum(C_i * Vbot_i)
    b1_p = q_top_p
         + p_ch[0]*vh_p[0] + p_ch[1]*vh_p[1] + p_ch[2]*vh_p[2]
         + p_ch[3]*vh_p[3] + p_ch[4]*vh_p[4] + p_ch[5]*vh_p[5] + p_ch[6]*vh_p[6];
    b2_p = q_bridge_p
         + p_cl[0]*vl_p[0] + p_cl[1]*vl_p[1] + p_cl[2]*vl_p[2]
         + p_cl[3]*vl_p[3] + p_cl[4]*vl_p[4] + p_cl[5]*vl_p[5] + p_cl[6]*vl_p[6];

    b1_n = q_top_n
         + n_ch[0]*vh_n[0] + n_ch[1]*vh_n[1] + n_ch[2]*vh_n[2]
         + n_ch[3]*vh_n[3] + n_ch[4]*vh_n[4] + n_ch[5]*vh_n[5] + n_ch[6]*vh_n[6];
    b2_n = q_bridge_n
         + n_cl[0]*vl_n[0] + n_cl[1]*vl_n[1] + n_cl[2]*vl_n[2]
         + n_cl[3]*vl_n[3] + n_cl[4]*vl_n[4] + n_cl[5]*vl_n[5] + n_cl[6]*vl_n[6];

    // Solve: V = A_inv * b
    vtop_p_val    = p_ai11 * b1_p + p_ai12 * b2_p;
    vbridge_p_val = p_ai21 * b1_p + p_ai22 * b2_p;
    vtop_n_val    = n_ai11 * b1_n + n_ai12 * b2_n;
    vbridge_n_val = n_ai21 * b1_n + n_ai22 * b2_n;
  end

  // ── Sampling ──
  // Sample: all bottom plates → VIN, VTOP forced to VCM
  // VBRIDGE finds DC operating point from capacitance divider
  always @(posedge sample) begin
    // All caps switch to input during sample
    // VTOP = VCM forced by sample switches
    // VBRIDGE = DC solution from cap divider with VTOP=VCM

    // For simplicity: assume VBRIDGE ≈ VCM during sampling
    // (exact value depends on VIN, but for differential VIN ≈ VCM it's valid)
    // Compute charge with VTOP=VCM
    vtop_p_val = VCM;  vtop_n_val = VCM;
    vbridge_p_val = VCM;  vbridge_n_val = VCM;

    // Q_top = C_high*(VCM-VIN) + C_bridge*(VCM-VBRIDGE)
    q_top_p = p_ch_total * (VCM - vinp) + p_cb * (VCM - VCM);
    q_top_n = n_ch_total * (VCM - vinn) + n_cb * (VCM - VCM);
    q_bridge_p = p_cb * (VCM - VCM) + p_cl_total * (VCM - vinp);
    q_bridge_n = n_cb * (VCM - VCM) + n_cl_total * (VCM - vinn);
  end

  // ── Output ──
  assign vdiff = vtop_p_val - vtop_n_val;

endmodule
