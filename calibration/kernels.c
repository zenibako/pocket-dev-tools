#include "calibration.h"
#include "expected.h"
#include <stddef.h>
#include <string.h>
#include <sys/mman.h>

#define KERNEL __attribute__((noinline,aligned(64)))
#define EIGHT(x) x x x x x x x x
#define BODY(code,outputs,inputs) __asm__ volatile("1:\n" code "addi %0,%0,-1\nbnez %0,1b\n" : outputs : inputs : "memory")

static uint32_t small[64] __attribute__((aligned(4096)));
static uint32_t large[8192][16] __attribute__((aligned(4096)));
static uint32_t stream[65536] __attribute__((aligned(4096)));
static uint32_t uncached[1024] __attribute__((aligned(4096)));

KERNEL uint32_t cal_loop(uint32_t n,void *arg){
 (void)arg; __asm__ volatile("1: addi %0,%0,-1; bnez %0,1b" : "+r"(n)); return 0;
}
KERNEL uint32_t cal_integer_dep(uint32_t n,void *arg){
 (void)arg;uint32_t x=1;
 __asm__ volatile("1:\n" EIGHT("addi %1,%1,3\n") "addi %0,%0,-1\nbnez %0,1b" : "+r"(n),"+r"(x));return x;
}
KERNEL uint32_t cal_integer_independent(uint32_t n,void *arg){
 (void)arg;uint32_t a=0,b=1,c=2,d=3,e=4,f=5,g=6,h=7;
 __asm__ volatile("1: addi %1,%1,3; addi %2,%2,3; addi %3,%3,3; addi %4,%4,3; addi %5,%5,3; addi %6,%6,3; addi %7,%7,3; addi %8,%8,3; addi %0,%0,-1; bnez %0,1b"
 : "+r"(n),"+r"(a),"+r"(b),"+r"(c),"+r"(d),"+r"(e),"+r"(f),"+r"(g),"+r"(h));return a+b+c+d+e+f+g+h;
}
KERNEL uint32_t cal_multiply(uint32_t n,void *arg){
 (void)arg;uint32_t x=1,k=3;
 __asm__ volatile("1:\n" EIGHT("mul %1,%1,%2\n") "addi %0,%0,-1\nbnez %0,1b" : "+r"(n),"+r"(x) : "r"(k));return x;
}
KERNEL uint32_t cal_divide(uint32_t n,void *arg){
 (void)arg;uint32_t x=1000000,k=7;
 __asm__ volatile("1:\n" EIGHT("divu %1,%1,%2\naddi %1,%1,101\n") "addi %0,%0,-1\nbnez %0,1b" : "+r"(n),"+r"(x) : "r"(k));return x;
}
KERNEL uint32_t cal_load_chain(uint32_t n,void *arg){
 uintptr_t x=(uintptr_t)arg,base=x;
 __asm__ volatile("1:\n" EIGHT("lw %1,0(%1)\n") "addi %0,%0,-1\nbnez %0,1b" : "+r"(n),"+r"(x) : : "memory");return x-base;
}
KERNEL uint32_t cal_stream(uint32_t n,void *arg){
 uint32_t sum=0,tmp;uintptr_t p=(uintptr_t)arg;
 __asm__ volatile("1:\n" EIGHT("lw %3,0(%1)\nadd %2,%2,%3\naddi %1,%1,4\n") "addi %0,%0,-1\nbnez %0,1b"
 : "+r"(n),"+r"(p),"+r"(sum),"=&r"(tmp) : : "memory");return sum;
}
KERNEL uint32_t cal_fp_add(uint32_t n,void *arg){
 (void)arg;uint32_t bits=0x3f800000,result;
 __asm__ volatile("fmv.w.x ft0,%2\nfmv.w.x ft1,%2\n1:\n" EIGHT("fadd.s ft0,ft0,ft1\n") "addi %0,%0,-1\nbnez %0,1b\nfmv.x.w %1,ft0"
 : "+r"(n),"=r"(result) : "r"(bits) : "ft0","ft1");return result;
}
KERNEL uint32_t cal_fp_multiply(uint32_t n,void *arg){
 (void)arg;uint32_t bits=0x3f800000,result;
 __asm__ volatile("fmv.w.x ft0,%2\nfmv.w.x ft1,%2\n1:\n" EIGHT("fmul.s ft0,ft0,ft1\n") "addi %0,%0,-1\nbnez %0,1b\nfmv.x.w %1,ft0"
 : "+r"(n),"=r"(result) : "r"(bits) : "ft0","ft1");return result;
}
KERNEL uint32_t cal_fp_divide(uint32_t n,void *arg){
 (void)arg;uint32_t a=0x40400000,b=0x40000000,result;
 __asm__ volatile("fmv.w.x ft1,%2\nfmv.w.x ft2,%3\n1:\n" EIGHT("fdiv.s ft0,ft1,ft2\n") "addi %0,%0,-1\nbnez %0,1b\nfmv.x.w %1,ft0"
 : "+r"(n),"=r"(result) : "r"(a),"r"(b) : "ft0","ft1","ft2");return result;
}
KERNEL uint32_t cal_convert(uint32_t n,void *arg){
 (void)arg;uint32_t x=1;
 __asm__ volatile("1:\n" EIGHT("fcvt.s.w ft0,%1,rne\nfcvt.w.s %1,ft0,rtz\naddi %1,%1,1\n") "addi %0,%0,-1\nbnez %0,1b"
 : "+r"(n),"+r"(x) : : "ft0");return x;
}
KERNEL uint32_t cal_int_to_fp(uint32_t n,void *arg){
 (void)arg;uint32_t x=1,result;
 __asm__ volatile("1:\n" EIGHT("addi %1,%1,1\nfcvt.s.w ft0,%1,rne\n") "addi %0,%0,-1\nbnez %0,1b\nfmv.x.w %2,ft0"
 : "+r"(n),"+r"(x),"=r"(result) : : "ft0");return result;
}
KERNEL uint32_t cal_fp_to_int(uint32_t n,void *arg){
 (void)arg;uint32_t a=0x3fc00000,result;
 __asm__ volatile("fmv.w.x ft0,%2\n1:\n" EIGHT("fcvt.w.s %1,ft0,rtz\n") "addi %0,%0,-1\nbnez %0,1b"
 : "+r"(n),"=&r"(result) : "r"(a) : "ft0");return result;
}
extern uint32_t cal_icache_stream(uint32_t,void*);
extern void calibration_sprite_setup(void);

