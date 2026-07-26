// tb_sar_subconverter.sv -- self-check recursive Q8 ruler use
`timescale 1ns / 1ps

module tb_sar_subconverter;
  parameter int CLK_PERIOD_NS = 10;
  parameter int WEIGHT_WIDTH = 20;
  parameter int SUBSUM_WIDTH = 24;

  logic clk = 0;
  logic rst_n;
  logic start;
  logic [2:0] target_idx;
  logic [2:0] phase;
  logic cmp_out;
  logic [WEIGHT_WIDTH-1:0] weights_p [6:0];
  logic [WEIGHT_WIDTH-1:0] weights_n [6:0];
  logic [1:0] sw_p_h [6:0];
  logic [1:0] sw_n_h [6:0];
  logic [1:0] sw_p_l [6:0];
  logic [1:0] sw_n_l [6:0];
  logic done;
  logic signed [SUBSUM_WIDTH-1:0] signed_sum;

  integer expected_p_q8;
  integer expected_n_q8;
  integer timeout_cycles;

  always #(CLK_PERIOD_NS/2) clk = ~clk;

  sar_subconverter #(
    .WEIGHT_WIDTH(WEIGHT_WIDTH),
    .SUBSUM_WIDTH(SUBSUM_WIDTH)
  ) u_dut (
    .clk(clk),
    .rst_n(rst_n),
    .start(start),
    .target_idx(target_idx),
    .phase(phase),
    .cmp_out(cmp_out),
    .weights_p(weights_p),
    .weights_n(weights_n),
    .sw_p_h(sw_p_h),
    .sw_n_h(sw_n_h),
    .sw_p_l(sw_p_l),
    .sw_n_l(sw_n_l),
    .done(done),
    .signed_sum(signed_sum)
  );

  task automatic pulse_start;
    begin
      start = 1'b1;
      @(posedge clk);
      start = 1'b0;
    end
  endtask

  task automatic wait_and_check(input integer expected);
    begin
      timeout_cycles = 0;
      while (!done && timeout_cycles < 200) begin
        @(posedge clk);
        timeout_cycles = timeout_cycles + 1;
      end
      if (!done)
        $fatal(1, "timeout waiting for lower-SAR done");
      // signed_sum is registered in SAR_DONE; sample after the NBA update.
      #1;
      if ($signed(signed_sum) !== expected)
        $fatal(
          1,
          "recursive Q8 sum mismatch: got=%0d expected=%0d",
          $signed(signed_sum),
          expected
        );
      @(posedge clk);
    end
  endtask

  initial begin
    // Register index order: H1, H2, H4, H8-R, H8-A, H16, H32.
    weights_p[0] = (67   << 8) + 8;
    weights_p[1] = (134  << 8) + 16;
    weights_p[2] = (268  << 8) + 24;
    weights_p[3] = (536  << 8) + 32;
    weights_p[4] = (536  << 8) + 40;
    weights_p[5] = (1072 << 8) + 48;
    weights_p[6] = (2144 << 8) + 56;

    weights_n[0] = (67   << 8) - 8;
    weights_n[1] = (134  << 8) - 16;
    weights_n[2] = (268  << 8) - 24;
    weights_n[3] = (536  << 8) - 32;
    weights_n[4] = (536  << 8) - 40;
    weights_n[5] = (1072 << 8) - 48;
    weights_n[6] = (2144 << 8) - 56;

    // H32 uses the six already-calibrated high targets plus the 131-Q0
    // low/terminal base ruler.  H32 itself (register 6) is excluded.
    expected_p_q8 = (131 << 8);
    expected_n_q8 = (131 << 8);
    for (int i = 0; i < 6; i++) begin
      expected_p_q8 = expected_p_q8 + weights_p[i];
      expected_n_q8 = expected_n_q8 + weights_n[i];
    end

    rst_n = 0;
    start = 0;
    target_idx = 3'd6;
    phase = 3'd1;
    cmp_out = 0;
    repeat (5) @(posedge clk);
    rst_n = 1;
    repeat (2) @(posedge clk);

    // All-zero comparator decisions retain P-side trials.
    pulse_start();
    wait_and_check(expected_p_q8);

    // All-one comparator decisions retain N-side trials with negative sign.
    cmp_out = 1;
    phase = 3'd3;
    pulse_start();
    wait_and_check(-expected_n_q8);

    $display(
      "PASS: lower-SAR uses recursive side-specific Q8 register weights"
    );
    $finish;
  end
endmodule
