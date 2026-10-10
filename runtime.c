#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

void harness_put(const char *s) {
#ifdef __riscv
    while(*s) {while(!(*(volatile unsigned *)0x4f000000u & 2)) {} *(volatile unsigned *)0x4f000004u=(unsigned char)*s++;}
#else
    fputs(s,stdout);
#endif
}
void harness_fail(const char *reason) {
    harness_put("VMHARNESS FAIL ");harness_put(reason);harness_put("\n");
#ifdef __riscv
    for(;;) {}
#else
    exit(2);
#endif
}
unsigned harness_cycles(void) {
#ifdef __riscv
    /* Production os25 omits cycle CSRs; use its real SYSREG cycle counter. */
    __asm__ volatile("" ::: "memory");
    return *(volatile unsigned *)0x40000004u;
#else
    return 0;
#endif
}

#ifdef __riscv
/* Harness-only bounded first-fit allocator, not the production musl allocator.
 * Keep allocation results out of performance claims about production malloc. */
typedef struct Block {size_t size;struct Block *next;unsigned free;unsigned pad;} Block;
static Block *first;
static uintptr_t cursor=0x10400000u;
void *malloc(size_t n) {
    if(!n)n=1;
    if(n>0x03300000u-16)return NULL;
    n=(n+15)&~(size_t)15;
    for(Block *b=first;b;b=b->next) if(b->free && b->size>=n) {b->free=0;return b+1;}
    if(cursor+sizeof(Block)+n>0x13700000u)return NULL;
    Block *b=(Block *)cursor;cursor+=sizeof(Block)+n;
    b->size=n;b->next=first;b->free=0;first=b;return b+1;
}
void free(void *p) {if(p){Block *b=(Block *)p-1;if(b->free)harness_fail("double free");b->free=1;}}
void *calloc(size_t n,size_t s) {if(s && n>SIZE_MAX/s)return NULL;size_t z=n*s;void *p=malloc(z);if(p)memset(p,0,z);return p;}
void *realloc(void *p,size_t n) {if(!p)return malloc(n);if(!n){free(p);return NULL;}Block *b=(Block *)p-1;if(b->size>=n)return p;void *q=malloc(n);if(!q)return NULL;memcpy(q,p,b->size);free(p);return q;}
void abort(void) {harness_fail("abort");__builtin_unreachable();}
void __assert_fail(const char *expr,const char *file,int line,const char *fn) {(void)file;(void)line;(void)fn;harness_fail(expr);__builtin_unreachable();}
/* Catch unexpected libc system calls rather than implementing fake I/O. */
void harness_trap(unsigned cause,unsigned pc,unsigned value) {
    char b[96];snprintf(b,sizeof(b),"trap cause=%x pc=%x value=%x",cause,pc,value);harness_fail(b);
}
#endif
