// Included in the generated runtime after its state hash and clock helpers.
#include "sw/sw_call_notes.h"
#include "sw/sw_renderer_private.h"
static Runner *probe_runner;
static unsigned probe_stage,probe_sprite,probe_calls,probe_width,probe_height,probe_path;
__attribute__((noinline)) void sprite_probe_begin(int stage,Renderer *renderer,int sprite,int calls,int width,int height,int path){
 probe_stage=stage;probe_sprite=sprite;probe_calls=calls;probe_width=width;probe_height=height;probe_path=path;
 SWRenderer *s=(SWRenderer*)renderer;
 unsigned scaleX,scaleY;memcpy(&scaleX,&s->scaleX,4);memcpy(&scaleY,&s->scaleY,4);
 char info[220];snprintf(info,sizeof(info),"SPRITECONFIG %u %d %d %d %d %d %d %d %d %d %d %08x %08x\n",measured,stage,sprite,width,height,s->viewX,s->viewY,s->viewW,s->viewH,s->portW,s->portH,scaleX,scaleY);frame_output(info);
 frame_ops=frame_events=frame_pcm_pairs=0;
 // Exact clock interval, after setup/logging and before the original call loop.
 begin_cycles=cycles();
}
__attribute__((noinline)) void sprite_probe_end(Renderer *renderer){
 unsigned elapsed=cycles()-begin_cycles;
 unsigned row[8]={measured,state_hash(probe_runner),frame_pixels(),probe_sprite,probe_calls,probe_width,probe_height,(probe_stage<<16)|probe_path};
 if(measured>=24)frame_fail("probe count overflow");
 if(!frame_host)for(unsigned i=0;i<8;i++)if(row[i]!=frame_expected[measured][i]){char text[120];snprintf(text,sizeof(text),"frame %u oracle field %u expected=%08x actual=%08x",measured,i,frame_expected[measured][i],row[i]);frame_fail(text);}
 char line[180];snprintf(line,sizeof(line),"FRAMERESULT %u %u %08x %08x %08x %u %u %u %08x\n",row[0],elapsed,row[1],row[2],row[3],row[4],row[5],row[6],row[7]);frame_output(line);
 snprintf(line,sizeof(line),"FRAMECOST %u 0 0 0\n",measured);frame_output(line);
 extern void frame_ppm(unsigned);frame_ppm(measured);measured++;
}
void frame_begin(Runner*r){
 frame_clock+=16666667ull;
 if(r->frameCount!=FRAME_TARGET)return;
 frame_suspend();probe_runner=r;
 for(int repeat=0;repeat<3;repeat++){
  int32_t width,height;uint32_t nanos[7],outside;int path;
  swrSpriteCostProbe(r->renderer,2000,&width,&height,nanos,&outside,&path);
  if(width<=0 || height<=0)frame_fail("probe could not select sprite");
 }
 if(measured!=24)frame_fail("missing probe samples");
 frame_output("FRAMEHARNESS PASS HAL init\n");
 if(frame_host)frame_syscall(93,0,0,0,0,0,0);for(;;){}
}
void frame_end(Runner*r){(void)r;}
