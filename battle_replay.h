#ifndef BATTLE_REPLAY_H
#define BATTLE_REPLAY_H
#include "vm.h"
#include "instance.h"
typedef struct { unsigned type,bits,stack,asset; } BattleValue;
typedef struct { int scope; unsigned index,present; BattleValue value; } BattleRef;
typedef struct { unsigned capacity,count; const int32_t *keys; const IntIntEntry *entries; } BattleMap;
typedef struct { int kind,id,instance,index; BattleValue value; unsigned nargs; const BattleValue *args; } BattleIo;
typedef struct {
    const char *name; unsigned wad,version[4],frame,ops,locals_count;
    unsigned self_id,global_id; int self_object,self_context,other_context,event_type,event_subtype,event_object;
    unsigned word_count,var_count,function_count,ref_count,io_count;
    const uint32_t *words; Variable *vars; Function *functions; FuncCallCache *cache;
    const BattleRef *before,*after; const BattleIo *io;
    BattleMap maps_before[3],maps_after[3]; BattleValue result; unsigned hash;
} BattleFixture;
bool battle_replay_active(void);
RValue battle_replay_function(VMContext *,unsigned,RValue *,int);
RValue battle_replay_get(VMContext *,Instance *,int,int);
void battle_replay_set(VMContext *,Instance *,int,int,RValue);
void battle_run_all(void);
#endif
