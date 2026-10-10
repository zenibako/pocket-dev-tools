// Read-only observability of the pinned os25 CPU. No CPU parameter changes.
assign cp_i_arvalid = cpu_sys.i_arvalid_cpu;
assign cp_i_arready = cpu_sys.i_arready_cpu;
assign cp_i_araddr = cpu_sys.i_araddr_cpu;
assign cp_i_arid = cpu_sys.i_arid_cpu;
assign cp_i_arlen = cpu_sys.i_arlen_cpu;
assign cp_i_rvalid = cpu_sys.i_rvalid_cpu;
assign cp_i_rready = cpu_sys.i_rready_cpu;
assign cp_i_rid = cpu_sys.i_rid_cpu;
assign cp_i_rlast = cpu_sys.i_rlast_cpu;
assign cp_i_rresp = cpu_sys.i_rresp_cpu;
assign cp_d_arvalid = cpu_sys.mem_arvalid_cpu;
assign cp_d_arready = cpu_sys.mem_arready_cpu;
assign cp_d_araddr = cpu_sys.mem_araddr_cpu;
assign cp_d_arid = cpu_sys.mem_arid_cpu;
assign cp_d_arlen = cpu_sys.mem_arlen_cpu;
assign cp_d_rvalid = cpu_sys.mem_rvalid_cpu;
assign cp_d_rready = cpu_sys.mem_rready_cpu;
assign cp_d_rid = cpu_sys.mem_rid_cpu;
assign cp_d_rlast = cpu_sys.mem_rlast_cpu;
assign cp_d_rresp = cpu_sys.mem_rresp_cpu;
assign cp_i_hold = cpu_sys.cpu.FetchL1Plugin_logic_refill_onRsp_holdHarts
                   && cpu_sys.cpu.fetch_logic_ctrls_1_up_valid;
// Shadow the pinned FetchL1Plugin onEvents.waiting register in the observer.
// Node.isMoving includes cancellation when this pipeline node has a cancel port.
assign cp_i_miss = cpu_sys.cpu.fetch_logic_ctrls_3_up_valid
                   && (cpu_sys.cpu.fetch_logic_ctrls_3_up_ready || cpu_sys.cpu.fetch_logic_ctrls_3_up_cancel)
                   && cpu_sys.cpu.FetchL1Plugin_logic_ctrl_allowRefill;
assign cp_i_resume = cpu_sys.cpu.fetch_logic_ctrls_3_up_valid
                     && !cpu_sys.cpu.fetch_logic_ctrls_3_down_TRAP;
assign cp_i_miss_pc = cpu_sys.cpu.fetch_logic_ctrls_3_down_Fetch_WORD_PC;
assign cp_i_pc = cpu_sys.cpu.fetch_logic_ctrls_1_down_Fetch_WORD_PC;
assign cp_d_wait = cpu_sys.cpu.LsuPlugin_logic_onCtrl_hartRegulation_valid;
assign cp_commit = cpu_sys.cpu.WhiteboxerPlugin_logic_commits_ports_0_valid;
assign cp_clock_cmd = cpu_sys.cpu.LsuPlugin_logic_bus_cmd_valid
                      && cpu_sys.cpu.LsuPlugin_logic_bus_cmd_ready
                      && !cpu_sys.cpu.LsuPlugin_logic_bus_cmd_payload_write
                      && cpu_sys.cpu.LsuPlugin_logic_bus_cmd_payload_address == 32'h40000004;
assign cp_clock_pc = cpu_sys.cpu.execute_ctrl4_down_PC_lane0;
// The exact edge on which the MMIO counter value returned to the firmware is
// latched. This avoids a UART/marker delay or any added firmware instructions.
assign cp_clock_latch = periph.state == 3'd4 && periph.req_region == 4'd2
                       && periph.req_addr == 32'h40000004;
assign cp_counter = periph.cycle_counter[31:0];
