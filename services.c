/* Unmodeled game services fail closed. The interpreter is not modified. */
#include "vm_builtins.h"
#include "battle_replay.h"
#include "runner.h"
#include "physics/physics_engine.h"
#include "log.h"
#include <stdlib.h>
#include <stdio.h>
#include <stdarg.h>

void harness_fail(const char *reason);
bool DataWin_isVersionAtLeast(const DataWin *dw, uint32_t a, uint32_t b, uint32_t c, uint32_t d) {
    const DetectedFormat *f=&dw->detectedFormat;
    if(f->major!=a)return f->major>a;
    if(f->minor!=b)return f->minor>b;
    if(f->release!=c)return f->release>c;
    return f->build>=d;
}
void VMBuiltins_checkIfBuiltinVarTableIsSorted(void) {}
void VMBuiltins_registerAll(VMContext *ctx) {(void)ctx; harness_fail("builtin registration");}
int16_t VMBuiltins_resolveBuiltinVarId(const char *name) {(void)name; harness_fail("builtin resolution");return -1;}
bool VMBuiltins_isInstanceScopedBuiltinVar(int16_t id) {(void)id; harness_fail("builtin scope");return false;}
RValue VMBuiltins_getVariable(VMContext *ctx, Instance *inst, int16_t id, const char *name, int32_t index) {
    if(battle_replay_active())return battle_replay_get(ctx,inst,id,index);
    (void)name;harness_fail("builtin read");return RValue_makeUndefined();
}
void VMBuiltins_setVariable(VMContext *ctx, Instance *inst, int16_t id, const char *name, RValue value, int32_t index) {
    if(battle_replay_active()){battle_replay_set(ctx,inst,id,index,value);return;}
    (void)name;harness_fail("builtin write");
}
Instance *Runner_createStruct(Runner *runner) {(void)runner;harness_fail("runner struct");return NULL;}
int32_t Runner_pushInstancesOfObject(Runner *runner,int32_t object) {(void)runner;(void)object;harness_fail("runner snapshot");return 0;}
void Runner_popInstanceSnapshot(Runner *runner,int32_t base) {(void)runner;(void)base;harness_fail("runner snapshot pop");}
void Profiler_destroy(Profiler *p) {if(p)harness_fail("profiler");}
void Profiler_enter(Profiler *p,const char *name) {(void)name;if(p)harness_fail("enabled profiler");}
void Profiler_exit(Profiler *p) {if(p)harness_fail("enabled profiler");}
void PhysicsEngine_destroyBody(PhysicsBody *body) {if(body)harness_fail("physics");}

#define LOGGER(NAME) void NAME(const char *fmt,...) {va_list ap;va_start(ap,fmt);vLogError(fmt,ap);va_end(ap);}
void vLogError(const char *fmt,va_list ap) {char b[512];vsnprintf(b,sizeof(b),fmt,ap);harness_fail(b);}
LOGGER(logError)
LOGGER(logWarn)
LOGGER(logInfo)
LOGGER(logDebug)
void vLogInfo(const char *fmt,va_list ap) {vLogError(fmt,ap);}
void vLogWarn(const char *fmt,va_list ap) {vLogError(fmt,ap);}
void vLogDebug(const char *fmt,va_list ap) {vLogError(fmt,ap);}
