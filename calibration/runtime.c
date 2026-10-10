#include "calibration.h"
#include "build_id.h"
#include "of_caps.h"
#include "save_log.h"
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include <stdlib.h>

int calibration_mode=0;
volatile unsigned calibration_expected_bias __attribute__((section(".data.cal_bias")))=0;
typedef struct { unsigned job,round,iterations,operations,cycles,result,expected; } CalResult;
static CalResult samples[72];
static unsigned measured,begin_cycles;

static void console(const char *s){
 if(calibration_mode==1){
  while(*s){while(!(*(volatile unsigned*)0x4f000000u&2)){}*(volatile unsigned*)0x4f000004u=(unsigned char)*s++;}
 }else fputs(s,stdout);
}
static void emit(const char *s){cal_log_keep(s);console(s);}
static void output(const char *fmt,...){
 char line[320];va_list ap;va_start(ap,fmt);vsnprintf(line,sizeof(line),fmt,ap);va_end(ap);emit(line);
}
void calibration_fail(const char *reason){
 output("FRAMEHARNESS FAIL calibration %s\n",reason);
 if(calibration_mode!=1){
  console(cal_log_dump()?"CALSAVE saved calibration_log.sav (failed run)\n":"CALSAVE FAIL calibration_log.sav\n");
  exit(2);
 }for(;;){}
}
void calibration_trap(unsigned cause,unsigned pc,unsigned value){
 output("FRAMEHARNESS FAIL calibration trap cause=%x pc=%x value=%x\n",cause,pc,value);for(;;){}
}
static inline unsigned cycles(void){
 __asm__ volatile("" ::: "memory");
 return calibration_mode==2?0:*(volatile unsigned*)0x40000004u;
}
/* Exact MMIO-latch bounds for the passive observer; no logs or checks here. */
__attribute__((noinline)) void calibration_begin(void){begin_cycles=cycles();}
__attribute__((noinline)) void calibration_end(void){samples[measured].cycles=cycles()-begin_cycles;measured++;}
static void measure(unsigned job,unsigned round,CalJob *j){
 CalResult *r=&samples[measured];r->job=job;r->round=round;r->iterations=j->iterations;r->operations=j->operations;r->expected=j->expected;
 calibration_begin();uint32_t value=j->run(j->iterations,j->arg);calibration_end();r->result=value;
}
int calibration_run(void){
 __asm__ volatile("fscsr x0" ::: "memory");
 calibration_setup();
 for(unsigned job=0;job<calibration_job_count;job++){
  CalJob *j=&calibration_jobs[job];j->run(j->iterations,j->arg); // full untimed warm-up
  for(unsigned round=0;round<3;round++)measure(job,round,j);
 }
 static const unsigned stages[]={6,5,4,3,2,1,0,7};
 for(unsigned round=0;round<3;round++){
  calibration_sprite_warm();
  for(unsigned i=0;i<8;i++){
   unsigned stage=stages[i];calibration_sprite_stage(stage);
   CalJob j={"sprite",calibration_sprite_draw,(void*)(uintptr_t)stage,2000,2000,1};
   measure(calibration_job_count+stage,round,&j);
  }
 }
 if(measured!=72)calibration_fail("sample count");
 /* All independent validation, formatting and output is after all 72 intervals. */
 unsigned pixel_hash=calibration_sprite_check();
 for(unsigned i=0;i<measured;i++)if(samples[i].result!=samples[i].expected+calibration_expected_bias)
  calibration_fail("independent result oracle");
 const struct of_capabilities *caps=calibration_mode==0?of_get_caps():NULL;
 output("CALINFO %s %s cpu_hz=%u os_version=%08x core_variant=%u caps_version=%u\n",CAL_BUILD_ID,
        calibration_mode==0?"hardware":calibration_mode==1?"rtl":"reference",
        caps?caps->cpu_freq_hz:100000000u,caps?caps->os_version:0,caps?caps->core_variant:0,caps?caps->version:0);
 output("CALPIXELS %08x\n",pixel_hash);
 output("CALPOLICY mmio=40000004 cached_fb=1 validation=after_all warmup=full_micro_and_one_sprite interrupts=platform_default\n");
 for(unsigned i=0;i<measured;i++){
  CalResult *r=&samples[i];
  const char *name=r->job<calibration_job_count?calibration_jobs[r->job].name:"sprite";
  output("CALRESULT %u %u %u %s %u %u %u %08x %08x\n",i,r->job,r->round,name,r->iterations,r->operations,r->cycles,r->result,r->expected);
 }
 /* Include the success marker in the saved text, but announce success on the
    console only after the save completes. No file operation is timed. */
 const char *pass="CALIBRATION PASS HAL init\n";
 cal_log_keep(pass);
 if(calibration_mode!=1){
  if(!cal_log_dump())calibration_fail("save log write");
  console("CALSAVE saved calibration_log.sav; exit via Analogue menu\n");
 }
 console(pass);return 0;
}
int main(int argc,char **argv){
 if(argc==2 && !strcmp(argv[1],"--reference"))calibration_mode=2;
 else if(argc==2 && !strcmp(argv[1],"--negative-reference")){calibration_mode=2;calibration_expected_bias=1;}
 else if(argc!=1){emit("Use no arguments on Pocket; --reference is QEMU only.\n");return 2;}
 if(calibration_mode==0){
  const struct of_capabilities *c=of_get_caps();
  if(!c || c->magic!=OF_CAPS_MAGIC || c->platform_id!=OF_PLATFORM_POCKET || c->cpu_freq_hz!=100000000u || c->version<2 ||
     c->sdram_base!=0x10000000u || c->sdram_uncached_base!=0x50000000u)
   calibration_fail("requires compatible 100 MHz Pocket SDRAM/uncached capability descriptor");
 }
 return calibration_run();
}
/* Unexpected renderer slow paths fail in both environments, rather than invoke
   a simulated kernel or silently replace a timed file/allocator service. */
void logError(const char *fmt,...){(void)fmt;calibration_fail("renderer error/slow path");}
void logWarn(const char *fmt,...){(void)fmt;calibration_fail("renderer warning/slow path");}
void logInfo(const char *fmt,...){(void)fmt;calibration_fail("renderer file/slow path");}
void logDebug(const char *fmt,...){(void)fmt;calibration_fail("renderer debug/slow path");}
