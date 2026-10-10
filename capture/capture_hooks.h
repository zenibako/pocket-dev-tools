#ifndef BATTLE_CAPTURE_H
#define BATTLE_CAPTURE_H
#include "vm.h"
bool battle_capture_begin(VMContext *ctx, int32_t code);
void battle_capture_end(VMContext *ctx, RValue result);
void battle_capture_tick(VMContext *ctx);
RValue battle_capture_builtin(VMContext *ctx, unsigned index, BuiltinFunc fn, RValue *args, int count);
#endif
