#include "frame.h"
#include "of.h"
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
static uint8_t *buffers[2];
static int draw_buf;
static uint8_t *presented;
static int16_t captured_pcm[131072*2];
unsigned frame_clock_reads,frame_audio_consumed,frame_audio_underruns;
static unsigned audio_last,audio_fraction;
static unsigned cycles(void){return frame_host?0:*(volatile unsigned*)0x40000004u;}
void frame_clock_read(void){frame_clock_reads++;if(!frame_host && FRAME_CLOCK_COST){unsigned start=cycles();while(cycles()-start<FRAME_CLOCK_COST){}}}
static void consume(unsigned n){frame_audio_consumed+=n;if(n>frame_audio_queued){frame_audio_underruns+=n-frame_audio_queued;frame_audio_queued=0;}else frame_audio_queued-=n;}
static void audio_poll(void){if(FRAME_AUDIO_REALTIME && !frame_host){unsigned now=cycles();unsigned long long units=(unsigned long long)(now-audio_last)*48000u+audio_fraction;audio_last=now;consume(units/100000000u);audio_fraction=units%100000000u;}}
void frame_platform_begin(void){audio_last=cycles();if(!FRAME_AUDIO_REALTIME || frame_host)consume(800);}
void frame_platform_end(void){audio_poll();}
static of_video_mode_t mode={320,240,640,OF_VIDEO_MODE_RGB555,0};
unsigned frame_pcm_hash,frame_pcm_pairs,frame_audio_queued;
void of_video_init(void){if(!buffers[0]){if(FRAME_FB_UNCACHED){buffers[0]=(uint8_t*)0x53a00000u;buffers[1]=buffers[0]+640*480*2;memset(buffers[0],0,640*480*4);}else{buffers[0]=calloc(1,640*480*2);buffers[1]=calloc(1,640*480*2);}if(!buffers[0]||!buffers[1])frame_fail("framebuffers");}}
int of_video_check_mode(const of_video_mode_t*m,of_video_mode_t*out){if(!m||m->width>640||m->height>480||!m->width||!m->height||m->color_mode!=OF_VIDEO_MODE_RGB555)return -1;if(out){*out=*m;out->stride=m->width*2;}return 0;}
int of_video_set_mode(const of_video_mode_t*m){if(of_video_check_mode(m,&mode))return -1;return 0;}
void of_video_get_mode(of_video_mode_t*m){*m=mode;}
uint8_t *of_video_surface(void){return buffers[draw_buf];}
void of_video_flip(void){presented=buffers[draw_buf];draw_buf^=1;}
void of_video_wait_flip(void){}
void of_video_set_color_mode(int x){(void)x;}
void of_video_set_display_mode(int x){(void)x;}
void of_video_get_timing(of_video_timing_t*x){memset(x,0,sizeof(*x));}
void of_input_poll(void){}
void of_input_poll_p0(void){}
int of_btn(uint32_t x){(void)x;return 0;}
int of_btn_pressed(uint32_t x){(void)x;return 0;}
int of_btn_released(uint32_t x){(void)x;return 0;}
uint32_t of_input_state(int p,of_input_state_t*s){(void)p;memset(s,0,sizeof(*s));return 0;}
void of_input_keyboard_state(of_keyboard_state_t*s){memset(s,0,sizeof(*s));}
void of_input_mouse_state(of_mouse_state_t*s){memset(s,0,sizeof(*s));}
int of_input_is_docked(void){return 0;}
void of_audio_init(void){frame_audio_queued=0;}
int of_audio_free(void){audio_poll();return 131072-(int)frame_audio_queued;}
int of_audio_write(const int16_t *samples,int count){if(count<0 || (unsigned)count>131072-frame_audio_queued)frame_fail("audio queue");if(frame_host){if(frame_pcm_pairs+(unsigned)count>131072)frame_fail("PCM capture bound");memcpy(captured_pcm+frame_pcm_pairs*2,samples,(size_t)count*4);}
 if(!FRAME_TIMING || frame_host)frame_pcm_hash=frame_hash(samples,(size_t)count*4,frame_pcm_hash);frame_pcm_pairs+=count;frame_audio_queued+=count;return count;}
unsigned int of_time_us(void){frame_clock_read();return frame_clock/1000;}
unsigned int of_time_ms(void){frame_clock_read();return frame_clock/1000000;}
static uint8_t *picture(void){return presented?presented:of_video_surface();}
unsigned frame_pixels(void){return frame_hash(picture(),(size_t)mode.stride*mode.height,2166136261u);}
static void raw_output(const char*name,const void*data,unsigned size){long fd=frame_syscall(56,-100,(long)name,577,0600,0,0);if(fd<0)frame_fail("raw output open");const char *p=data;while(size){long n=frame_syscall(64,fd,(long)p,size,0,0,0);if(n<=0)frame_fail("raw output write");p+=n;size-=n;}frame_syscall(57,fd,0,0,0,0,0);}
void frame_ppm(unsigned index){
 if(!frame_host)return;char name[32];snprintf(name,sizeof(name),"frame-%u.rgb555",index);raw_output(name,picture(),(unsigned)mode.stride*mode.height);snprintf(name,sizeof(name),"frame-%u.pcm",index);raw_output(name,captured_pcm,frame_pcm_pairs*4);snprintf(name,sizeof(name),"frame-%u.ppm",index);
 long fd=frame_syscall(56,-100,(long)name,577,0600,0,0);if(fd<0)frame_fail("PPM open");
 char header[80];int n=snprintf(header,sizeof(header),"P6\n%u %u\n255\n",mode.width,mode.height);frame_syscall(64,fd,(long)header,n,0,0,0);
 const uint16_t *src=(const uint16_t*)picture();unsigned char row[640*3];
 for(unsigned y=0;y<mode.height;y++){for(unsigned x=0;x<mode.width;x++){unsigned p=src[y*mode.width+x];row[x*3]=((p>>10)&31)<<3;row[x*3+1]=((p>>5)&31)<<3;row[x*3+2]=(p&31)<<3;}frame_syscall(64,fd,(long)row,mode.width*3,0,0,0);}frame_syscall(57,fd,0,0,0,0,0);
}

/* Device branches compile against explicit harness OS-service substitutions. */
void of_file_slot_register(uint32_t slot,const char *name){(void)slot;(void)name;}
void of_file_set_idle_hook(void (*hook)(void)){(void)hook;}
int of_file_slot_find(const char *name,uint32_t *slot){(void)name;(void)slot;return -1;}
uint32_t of_file_async_max_read(void){return 0;}
void *of_file_dma_stage_alloc(uint32_t size,uint32_t align){(void)size;(void)align;return NULL;}
int of_file_read_async(int slot,uint32_t offset,void *dest,uint32_t size,void (*callback)(int,int)){(void)slot;(void)offset;(void)dest;(void)size;(void)callback;return -1;}
int of_file_async_poll(void){return 0;}
int of_file_async_busy(void){return 0;}
static const struct of_capabilities capabilities={.heap_base=0x10800000,.heap_size=51u*1024u*1024u,.cpu_freq_hz=100000000};
const struct of_capabilities *of_get_caps(void){return &capabilities;}
int of_has_feature(uint32_t feature){(void)feature;return 0;}
