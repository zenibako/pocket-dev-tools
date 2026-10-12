#include "frame.h"
#include "instance.h"
#include "gml_array.h"
#include "gml_method.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef FRAME_SCENE_ROOM
#include "sw_renderer_private.h"
#include "sw_call_notes.h"
#include "openfpga/platform/ut_bench.h"
#ifndef FRAME_SCENE_EXPECT_ROOM
#define FRAME_SCENE_EXPECT_ROOM FRAME_SCENE_ROOM
#endif
#endif
#ifndef FRAME_TARGET
#define FRAME_TARGET 2399
#endif
#define FRAME_COUNT 3
unsigned frame_ops FRAME_META,frame_events FRAME_META,frame_trace FRAME_META;
static unsigned measured FRAME_META,begin_cycles FRAME_META;
extern unsigned frame_clock_reads,frame_audio_consumed,frame_audio_underruns;
extern void frame_platform_begin(void);
extern void frame_platform_end(void);
static void *visited[8192] FRAME_META;
static unsigned nvisited FRAME_META;
unsigned frame_hash(const void*p,size_t n,unsigned hash){const unsigned char*s=p;while(n--)hash=(hash^*s++)*16777619u;return hash;}
static unsigned word(unsigned h,unsigned x){return frame_hash(&x,4,h);}
static bool seen(void *p){for(unsigned i=0;i<nvisited;i++)if(visited[i]==p)return true;if(nvisited==8192)frame_fail("state graph size");visited[nvisited++]=p;return false;}
static unsigned instance_hash(Instance*,unsigned,unsigned);
static unsigned value_hash(RValue v,unsigned h,unsigned depth){
 if(depth>128)frame_fail("state graph depth");h=word(h,v.type);h=word(h,v.gmlStackType);h=word(h,v.assetRefType);
 switch(v.type){
 case RVALUE_UNDEFINED:return h;
 case RVALUE_INT32:case RVALUE_BOOL:case RVALUE_REAL:case RVALUE_ASSETREF:return word(h,(unsigned)v.int32);
 case RVALUE_STRING:if(!v.string)return word(h,0);return frame_hash(v.string,strlen(v.string)+1,h);
 case RVALUE_ARRAY:{GMLArray*a=v.array;h=word(h,(unsigned)(uintptr_t)a);if(!a || seen(a))return h;
  h=word(h,a->type);h=word(h,a->refCount);
  if(a->type==GML_LEGACY_ARRAY){h=word(h,a->legacy.rowCount);for(int row=0;row<a->legacy.rowCount;row++){GMLArrayRow*r=&a->legacy.rows[row];h=word(h,r->length);for(int i=0;i<r->length;i++)h=value_hash(r->data[i],h,depth+1);}}
  else {h=word(h,a->modern.length);for(int i=0;i<a->modern.length;i++)h=value_hash(a->modern.data[i],h,depth+1);}return h;}
#if IS_WAD17_OR_HIGHER_ENABLED
 case RVALUE_METHOD:{GMLMethod*m=v.method;h=word(h,(unsigned)(uintptr_t)m);if(!m || seen(m))return h;h=word(h,m->codeIndex);h=word(h,m->boundInstanceId);h=word(h,(unsigned)(uintptr_t)m->builtin);if(m->unresolvedName)h=frame_hash(m->unresolvedName,strlen(m->unresolvedName)+1,h);return h;}
#endif
 case RVALUE_STRUCT:return instance_hash(v.structInst,h,depth+1);
 default:frame_fail("state RValue type");return 0;
 }
}
static unsigned instance_hash(Instance *inst,unsigned h,unsigned depth){
 h=word(h,(unsigned)(uintptr_t)inst);if(!inst || seen(inst))return h;
 /* All fixed instance properties, including alarms/motion/collision metadata. */
 h=frame_hash(inst,sizeof(*inst),h);
 for(unsigned i=0;i<inst->selfVars.capacity;i++){IntRValueEntry*e=&inst->selfVars.entries[i];h=word(h,e->key);if(e->key!=-1)h=value_hash(e->value,h,depth+1);}return h;
}
static unsigned state_hash(Runner*r){
 nvisited=0;unsigned h=word(2166136261u,r->frameCount);h=word(h,r->currentRoomIndex);h=word(h,r->pendingRoom);
 h=instance_hash(r->vmContext->globalScopeInstance,h,0);
 h=word(h,arrlen(r->instances));for(int i=0;i<arrlen(r->instances);i++)h=instance_hash(r->instances[i],h,0);
 h=word(h,arrlen(r->structInstances));for(int i=0;i<arrlen(r->structInstances);i++)h=instance_hash(r->structInstances[i],h,0);
 VMContext*c=r->vmContext;if(c->stack.top || c->localVars || c->callStack || c->callDepth || c->envStack)frame_fail("frame VM cleanup");
 if(c->codeLocalsSlotMaps)for(unsigned i=0;i<c->dataWin->code.count;i++){IntIntHashMap*m=&c->codeLocalsSlotMaps[i];h=word(h,m->capacity);h=word(h,m->count);for(unsigned j=0;j<m->capacity;j++){h=word(h,m->entries[j].key);if(m->entries[j].key!=-1)h=word(h,m->entries[j].value);}}
 return h;
}
void frame_tick(VMContext*c,unsigned addr,unsigned instr){frame_ops++;frame_trace=word(frame_trace,c->currentCodeIndex);frame_trace=word(frame_trace,addr);frame_trace=word(frame_trace,instr);}
void frame_event(int index){frame_events++;frame_trace=word(frame_trace,(unsigned)index);}
static unsigned cycles(void){if(frame_host)return 0;return *(volatile unsigned*)0x40000004u;}
void frame_begin(Runner*r){
 if(r->frameCount==FRAME_TARGET && !measured){frame_suspend();}
 frame_clock+=16666667ull;
 frame_clock_reads=frame_audio_consumed=frame_audio_underruns=0;
 frame_platform_begin();
 frame_ops=frame_events=frame_pcm_pairs=0;frame_trace=frame_pcm_hash=2166136261u;
 if(r->frameCount>=FRAME_TARGET)begin_cycles=cycles();
}
extern unsigned frame_pixels(void);
extern void frame_ppm(unsigned);
#ifdef FRAME_SCENE_ROOM
static void frame_scene_check(Runner *r) {
 unsigned spades=0,visible_spades=0,controllers=0;
 GMLCamera *camera=Runner_getCameraForView(r,0);
 for(ptrdiff_t i=0;i<arrlen(r->instances);i++) {
  Instance *inst=r->instances[i];
  if(!inst->active || inst->destroyed || inst->objectIndex<0)continue;
  const char *name=r->dataWin->objt.objects[inst->objectIndex].name;
  if(name && (!strcmp(name,"obj_overworld_spade") || !strcmp(name,"obj_overworld_spade_homing"))) {
   spades++;
   if(inst->visible && camera && inst->x>=camera->viewX && inst->x<camera->viewX+camera->viewWidth &&
      inst->y>=camera->viewY && inst->y<camera->viewY+camera->viewHeight)visible_spades++;
  }
  if(name && !strcmp(name,"obj_battlecontroller"))controllers++;
 }
 SWRenderer *swr=(SWRenderer*)r->renderer;
 if(r->currentRoomIndex!=FRAME_SCENE_EXPECT_ROOM)frame_fail("scene room mismatch");
 if(FRAME_SCENE_SPADES && !spades)frame_fail("scene has no active spades");
 if(FRAME_SCENE_SPADES && !visible_spades)frame_fail("scene has no visible spades");
 if(controllers || swr->contrastEnabled)frame_fail("overworld scene unexpectedly enables battle sampling");
 if(swrCallNotes)frame_fail("scene unexpectedly enables benchmark draw diagnostics");
 if(swrDrawTimed || r->vmContext->profiler)frame_fail("scene unexpectedly enables draw or script profiling");
 if(utPlatformSpeedMode()!=(FRAME_SPEED!=0))frame_fail("scene mode mismatch");
 char line[160];snprintf(line,sizeof(line),"FRAMESCENE %u room=%d spades=%u visible=%u controllers=%u contrast=%u speed=%u\n",
  r->frameCount,r->currentRoomIndex,spades,visible_spades,controllers,swr->contrastEnabled,utPlatformSpeedMode());frame_output(line);
}
#endif
void frame_end(Runner*r){
 unsigned elapsed=cycles()-begin_cycles;
 frame_platform_end();
 if(r->frameCount<=FRAME_TARGET)return;
#ifdef FRAME_SCENE_ROOM
 // Validation and reporting occur after elapsed cycles have been sampled.
 frame_scene_check(r);
#endif
 unsigned row[8]={r->frameCount,state_hash(r),frame_pixels(),frame_pcm_hash,frame_pcm_pairs,frame_ops,frame_events,frame_trace};
 if(measured>=FRAME_COUNT)frame_fail("frame count overflow");
 if(!frame_host)for(unsigned i=0;i<8;i++)if(!(FRAME_TIMING && i==3) && !(FRAME_AUDIO_REALTIME && (i==3 || i==4)) && row[i]!=frame_expected[measured][i]){char s[120];snprintf(s,sizeof(s),"frame %u oracle field %u expected=%08x actual=%08x",r->frameCount,i,frame_expected[measured][i],row[i]);frame_fail(s);}
 char line[180];snprintf(line,sizeof(line),"FRAMERESULT %u %u %08x %08x %08x %u %u %u %08x\n",row[0],elapsed,row[1],row[2],row[3],row[4],row[5],row[6],row[7]);frame_output(line);
 snprintf(line,sizeof(line),"FRAMECOST %u %u %u %u\n",row[0],frame_clock_reads,frame_audio_consumed,frame_audio_underruns);frame_output(line);
 frame_ppm(measured);measured++;
 if(measured==FRAME_COUNT){frame_output("FRAMEHARNESS PASS HAL init\n");if(frame_host)frame_syscall(93,0,0,0,0,0,0);for(;;){}}
}
extern char __frame_heap_start[],__bss_end[];
static void raw_file(const char*name,const void*data,unsigned size){long fd=frame_syscall(56,-100,(long)name,577,0600,0,0);if(fd<0)frame_fail("checkpoint open");const char*s=data;while(size){long n=frame_syscall(64,fd,(long)s,size,0,0,0);if(n<=0)frame_fail("checkpoint write");size-=n;s+=n;}frame_syscall(57,fd,0,0,0,0,0);}
void frame_checkpoint(void){
 if(FRAME_FB_UNCACHED)raw_file("framebuffer.bin",(void*)0x53a00000u,640u*480u*4u);
 unsigned top=(unsigned)frame_heap_cursor;
 raw_file("checkpoint.bin",(void*)0x10400000u,top-0x10400000u);
 raw_file("stack.bin",(void*)0x13f80000u,0x7f000u);
 unsigned info[3]={(unsigned)(uintptr_t)__frame_heap_start,top,FRAME_TARGET};raw_file("checkpoint-info.bin",info,sizeof(info));
}
extern int game_main(int,char**);
void frame_host_main(void){char *args[]={"frame-runner",FRAME_SPEED ? "--bench-smooth" : "--bench",NULL};game_main(2,args);frame_fail("game ended before capture");}
