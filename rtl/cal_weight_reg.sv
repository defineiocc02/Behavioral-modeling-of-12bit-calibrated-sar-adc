// cal_weight_reg.sv — Calibrated Weight Register File
`timescale 1ns / 1ps
//
// 7 × 2 entries (P-side + N-side per target), 20-bit Q8 each.
// Simple synchronous write, combinatorial read.

module cal_weight_reg #(
  parameter int N_TARGETS    = 7,
  parameter int WEIGHT_WIDTH = 20
) (
  input  logic                          clk,
  input  logic                          rst_n,
  input  logic                          we,
  input  logic [$clog2(N_TARGETS)-1:0]  addr,
  input  logic [WEIGHT_WIDTH-1:0]       wp_in,
  input  logic [WEIGHT_WIDTH-1:0]       wn_in,
  output logic [WEIGHT_WIDTH-1:0]       wp_out [N_TARGETS-1:0],
  output logic [WEIGHT_WIDTH-1:0]       wn_out [N_TARGETS-1:0]
);

  logic [WEIGHT_WIDTH-1:0] wp_reg [N_TARGETS-1:0];
  logic [WEIGHT_WIDTH-1:0] wn_reg [N_TARGETS-1:0];

  // ── Default weights (nominal Q8) ──
  // H1C=67, H2C=134, H4C=268, H8C-R=536, H8C-A=536, H16C=1072, H32C=2144
  localparam logic [WEIGHT_WIDTH-1:0] NOMINAL_Q8 [0:6] = '{
    17152, 34304, 68608, 137216, 137216, 274432, 548864
  };

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      for (int i = 0; i < N_TARGETS; i++) begin
        wp_reg[i] <= NOMINAL_Q8[i];
        wn_reg[i] <= NOMINAL_Q8[i];
      end
    end else if (we) begin
      wp_reg[addr] <= wp_in;
      wn_reg[addr] <= wn_in;
    end
  end

  // ── Read outputs (combinational) ──
  always_comb begin
    for (int i = 0; i < N_TARGETS; i++) begin
      wp_out[i] = wp_reg[i];
      wn_out[i] = wn_reg[i];
    end
  end

endmodule
