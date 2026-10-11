#ifndef PICO_FRAME_H
#define PICO_FRAME_H
#include <stdint.h>
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
#ifndef PICO_MEASURED_FRAMES
#define PICO_MEASURED_FRAMES 3
#endif
#define FRAME_META __attribute__((section(".frame_meta")))
extern int frame_host;
extern uintptr_t frame_heap_cursor;
extern uint64_t frame_clock;
extern unsigned frame_context[64], frame_expected[PICO_MEASURED_FRAMES][8];
int frame_suspend(void);
void frame_output(const char *);
void frame_fail(const char *) __attribute__((noreturn));
long frame_syscall(long,long,long,long,long,long,long);
void frame_checkpoint(void);
void frame_host_main(void);
#ifdef __cplusplus
}
#endif
#endif
