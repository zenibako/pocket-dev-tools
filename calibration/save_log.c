/* Same Pocket save-slot transport as the game benchmark logs: plain text,
   fopen("wb"), checked writes, a terminating NUL and checked fclose. The
   instance JSON maps this separate filename to the core's second save slot.
   Keep the latest calibration run only, so comparison has one complete set. */
#include "save_log.h"
#include <stdio.h>
#include <string.h>

static char history[16*1024];
static size_t length;
static int overflow;

void cal_log_keep(const char *text){
 size_t n=strlen(text);
 if(n>sizeof(history)-length){overflow=1;return;}
 memcpy(history+length,text,n);length+=n;
}
int cal_log_dump(void){
 if(overflow)return 0;
 FILE *file=fopen(CAL_LOG_FILE,"wb");
 if(!file)return 0;
 int ok=fwrite(history,1,length,file)==length;
 ok=ok && fputc('\0',file)!=EOF;
 return fclose(file)==0 && ok;
}
