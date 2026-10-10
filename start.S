.section .text.start,"ax"
.global _start
_start:
  .option push
  .option norelax
  la gp, __global_pointer$
  .option pop
  li sp, 0x13fffff0
  li t0, 0x6000
  csrs mstatus, t0
  la t0, trap
  csrw mtvec, t0
  la t0, __bss_start
  la t1, __bss_end
1:
  bgeu t0, t1, 2f
  sw zero, 0(t0)
  addi t0, t0, 4
  j 1b
2:
  call main
3:
  j 3b
.balign 4
trap:
  csrr a0, mcause
  csrr a1, mepc
  csrr a2, mtval
  call harness_trap
  j 3b
