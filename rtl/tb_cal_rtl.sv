// tb_cal_rtl.sv — self-checking calibration arithmetic/FSM test
`timescale 1ns / 1ps

module tb_cal_rtl;
  parameter int CLK_PERIOD_NS = 10;
  parameter int N_TARGETS = 7;
  parameter int N_PAIRS = 4;
  parameter int WEIGHT_WIDTH = 20;
  parameter int SUBSUM_WIDTH = 24;

  localparam int TARGET_NOM_Q0 [0:6] = '{
    67, 134, 268, 536, 536, 1072, 2144
  };

  logic clk = 0;
  logic rst_n;
  logic start;
  logic subconv_done;
  logic signed [SUBSUM_WIDTH-1:0] subconv_signed_sum;
  logic start_subconv;
  logic [2:0] target_idx;
  logic [2:0] phase;
  logic [$clog2(N_PAIRS)-1:0] pair_cnt;
  logic acc_valid;
  logic wreg_we;
  logic [2:0] wreg_addr;
  logic [WEIGHT_WIDTH-1:0] wreg_wp, wreg_wn;
  logic cal_done, cal_failed;

  logic pending_response;
  logic [2:0] pending_phase;
  logic [2:0] pending_target;
  logic [4:1] phase_seen;
  integer write_count;
  integer timeout_cycles;

  always #(CLK_PERIOD_NS/2) clk = ~clk;

  cal_fsm #(
    .N_TARGETS(N_TARGETS),
    .N_PAIRS(N_PAIRS),
    .WEIGHT_WIDTH(WEIGHT_WIDTH),
    .SUBSUM_WIDTH(SUBSUM_WIDTH)
  ) u_dut (
    .clk(clk),
    .rst_n(rst_n),
    .start(start),
    .subconv_done(subconv_done),
    .subconv_signed_sum(subconv_signed_sum),
    .start_subconv(start_subconv),
    .target_idx(target_idx),
    .phase(phase),
    .pair_cnt(pair_cnt),
    .acc_valid(acc_valid),
    .wreg_we(wreg_we),
    .wreg_addr(wreg_addr),
    .wreg_wp(wreg_wp),
    .wreg_wn(wreg_wn),
    .cal_done(cal_done),
    .cal_failed(cal_failed)
  );

  // One-cycle-latency lower-SAR response.  Values implement:
  // P0=+W_Q8, P1=-W_Q8, N0=-W_Q8, N1=+W_Q8, hence both
  // half-differences equal W_Q8.
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      subconv_done <= 1'b0;
      subconv_signed_sum <= '0;
      pending_response <= 1'b0;
      pending_phase <= '0;
      pending_target <= '0;
      phase_seen <= '0;
    end else begin
      subconv_done <= 1'b0;
      if (start_subconv) begin
        pending_response <= 1'b1;
        pending_phase <= phase;
        pending_target <= target_idx;
        if (phase >= 1 && phase <= 4)
          phase_seen[phase] <= 1'b1;
      end else if (pending_response) begin
        pending_response <= 1'b0;
        subconv_done <= 1'b1;
        case (pending_phase)
          3'd1, 3'd4:
            subconv_signed_sum <= (
              TARGET_NOM_Q0[pending_target] <<< 8
            );
          3'd2, 3'd3:
            subconv_signed_sum <= -(
              TARGET_NOM_Q0[pending_target] <<< 8
            );
          default:
            $fatal(1, "illegal phase %0d", pending_phase);
        endcase
      end
    end
  end

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      write_count <= 0;
    end else if (wreg_we) begin
      if (wreg_addr !== write_count[2:0])
        $fatal(1, "write order mismatch: addr=%0d expected=%0d",
               wreg_addr, write_count);
      if (wreg_wp !== (TARGET_NOM_Q0[wreg_addr] << 8))
        $fatal(1, "W_P mismatch target=%0d got=%0d expected=%0d",
               wreg_addr, wreg_wp, TARGET_NOM_Q0[wreg_addr] << 8);
      if (wreg_wn !== (TARGET_NOM_Q0[wreg_addr] << 8))
        $fatal(1, "W_N mismatch target=%0d got=%0d expected=%0d",
               wreg_addr, wreg_wn, TARGET_NOM_Q0[wreg_addr] << 8);
      write_count <= write_count + 1;
    end
  end

  initial begin
    rst_n = 0;
    start = 0;
    timeout_cycles = 0;
    repeat (5) @(posedge clk);
    rst_n = 1;
    repeat (2) @(posedge clk);
    start = 1;
    @(posedge clk);
    start = 0;

    while (!cal_done && timeout_cycles < 5000) begin
      @(posedge clk);
      timeout_cycles = timeout_cycles + 1;
    end
    if (!cal_done)
      $fatal(1, "timeout waiting for cal_done");
    if (cal_failed)
      $fatal(1, "calibration unexpectedly failed");
    if (write_count != N_TARGETS)
      $fatal(1, "only %0d/%0d targets committed", write_count, N_TARGETS);
    if (phase_seen !== 4'b1111)
      $fatal(1, "not all P0/P1/N0/N1 phases observed: %b", phase_seen);

    $display("PASS: 7/7 targets, P0/P1/N0/N1, Q8 width and averaging");
    $finish;
  end
endmodule
