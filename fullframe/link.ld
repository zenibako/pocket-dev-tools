/* App SDRAM/BRAM placement follows the copied SDK app.ld. */
ENTRY(_host_start)
SECTIONS {
 . = 0x10400000;
 .text : { KEEP(*(.text.start)) *(.text*) *(.rodata*) *(.srodata*) }
 .data : { *(.data*) *(.sdata*) }
 . = ALIGN(16); __global_pointer$ = . + 0x800;
 __bss_start = .;
 .bss : { *(.bss*) *(.sbss*) *(COMMON) }
 __bss_end = .;
 .frame_meta : { *(.frame_meta) }
 . = ALIGN(4096); __frame_heap_start = .;
 ASSERT(__frame_heap_start < 0x10800000, "full-frame program consumes over 4 MiB")
 .app_fasttext 0x4000 : { *(.app_fasttext*) }
 ASSERT(SIZEOF(.app_fasttext)<=0x3800,"BRAM overflow")
 /DISCARD/ : { *(.comment) *(.riscv.attributes) *(.eh_frame*) }
}
