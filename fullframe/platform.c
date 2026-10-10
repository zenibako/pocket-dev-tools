#include "frame.h"
#include "of.h"
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
static uint8_t *buffers[2];
static int draw_buf;
static of_video_mode_t mode={320,240,640,OF_VIDEO_MODE_RGB555,0};
unsigned frame_pcm_hash,frame_pcm_pairs,frame_audio_queued;
void of_video_init(void){if(!buffers[0]){buffers[0]=calloc(1,640*480*2);buffers[1]=calloc(1,640*480*2);if(!buffers[0]||!buffers[1])frame_fail("framebuffers");}}
int of_video_check_mode(const of_video_mode_t*m,of_video_mode_t*out){if(!m||m->width>640||m->height>480||!m->width||!m->height||m->color_mode!=OF_VIDEO_MODE_RGB555)return -1;if(out){*out=*m;out->stride=m->width*2;}return 0;}
int of_video_set_mode(const of_video_mode_t*m){if(of_video_check_mode(m,&mode))return -1;return 0;}
void of_video_get_mode(of_video_mode_t*m){*m=mode;}
uint8_t *of_video_surface(void){return buffers[draw_buf];}
void of_video_flip(void){draw_buf^=1;}
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
int of_audio_free(void){return 131072-(int)frame_audio_queued;}
int of_audio_write(const int16_t *samples,int count){if(count<0 || (unsigned)count>131072-frame_audio_queued)frame_fail("audio queue");frame_pcm_hash=frame_hash(samples,(size_t)count*4,frame_pcm_hash);frame_pcm_pairs+=count;frame_audio_queued+=count;return count;}
unsigned int of_time_us(void){return frame_clock/1000;}
unsigned int of_time_ms(void){return frame_clock/1000000;}
unsigned frame_pixels(void){return frame_hash(of_video_surface(),(size_t)mode.stride*mode.height,2166136261u);}
void frame_ppm(unsigned index){
 if(!frame_host)return;char name[32];snprintf(name,sizeof(name),"frame-%u.ppm",index);
 long fd=frame_syscall(56,-100,(long)name,577,0600,0,0);if(fd<0)frame_fail("PPM open");
 char header[80];int n=snprintf(header,sizeof(header),"P6\n%u %u\n255\n",mode.width,mode.height);frame_syscall(64,fd,(long)header,n,0,0,0);
 const uint16_t *src=(const uint16_t*)of_video_surface();unsigned char row[640*3];
 for(unsigned y=0;y<mode.height;y++){for(unsigned x=0;x<mode.width;x++){unsigned p=src[y*mode.width+x];row[x*3]=((p>>10)&31)<<3;row[x*3+1]=((p>>5)&31)<<3;row[x*3+2]=(p&31)<<3;}frame_syscall(64,fd,(long)row,mode.width*3,0,0,0);}frame_syscall(57,fd,0,0,0,0,0);
}
