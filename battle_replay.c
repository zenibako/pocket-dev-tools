/* Replay captured numeric battle events through the unchanged production VM.
 * External calls are an ordered, argument-checked transcript, not timed game services. */
#include "battle_replay.h"
#include "runner.h"
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
void harness_fail(const char *);
void harness_put(const char *);
unsigned harness_cycles(void);
#ifndef HARNESS_BATTLE_EXPECT_BIAS
#define HARNESS_BATTLE_EXPECT_BIAS 0
#endif
#ifndef HARNESS_REPEATS
#define HARNESS_REPEATS 2
#endif
#include "battle_fixtures.inc"
static const BattleFixture *current;
static VMContext *owner;
static unsigned cursor;
static unsigned mix(unsigned h,unsigned v){return (h^v)*16777619u;}
static RValue decode(BattleValue v) {
    RValue r={0};r.type=v.type;r.gmlStackType=v.stack;r.assetRefType=v.asset;
    memcpy(&r.int32,&v.bits,4);return r;
}
static BattleValue encode(RValue r) {
    BattleValue v={r.type,0,r.gmlStackType,r.assetRefType};
    if(r.type!=RVALUE_UNDEFINED)memcpy(&v.bits,&r.int32,4);
    return v;
}
static bool equal(BattleValue a,BattleValue b) {
    return a.type==b.type && a.bits==b.bits && a.stack==b.stack && a.asset==b.asset;
}
bool battle_replay_active(void){return current!=NULL;}
static const BattleIo *next(VMContext *ctx,int kind,int id,Instance *inst,int index) {
    if(!current || ctx!=owner || cursor>=current->io_count)harness_fail("battle unexpected external call");
    const BattleIo *io=&current->io[cursor++];
    if(io->kind!=kind || io->id!=id || (kind!=2 && (io->instance!=(inst?(int)inst->instanceId:-1) || io->index!=index)))
        harness_fail("battle external call order");
    return io;
}
RValue battle_replay_function(VMContext *ctx,unsigned id,RValue *args,int count) {
    const BattleIo *io=next(ctx,2,(int)id,NULL,0);
    if(count<0 || (unsigned)count!=io->nargs)harness_fail("battle function argument count");
    for(int i=0;i<count;i++)if(!equal(encode(args[i]),io->args[i]))harness_fail("battle function argument oracle");
    return decode(io->value);
}
RValue battle_replay_get(VMContext *ctx,Instance *inst,int id,int index) {
    return decode(next(ctx,0,id,inst,index)->value);
}
void battle_replay_set(VMContext *ctx,Instance *inst,int id,int index,RValue value) {
    if(!equal(encode(value),next(ctx,1,id,inst,index)->value))harness_fail("battle builtin write oracle");
}
static void restore_map(IntRValueHashMap *m,const BattleMap *image) {
    m->capacity=image->capacity;m->mask=m->capacity?m->capacity-1:0;m->count=image->count;
    m->entries=m->capacity?calloc(m->capacity,sizeof(*m->entries)):NULL;
    if(m->capacity && !m->entries)harness_fail("battle map allocation");
    /* Preserve exact occupied keys/probe layout. Untouched nonnumeric values
     * are deliberately undefined: eligible bytecode cannot read them. */
    for(unsigned i=0;i<m->capacity;i++)m->entries[i].key=image->keys[i];
}
static void restore_local(IntIntHashMap *m,const BattleMap *image) {
    m->capacity=image->capacity;m->mask=m->capacity?m->capacity-1:0;m->count=image->count;
    m->entries=m->capacity?calloc(m->capacity,sizeof(*m->entries)):NULL;
    if(m->capacity && !m->entries)harness_fail("battle locals allocation");
    if(m->capacity)memcpy(m->entries,image->entries,m->capacity*sizeof(*m->entries));
}
static Instance *scope(VMContext *ctx,int which) {
    return which==INSTANCE_GLOBAL?ctx->globalScopeInstance:ctx->currentInstance;
}
static unsigned check_map(unsigned hash,const IntRValueHashMap *m,const BattleMap *expected) {
    if(m->capacity!=expected->capacity || m->count!=expected->count)harness_fail("battle map size oracle");
    hash=mix(hash,m->count);
    for(unsigned i=0;i<m->capacity;i++) {
        if(m->entries[i].key!=expected->keys[i])harness_fail("battle map probe layout oracle");
        hash=mix(hash,(unsigned)m->entries[i].key);
    }
    return hash;
}
static unsigned hash_value(unsigned hash,BattleValue v) {
    hash=mix(hash,v.type);hash=mix(hash,v.bits);hash=mix(hash,v.stack);return mix(hash,v.asset);
}
static unsigned check(VMContext *ctx,RValue result) {
    BattleValue encoded=encode(result),expected=current->result;expected.bits+=HARNESS_BATTLE_EXPECT_BIAS;
    if(!equal(encoded,expected))harness_fail("battle independent return oracle");
    if(cursor!=current->io_count)harness_fail("battle missing external calls");
    if(ctx->stack.top || ctx->localVars || ctx->callStack || ctx->callDepth || ctx->scriptArgs || ctx->envStack)
        harness_fail("battle VM frame cleanup");
    unsigned hash=hash_value(2166136261u,encoded);
    for(unsigned i=0;i<current->ref_count;i++) {
        const BattleRef *r=&current->after[i];Variable *v=&current->vars[r->index];
        bool present=false;RValue actual=RValue_makeUndefined();
        if(r->scope!=INSTANCE_LOCAL && v->varID!=VARIABLE_BUILTIN) {
            RValue *slot=IntRValueHashMap_findSlot(&scope(ctx,r->scope)->selfVars,v->varID);
            present=slot!=NULL;if(slot)actual=*slot;
        }
        if(present!=r->present || !equal(encode(actual),r->value))harness_fail("battle variable state oracle");
        hash=mix(hash,(unsigned)r->scope);hash=mix(hash,r->index);hash=mix(hash,present);hash=hash_value(hash,encode(actual));
    }
    hash=check_map(hash,&ctx->currentInstance->selfVars,&current->maps_after[0]);
    hash=check_map(hash,&ctx->globalScopeInstance->selfVars,&current->maps_after[1]);
    const BattleMap *expected_map=&current->maps_after[2];IntIntHashMap *m=&ctx->codeLocalsSlotMaps[0];
    if(m->capacity!=expected_map->capacity || m->count!=expected_map->count)harness_fail("battle locals size oracle");
    hash=mix(hash,m->count);
    for(unsigned i=0;i<m->capacity;i++) {
        IntIntEntry e=m->entries[i];if(e.key==-1)e.value=0;
        if(e.key!=expected_map->entries[i].key || e.value!=expected_map->entries[i].value)harness_fail("battle locals layout oracle");
        hash=mix(hash,(unsigned)e.key);hash=mix(hash,e.value);
    }
    if(hash!=current->hash)harness_fail("battle captured state hash");
    RValue_free(&result);return hash;
}
static unsigned execute(const BattleFixture *f,unsigned *elapsed) {
    DataWin dw={0};CodeEntry entry={0};dw.gen8.wadVersion=f->wad;
    dw.detectedFormat=(DetectedFormat){f->version[0],f->version[1],f->version[2],f->version[3]};
    dw.code.count=1;dw.code.entries=&entry;entry.present=true;entry.name=f->name;
    entry.length=f->word_count*4;entry.localsCount=f->locals_count;
    dw.bytecodeBuffer=(uint8_t*)f->words;dw.vari.variableCount=f->var_count;dw.vari.variables=f->vars;
    dw.func.functionCount=f->function_count;dw.func.functions=f->functions;
    VMContext *ctx=calloc(1,sizeof(*ctx));Runner *runner=calloc(1,sizeof(*runner));
    if(!ctx || !runner)harness_fail("battle context allocation");
    ctx->dataWin=&dw;ctx->runner=runner;runner->dataWin=&dw;runner->frameCount=f->frame;
    ctx->funcCallCache=f->cache;ctx->funcCallCacheCount=f->function_count;
    ctx->currentInstance=Instance_create(f->self_id,f->self_object,0,0);
    ctx->globalScopeInstance=Instance_create(f->global_id,STRUCT_OBJECT_INDEX,0,0);
    ctx->codeLocalsSlotMaps=calloc(1,sizeof(IntIntHashMap));
    if(!ctx->currentInstance || !ctx->globalScopeInstance || !ctx->codeLocalsSlotMaps)harness_fail("battle fixture allocation");
    ctx->selfId=f->self_context;ctx->otherId=f->other_context;
    ctx->currentEventType=f->event_type;ctx->currentEventSubtype=f->event_subtype;ctx->currentEventObjectIndex=f->event_object;
    restore_map(&ctx->currentInstance->selfVars,&f->maps_before[0]);
    restore_map(&ctx->globalScopeInstance->selfVars,&f->maps_before[1]);restore_local(&ctx->codeLocalsSlotMaps[0],&f->maps_before[2]);
    for(unsigned i=0;i<f->ref_count;i++) {
        const BattleRef *r=&f->before[i];Variable *v=&f->vars[r->index];
        if(r->present && r->scope!=INSTANCE_LOCAL && v->varID!=VARIABLE_BUILTIN) {
            RValue *slot=IntRValueHashMap_findSlot(&scope(ctx,r->scope)->selfVars,v->varID);
            if(!slot)harness_fail("battle initial map mismatch");*slot=decode(r->value);
        }
    }
    current=f;owner=ctx;cursor=0;
    unsigned begin=harness_cycles();RValue result=VM_executeCode(ctx,0);unsigned end=harness_cycles();
    if(elapsed)*elapsed+=end-begin;
    unsigned hash=check(ctx,result);current=NULL;owner=NULL;
    Instance_free(ctx->currentInstance);Instance_free(ctx->globalScopeInstance);
    IntIntHashMap_free(&ctx->codeLocalsSlotMaps[0]);free(ctx->codeLocalsSlotMaps);free(ctx);free(runner);
    return hash;
}
void battle_run_all(void) {
    for(unsigned i=0;i<sizeof(battle_fixtures)/sizeof(*battle_fixtures);i++) {
        const BattleFixture *f=&battle_fixtures[i];execute(f,NULL);
        for(unsigned round=0;round<3;round++) {
            unsigned elapsed=0,hash=0;
            for(unsigned repeat=0;repeat<HARNESS_REPEATS;repeat++)hash=execute(f,&elapsed);
            char line[240];snprintf(line,sizeof(line),"BATTLERESULT %u %u %u %08x %u %u %s\n",i,round,elapsed,hash,HARNESS_REPEATS,f->ops,f->name);harness_put(line);
        }
    }
}
