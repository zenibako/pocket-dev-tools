#ifndef FRAME_H
#define FRAME_H
#include <stdint.h>
#include <stddef.h>
#include "runner.h"
#define FRAME_META __attribute__((section(".frame_meta")))
extern int frame_host;
extern uintptr_t frame_heap_cursor;
extern uint64_t frame_clock;
extern unsigned frame_pcm_hash,frame_pcm_pairs,frame_ops,frame_events,frame_trace,frame_audio_queued;
extern unsigned frame_context[64];
extern unsigned frame_expected[3][8];
void frame_begin(Runner *);
void frame_end(Runner *);
void frame_tick(VMContext *,unsigned,unsigned);
void frame_event(int);
void frame_checkpoint(void);
int frame_suspend(void);
void frame_restore(void);
void frame_output(const char *);
void frame_fail(const char *) __attribute__((noreturn));
long frame_syscall(long,long,long,long,long,long,long);
int frame_rpc(unsigned,const char *,unsigned,void *,unsigned);
unsigned frame_hash(const void *,size_t,unsigned);
#endif
