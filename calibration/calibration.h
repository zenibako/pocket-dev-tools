#ifndef CALIBRATION_H
#define CALIBRATION_H
#include <stdint.h>
typedef uint32_t (*CalKernel)(uint32_t, void *);
typedef struct { const char *name; CalKernel run; void *arg; uint32_t iterations, operations, expected; } CalJob;
extern int calibration_mode; /* 0 SDK hardware, 1 bare RTL, 2 QEMU reference */
extern CalJob calibration_jobs[];
extern unsigned calibration_job_count;
void calibration_setup(void);
uint32_t calibration_sprite_check(void);
void calibration_sprite_warm(void);
void calibration_sprite_stage(unsigned);
uint32_t calibration_sprite_draw(uint32_t,void*);
void calibration_fail(const char*);
int calibration_run(void);
void calibration_trap(unsigned,unsigned,unsigned);
#endif
