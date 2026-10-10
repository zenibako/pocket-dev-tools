ENTRY(_start)
SECTIONS {
  . = 0x10320000;
  .text : { *(.text.start) *(.text*) }
  .rodata : { *(.rodata*) }
  .data : { *(.data*) *(.sdata*) }
  . = ALIGN(16);
  __global_pointer$ = . + 0x800;
  __bss_start = .;
  .bss : { *(.bss*) *(.sbss*) *(COMMON) }
  . = ALIGN(16);
  __bss_end = .;
  ASSERT(__bss_end < 0x10400000, "image overlaps harness heap")
  .app_fasttext 0x4000 : { *(.app_fasttext*) }
  ASSERT(SIZEOF(.app_fasttext) <= 0x3800, "application BRAM overflow")
}
