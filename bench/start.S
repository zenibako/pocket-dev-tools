.section .text.start,"ax"
.global _rtl_start
_rtl_start:
  li t0, 0x6000
  csrs mstatus, t0
  la t0, frame_trap
  csrw mtvec, t0
  la t0, frame_host
  sw zero, 0(t0)
  # Hand CRAM0 to the CPU before using its uncached virtual-file mailbox.
  li t0, 0x4e000000
  li t1, 1
  sw t1, 0(t0)
  j frame_restore
frame_trap:
  csrr a0, mcause
  csrr a1, mepc
  csrr a2, mtval
  call frame_trap_report
1: j 1b
.section .text.host_boot,"ax"
.global _host_start
_host_start:
  la a0, __frame_heap_start
  li a1, 0x14000000
  sub a1, a1, a0
  li a2, 3
  li a3, 0x32
  li a4, -1
  li a5, 0
  li a7, 222
  ecall
#if FRAME_FB_UNCACHED
  li a0, 0x53a00000
  li a1, 1228800
  li a2, 3
  li a3, 0x32
  li a4, -1
  li a5, 0
  li a7, 222
  ecall
#endif
  li sp, 0x13fff000
  .option push
  .option norelax
  la gp, __global_pointer$
  .option pop
  la tp, frame_tls
  addi tp, tp, 1024
  call frame_host_main
2: j 2b
.global frame_suspend
frame_suspend:
  la t0, frame_context
  sw ra,0(t0)
  sw sp,4(t0)
  sw gp,8(t0)
  sw tp,12(t0)
  sw s0,16(t0)
  sw s1,20(t0)
  sw s2,24(t0)
  sw s3,28(t0)
  sw s4,32(t0)
  sw s5,36(t0)
  sw s6,40(t0)
  sw s7,44(t0)
  sw s8,48(t0)
  sw s9,52(t0)
  sw s10,56(t0)
  sw s11,60(t0)
  fsw fs0,64(t0)
  fsw fs1,68(t0)
  fsw fs2,72(t0)
  fsw fs3,76(t0)
  fsw fs4,80(t0)
  fsw fs5,84(t0)
  fsw fs6,88(t0)
  fsw fs7,92(t0)
  fsw fs8,96(t0)
  fsw fs9,100(t0)
  fsw fs10,104(t0)
  fsw fs11,108(t0)
  frcsr t1
  sw t1,112(t0)
  call frame_checkpoint
.global frame_restore
frame_restore:
  la t0, frame_context
  lw ra,0(t0)
  lw sp,4(t0)
  lw gp,8(t0)
  lw tp,12(t0)
  lw s0,16(t0)
  lw s1,20(t0)
  lw s2,24(t0)
  lw s3,28(t0)
  lw s4,32(t0)
  lw s5,36(t0)
  lw s6,40(t0)
  lw s7,44(t0)
  lw s8,48(t0)
  lw s9,52(t0)
  lw s10,56(t0)
  lw s11,60(t0)
  flw fs0,64(t0)
  flw fs1,68(t0)
  flw fs2,72(t0)
  flw fs3,76(t0)
  flw fs4,80(t0)
  flw fs5,84(t0)
  flw fs6,88(t0)
  flw fs7,92(t0)
  flw fs8,96(t0)
  flw fs9,100(t0)
  flw fs10,104(t0)
  flw fs11,108(t0)
  lw t1,112(t0)
  fscsr t1
  li a0, 1
  ret
