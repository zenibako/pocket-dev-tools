#define _GNU_SOURCE
#include "frame.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <time.h>
#include <sys/time.h>
#include <errno.h>
#include <stdarg.h>
#include "of.h"
int frame_host FRAME_META=1;
unsigned frame_context[64] FRAME_META;
unsigned char frame_tls[4096] FRAME_META;
unsigned frame_expected[3][8] FRAME_META;
extern char __frame_heap_start[];
uintptr_t frame_heap_cursor;
static uintptr_t heap_limit;
/* Bounded segregated allocator. Splitting/coalescing avoids retaining huge
 * free blocks for tiny VM temporaries. This is still a harness allocator. */
typedef struct Block {size_t size;struct Block *prev,*next,*free_prev,*free_next;unsigned free,pad,pad2;} Block;
static Block *bins[32],*last_block;
static unsigned bucket(size_t size){unsigned k=0;while(size>>=1)k++;return k;}
static void unlink_free(Block*b){unsigned k=bucket(b->size);if(b->free_prev)b->free_prev->free_next=b->free_next;else bins[k]=b->free_next;if(b->free_next)b->free_next->free_prev=b->free_prev;b->free=0;}
static void link_free(Block*b){unsigned k=bucket(b->size);b->free=1;b->free_prev=NULL;b->free_next=bins[k];if(bins[k])bins[k]->free_prev=b;bins[k]=b;}
static void split(Block*b,size_t n){
 if(b->size<n+sizeof(Block)+16)return;
 Block*t=(Block*)((char*)(b+1)+n);memset(t,0,sizeof(*t));t->size=b->size-n-sizeof(Block);t->prev=b;t->next=b->next;
 if(t->next)t->next->prev=t;else last_block=t;b->next=t;b->size=n;link_free(t);
}
void *malloc(size_t n) {
 if(!frame_heap_cursor){frame_heap_cursor=(uintptr_t)__frame_heap_start;heap_limit=frame_heap_cursor+51u*1024u*1024u;if(heap_limit>0x13a00000)heap_limit=0x13a00000;}
 if(!n)n=1;if(n>51u*1024u*1024u-32)return NULL;n=(n+15)&~15u;
 for(unsigned k=bucket(n);k<32;k++)for(Block*b=bins[k];b;b=b->free_next)if(b->size>=n){unlink_free(b);split(b,n);return b+1;}
 if(frame_heap_cursor+sizeof(Block)+n>heap_limit)return NULL;
 Block*b=(Block*)frame_heap_cursor;frame_heap_cursor+=sizeof(*b)+n;memset(b,0,sizeof(*b));b->size=n;b->prev=last_block;if(last_block)last_block->next=b;last_block=b;return b+1;
}
void free(void*p){if(!p)return;Block*b=(Block*)p-1;if(b->free)frame_fail("double free");
 if(b->next && b->next->free){Block*t=b->next;unlink_free(t);b->size+=sizeof(*t)+t->size;b->next=t->next;if(b->next)b->next->prev=b;else last_block=b;}
 if(b->prev && b->prev->free){Block*t=b->prev;unlink_free(t);t->size+=sizeof(*b)+b->size;t->next=b->next;if(t->next)t->next->prev=t;else last_block=t;b=t;}
 link_free(b);
}
void *calloc(size_t n,size_t s){if(s && n>SIZE_MAX/s)return NULL;size_t z=n*s;void*p=malloc(z);if(p)memset(p,0,z);return p;}
void *realloc(void*p,size_t n){if(!p)return malloc(n);if(!n){free(p);return NULL;}Block*b=(Block*)p-1;if(b->size>=n)return p;void*q=malloc(n);if(q){memcpy(q,p,b->size);free(p);}return q;}
long frame_syscall(long nr,long p0,long p1,long p2,long p3,long p4,long p5) {
 register long a0 __asm__("a0")=p0,a1 __asm__("a1")=p1,a2 __asm__("a2")=p2,a3 __asm__("a3")=p3,a4 __asm__("a4")=p4,a5 __asm__("a5")=p5,a7 __asm__("a7")=nr;
 __asm__ volatile("ecall":"+r"(a0):"r"(a1),"r"(a2),"r"(a3),"r"(a4),"r"(a5),"r"(a7):"memory");return a0;
}
void frame_output(const char*s){if(frame_host){frame_syscall(64,1,(long)s,strlen(s),0,0,0);return;}while(*s){while(!(*(volatile unsigned*)0x4f000000u&2)){}*(volatile unsigned*)0x4f000004u=(unsigned char)*s++;}}
void frame_fail(const char*s){frame_output("FRAMEHARNESS FAIL ");frame_output(s);frame_output("\n");if(frame_host)frame_syscall(93,2,0,0,0,0,0);for(;;){}}
__attribute__((weak)) void abort(void){frame_fail("abort");}
void exit(int code){if(frame_host)frame_syscall(93,code,0,0,0,0,0);frame_fail("unexpected exit");}
void __assert_fail(const char*s,const char*f,int l,const char*n){(void)f;(void)l;(void)n;frame_fail(s);}
void frame_trap_report(unsigned cause,unsigned pc,unsigned val){char s[100];snprintf(s,sizeof(s),"trap %x pc=%x val=%x",cause,pc,val);frame_fail(s);}
int frame_rpc(unsigned op,const char*name,unsigned offset,void*buf,unsigned size) {
 volatile uint32_t *m=(volatile uint32_t*)0x30000000u;
 volatile unsigned char *payload=(volatile unsigned char*)0x30001000u;
 if(size>65536)frame_fail("RPC size");
 const char *s=name;unsigned i=0;while(s && *s && i<255)((volatile char*)m)[64+i++]=*s++;
 ((volatile char*)m)[64+i]=0;m[1]=offset;m[2]=size;m[0]=op;
 while(m[0]){}int result=(int)m[3];
 if(op==2 && result>(int)size)frame_fail("RPC result size");
 if(op==2 && result>0)for(int j=0;j<result;j++)((unsigned char*)buf)[j]=payload[j];
 return result;
}
typedef struct {char *name;int fd;off_t offset,size;} Cookie;
static uint64_t fdmask=7;
static ssize_t cookie_read(void *arg,char *buf,size_t size) {
 Cookie*c=arg;ssize_t total=0;
 while(size){size_t n=size>65536?65536:size;ssize_t got;
  if(frame_host)got=pread(c->fd,buf,n,c->offset);
  else got=frame_rpc(2,c->name,(unsigned)c->offset,buf,n);
  if(got<0)return total?total:-1;if(!got)break;c->offset+=got;buf+=got;size-=got;total+=got;if((size_t)got<n)break;
 }return total;
}
static int cookie_seek(void*arg,off_t*offset,int whence){Cookie*c=arg;off_t base=whence==SEEK_SET?0:whence==SEEK_CUR?c->offset:c->size;if(base+*offset<0)return -1;c->offset=base+*offset;*offset=c->offset;return 0;}
static int cookie_close(void*arg){Cookie*c=arg;if(frame_host)close(c->fd);fdmask&=~(1ull<<c->fd);free(c->name);free(c);return 0;}
FILE *__wrap_fopen(const char*name,const char*mode) {
 if(mode[0]!='r')frame_fail("write to game file");int fd;off_t size;
 if(frame_host){fd=open(name,O_RDONLY);if(fd<0)return NULL;size=lseek(fd,0,SEEK_END);}
 else {int n=frame_rpc(1,name,0,NULL,0);if(n<0)return NULL;size=n;for(fd=3;fd<63 && (fdmask&(1ull<<fd));fd++){}if(fd==63)frame_fail("file handles");}
 if(fd>63 || size<0)frame_fail("file open");fdmask|=1ull<<fd;
 Cookie*c=calloc(1,sizeof(*c));if(!c)frame_fail("file cookie allocation");c->name=strdup(name);c->fd=fd;c->size=size;
 cookie_io_functions_t io={.read=cookie_read,.seek=cookie_seek,.close=cookie_close};FILE*f=fopencookie(c,"r",io);if(!f)frame_fail("stdio cookie");return f;
}
char *getenv(const char *name){
 if(!strcmp(name,"UT_NO_NATIVE"))return FRAME_DISABLE_NATIVE ? "1" : NULL;
 if(!strcmp(name,"UT_UNCAPPED") || !strcmp(name,"UT_NOFLIP"))return "1";
 if(!strcmp(name,"UT_SEED"))return "7";return NULL;
}
uint64_t frame_clock;
extern void frame_clock_read(void);
int clock_gettime(clockid_t id,struct timespec *ts){frame_clock_read();(void)id;ts->tv_sec=frame_clock/1000000000ull;ts->tv_nsec=frame_clock%1000000000ull;return 0;}
int gettimeofday(struct timeval *v,void *tz){frame_clock_read();(void)tz;v->tv_sec=frame_clock/1000000000ull;v->tv_usec=(frame_clock/1000)%1000000;return 0;}
int usleep(useconds_t x){(void)x;return 0;}
int __real_vfprintf(FILE*,const char*,va_list);
int __wrap_vfprintf(FILE*f,const char*fmt,va_list ap){if(f!=stdout && f!=stderr)return __real_vfprintf(f,fmt,ap);char b[2048];int n=vsnprintf(b,sizeof(b),fmt,ap);frame_output(b);return n;}
int __wrap_fprintf(FILE*f,const char*fmt,...){va_list ap;va_start(ap,fmt);int n=__wrap_vfprintf(f,fmt,ap);va_end(ap);return n;}
int __wrap_printf(const char*fmt,...){va_list ap;va_start(ap,fmt);int n=__wrap_vfprintf(stdout,fmt,ap);va_end(ap);return n;}
int __wrap_vprintf(const char*fmt,va_list ap){return __wrap_vfprintf(stdout,fmt,ap);}
int __real_fputs(const char*,FILE*);
int __wrap_fputs(const char*s,FILE*f){if(f!=stdout && f!=stderr)return __real_fputs(s,f);frame_output(s);return 0;}
int __wrap_puts(const char*s){frame_output(s);frame_output("\n");return 0;}
int __wrap_putchar(int c){char b[2]={(char)c,0};frame_output(b);return c;}
size_t __real_fwrite(const void*,size_t,size_t,FILE*);
size_t __wrap_fwrite(const void*p,size_t s,size_t n,FILE*f){if(f!=stdout && f!=stderr)return __real_fwrite(p,s,n,f);const char*bytes=p;for(size_t i=0;i<s*n;i++){char b[2]={bytes[i],0};frame_output(b);}return n;}
