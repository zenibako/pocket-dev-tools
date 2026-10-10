.section .text.start,"ax"
.global _rtl_start
_rtl_start:
  .option push
  .option norelax
  la gp,__global_pointer$
  .option pop
  li sp,0x13fffff0
  la tp,calibration_tls
  addi tp,tp,1024
  li t0,0x6000
  csrs mstatus,t0
  la t0,calibration_trap_entry
  csrw mtvec,t0
  la t0,calibration_mode
  li t1,1
  sw t1,0(t0)
  call calibration_run
1: j 1b
calibration_trap_entry:
  csrr a0,mcause
  csrr a1,mepc
  csrr a2,mtval
  call calibration_trap
  j 1b
.section .bss.calibration_tls,"aw",@nobits
.balign 16
.global calibration_tls
calibration_tls: .space 2048
