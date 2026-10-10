/* Synthetic BC16/BC17 programs run through the unchanged production VM. */
#include "vm.h"
#include "battle_replay.h"
#include "instance.h"
#include "runner.h"
#include "int_rvalue_hashmap.h"
#include "vm_builtins.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void harness_put(const char *s);
void harness_fail(const char *s);
unsigned harness_cycles(void);
#ifndef HARNESS_REPEATS
#define HARNESS_REPEATS 2
#endif
#ifndef HARNESS_EXPECT_BIAS
#define HARNESS_EXPECT_BIAS 0
#endif
static uint32_t words[4096];
static unsigned used;
static void emit(unsigned op,unsigned type1,unsigned type2,unsigned low) {
    if(used>=4096)harness_fail("bytecode capacity");
    words[used++]=(op<<24)|(type2<<20)|(type1<<16)|(low&65535);
}
static void push(int n) {emit(OP_PUSHI,GML_TYPE_INT16,0,(unsigned)n);}
static void variable(unsigned op,int scope,unsigned index,unsigned source) {
    emit(op,GML_TYPE_VARIABLE,source,(unsigned)scope);
    words[used++]=((uint32_t)VARTYPE_NORMAL<<24)|index;
}
static void float_push(float value) {emit(OP_PUSH,GML_TYPE_FLOAT,0,0);memcpy(&words[used++],&value,4);}
static void finish(void) {emit(OP_RET,GML_TYPE_VARIABLE,0,0);}
static void integer_program(void) {
    for(unsigned i=0;i<64;i++) {
        push(3);push(7);emit(OP_MUL,GML_TYPE_INT32,GML_TYPE_INT32,0);
        push(2);emit(OP_ADD,GML_TYPE_INT32,GML_TYPE_INT32,0);
        if(i!=63)emit(OP_POPZ,0,0,0);
    }
    finish();
}
static void float_program(void) {
    for(unsigned i=0;i<64;i++) {
        float_push(1.25f);float_push(2.0f);emit(OP_MUL,GML_TYPE_FLOAT,GML_TYPE_FLOAT,0);
        float_push(0.5f);emit(OP_ADD,GML_TYPE_FLOAT,GML_TYPE_FLOAT,0);
        if(i!=63)emit(OP_POPZ,0,0,0);
    }
    finish();
}
static void variable_program(int scope) {
    for(unsigned i=0;i<16;i++) {push((int)i);variable(OP_POP,scope,i,GML_TYPE_INT16);}
    for(unsigned i=0;i<128;i++) {
        unsigned k=(i*7)&15;
        variable(OP_PUSH,scope,k,0);push(1);emit(OP_ADD,GML_TYPE_VARIABLE,GML_TYPE_INT16,0);
        variable(OP_POP,scope,k,GML_TYPE_VARIABLE);
    }
    variable(OP_PUSH,scope,15,0);finish();
}
static void branch_program(void) {
    push(0);variable(OP_POP,INSTANCE_LOCAL,0,GML_TYPE_INT16);
    unsigned loop=used;
    variable(OP_PUSH,INSTANCE_LOCAL,0,0);push(1);emit(OP_ADD,GML_TYPE_VARIABLE,GML_TYPE_INT16,0);
    variable(OP_POP,INSTANCE_LOCAL,0,GML_TYPE_VARIABLE);
    variable(OP_PUSH,INSTANCE_LOCAL,0,0);push(64);emit(OP_CMP,GML_TYPE_VARIABLE,GML_TYPE_INT16,CMP_LT<<8);
    unsigned branch=used;words[used++]=((uint32_t)OP_BT<<24)|((loop-branch)&0x7fffff);
    variable(OP_PUSH,INSTANCE_LOCAL,0,0);finish();
}
static void call_program(CodeEntry *entries) {
    for(unsigned i=0;i<64;i++) {
        push(5);emit(OP_CALL,GML_TYPE_INT32,0,1);words[used++]=0;
        if(i!=63)emit(OP_POPZ,0,0,0);
    }
    finish();entries[0].length=used*4;
    entries[1].bytecodeAbsoluteOffset=used*4;
    unsigned start=used;
    variable(OP_PUSH,INSTANCE_ARG,0,0);push(8);emit(OP_ADD,GML_TYPE_VARIABLE,GML_TYPE_INT16,0);finish();
    entries[1].length=(used-start)*4;
}
static unsigned mix(unsigned hash,unsigned value) {return (hash^value)*16777619u;}
static unsigned check(VMContext *ctx,RValue result,unsigned kind,unsigned expected) {
    if((unsigned)RValue_toInt32(result)!=expected+HARNESS_EXPECT_BIAS)harness_fail("independent return oracle");
    if(kind==1 && RValue_toReal(result)!=3.0f)harness_fail("independent float oracle");
    if(ctx->stack.top || ctx->localVars || ctx->callStack || ctx->callDepth || ctx->scriptArgs)
        harness_fail("VM frame cleanup");
    unsigned hash=mix(2166136261u,(unsigned)RValue_toInt32(result));
    if(kind==5 || kind==6) for(unsigned i=0;i<16;i++) {
        int id=ctx->dataWin->vari.variables[i].varID;
        Instance *scope=kind==5?ctx->currentInstance:ctx->globalScopeInstance;
        RValue v=IntRValueHashMap_get(&scope->selfVars,id);
        if(RValue_toInt32(v)!=(int)i+8)harness_fail("independent variable oracle");
        hash=mix(hash,(unsigned)RValue_toInt32(v));
    }
    RValue_free(&result);return hash;
}
static void one(unsigned kind) {
    static const char *names[]={"bc16_integer","bc16_float","bc16_branch","bc16_locals","bc17_locals","bc17_self","bc17_global","bc17_script_call"};
    DataWin dw={0};CodeEntry entries[2]={0};Variable vars[16]={0};Function fn={0};
    dw.gen8.wadVersion=kind<4?16:17;
    dw.detectedFormat.major=kind<4?1:2;dw.detectedFormat.minor=kind<4?4:0;
    dw.code.count=kind==7?2:1;dw.code.entries=entries;
    entries[0].present=true;entries[0].name=names[kind];entries[0].localsCount=16;
    entries[1].present=true;entries[1].name="harness_callee";entries[1].argumentsCount=1;
    dw.vari.variableCount=16;dw.vari.variables=vars;
    for(unsigned i=0;i<16;i++) {vars[i].name="harness_variable";vars[i].varID=kind<4?(int)i:(int)(100+i*97);vars[i].builtinVarId=-1;}
    /* Arguments are indexed directly, unlike BC17 local IDs. */
    if(kind==7){vars[0].varID=0;vars[0].builtinVarId=BUILTIN_VAR_ARGUMENT0;}
    used=0;
    switch(kind) {
        case 0:integer_program();break;
        case 1:float_program();break;
        case 2:branch_program();break;
        case 3:case 4:variable_program(INSTANCE_LOCAL);break;
        case 5:variable_program(INSTANCE_SELF);break;
        case 6:variable_program(INSTANCE_GLOBAL);break;
        case 7:call_program(entries);break;
    }
    if(kind!=7)entries[0].length=used*4;
    dw.bytecodeBuffer=(uint8_t *)words;
    VMContext *ctx=calloc(1,sizeof(*ctx));if(!ctx)harness_fail("context allocation");
    ctx->dataWin=&dw;ctx->codeLocalsSlotMaps=calloc(2,sizeof(IntIntHashMap));
    ctx->globalScopeInstance=Instance_create(INSTANCE_ID_BASE+1,0,0,0);
    ctx->currentInstance=Instance_create(INSTANCE_ID_BASE,0,0,0);
    Runner *runner=calloc(1,sizeof(*runner));
    if(!ctx->codeLocalsSlotMaps || !ctx->globalScopeInstance || !ctx->currentInstance || !runner)
        harness_fail("fixture allocation");
    runner->dataWin=&dw;ctx->runner=runner;
    FuncCallCache cache={0};cache.scriptCodeIndex=1;
    if(kind==7){fn.name="harness_callee";dw.func.functionCount=1;dw.func.functions=&fn;ctx->funcCallCache=&cache;}
    unsigned expected=kind==1?3:kind==2?64:kind==7?13:23;
    unsigned hash=check(ctx,VM_executeCode(ctx,0),kind,expected);
    for(unsigned round=0;round<3;round++) {
        unsigned elapsed=0;
        for(unsigned repeat=0;repeat<HARNESS_REPEATS;repeat++) {
            unsigned t=harness_cycles();RValue result=VM_executeCode(ctx,0);unsigned end=harness_cycles();
            elapsed+=end-t;if(check(ctx,result,kind,expected)!=hash)harness_fail("batch hash");
        }
        char line[180];snprintf(line,sizeof(line),"VMRESULT %u %u %u %08x %u %u %s\n",kind,round,elapsed,hash,HARNESS_REPEATS,entries[0].length,names[kind]);harness_put(line);
    }
    for(unsigned i=0;i<2;i++)IntIntHashMap_free(&ctx->codeLocalsSlotMaps[i]);
    free(ctx->codeLocalsSlotMaps);Instance_free(ctx->globalScopeInstance);Instance_free(ctx->currentInstance);free(runner);free(ctx);
}
int main(void) {
    for(unsigned kind=0;kind<8;kind++)one(kind);
    battle_run_all();
    harness_put("VMHARNESS PASS HAL init\n");return 0;
}