#define JOB(name,fn,arg,n,ops,expected) {name,fn,arg,n,ops,expected}
CalJob calibration_jobs[]={
 JOB("loop",cal_loop,0,2047,2047,0),
 JOB("integer-dependent",cal_integer_dep,0,2047,2047*8,EXPECTED_INTEGER_DEP),
 JOB("integer-independent",cal_integer_independent,0,2047,2047*8,EXPECTED_INTEGER_INDEPENDENT),
 JOB("multiply-dependent",cal_multiply,0,2047,2047*8,EXPECTED_MULTIPLY),
 JOB("divide-dependent",cal_divide,0,2047,2047*8,EXPECTED_DIVIDE),
 JOB("cached-load-chain",cal_load_chain,small,2047,2047*8,56*4),
 JOB("capacity-load-chain",cal_load_chain,large,2047,2047*8,8056*64),
 JOB("uncached-load-chain",cal_load_chain,0,2047,2047*8,56*4),
 JOB("cached-stream",cal_stream,stream,8191,8191*8,EXPECTED_STREAM),
 JOB("fp-add-dependent",cal_fp_add,0,2047,2047*8,EXPECTED_FP_ADD),
 JOB("fp-multiply-dependent",cal_fp_multiply,0,2047,2047*8,0x3f800000),
 JOB("fp-divide",cal_fp_divide,0,2047,2047*8,0x3fc00000),
 JOB("conversion-roundtrip",cal_convert,0,2047,2047*8,EXPECTED_CONVERT),
 JOB("int-to-fp",cal_int_to_fp,0,2047,2047*8,EXPECTED_FP_ADD),
 JOB("fp-to-int",cal_fp_to_int,0,2047,2047*8,1),
 JOB("icache-64k-stream",cal_icache_stream,0,8,8*1024,8*1024),
};
unsigned calibration_job_count=sizeof(calibration_jobs)/sizeof(calibration_jobs[0]);
void calibration_setup(void){
 for(unsigned i=0;i<64;i++)small[i]=(uint32_t)(uintptr_t)&small[(i+1)&63];
 for(unsigned i=0;i<8192;i++)large[i][0]=(uint32_t)(uintptr_t)&large[(i+17)&8191][0];
 for(unsigned i=0;i<65536;i++)stream[i]=i*2654435761u;
 uintptr_t alias=(uintptr_t)uncached|0x40000000u;
 if(calibration_mode==2){
  if(mmap((void*)alias,4096,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED,-1,0)!=(void*)alias)
   calibration_fail("reference uncached mapping");
 }else{
  /* Write back/invalidate every possible dirty cached alias before direct stores.
     CBO.FLUSH, encoded explicitly like the OS: fixed os25 Zicbom capability. */
  for(unsigned i=0;i<4096;i+=64){uintptr_t p=(uintptr_t)uncached+i;__asm__ volatile(".insn i 0x0f,2,x0,%0,2" : : "r"(p) : "memory");}
 }
 volatile uint32_t *u=(volatile uint32_t*)alias;
 for(unsigned i=0;i<64;i++)u[i]=(uint32_t)(alias+((i+1)&63)*4);
 __asm__ volatile("fence rw,rw" ::: "memory");
 calibration_jobs[7].arg=(void*)alias;
 calibration_sprite_setup();
}
