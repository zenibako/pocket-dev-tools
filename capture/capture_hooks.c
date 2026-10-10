/* Host-only observation hooks. The real runner supplies every recorded value. */
#include "capture_hooks.h"
#include "vm_builtins.h"
#include "runner.h"
#include "runner_keyboard.h"
#include "instance.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_REFS 256
#define MAX_IO 1024
typedef struct { int scope; unsigned index; bool present; RValue value; } Ref;
typedef struct { int write; int id, instance, index; RValue value; int nargs; RValue args[16]; } Io;
static Ref refs[MAX_REFS];
static Io ios[MAX_IO];
static unsigned nrefs, nio, ops;
static bool active, valid;
static int captured_code;
static VMContext *owner;
static FILE *output;
#define MAX_MAP 65536
static int32_t self_keys[MAX_MAP], global_keys[MAX_MAP];
static unsigned self_cap, self_count, global_cap, global_count, local_cap, local_count;
static IntIntEntry local_entries[MAX_MAP];
static bool snapshot_maps(VMContext *ctx,int code) {
    IntRValueHashMap *a=&ctx->currentInstance->selfVars,*b=&ctx->globalScopeInstance->selfVars;
    IntIntHashMap empty={0};
    IntIntHashMap *c=ctx->codeLocalsSlotMaps?&ctx->codeLocalsSlotMaps[code]:&empty;
    if(a->capacity>MAX_MAP || b->capacity>MAX_MAP || c->capacity>MAX_MAP)return false;
    self_cap=a->capacity;self_count=a->count;global_cap=b->capacity;global_count=b->count;
    local_cap=c->capacity;local_count=c->count;
    for(unsigned i=0;i<self_cap;i++)self_keys[i]=a->entries[i].key;
    for(unsigned i=0;i<global_cap;i++)global_keys[i]=b->entries[i].key;
    if(local_cap)memcpy(local_entries,c->entries,sizeof(*local_entries)*local_cap);
    return true;
}
static void map_json(const IntRValueHashMap *m,const int32_t *keys,unsigned cap,unsigned count) {
    fprintf(output,"{\"count\":%u,\"keys\":[",count);
    for(unsigned i=0;i<cap;i++)fprintf(output,"%s%d",i?",":"",keys?keys[i]:m->entries[i].key);
    fprintf(output,"]}");
}
static void local_json(const IntIntHashMap *m) {
    unsigned cap=m?m->capacity:local_cap,count=m?m->count:local_count;
    const IntIntEntry *entries=m?m->entries:local_entries;
    fprintf(output,"{\"count\":%u,\"entries\":[",count);
    for(unsigned i=0;i<cap;i++)fprintf(output,"%s[%d,%u]",i?",":"",entries[i].key,entries[i].key==-1?0:entries[i].value);
    fprintf(output,"]}");
}

static bool numeric(RValue v) {
    return v.type==RVALUE_UNDEFINED || v.type==RVALUE_INT32 || v.type==RVALUE_BOOL || v.type==RVALUE_REAL || v.type==RVALUE_ASSETREF;
}
static void string(FILE *f,const char *s) {
    fputc('"',f);
    while(*s) { unsigned c=(unsigned char)*s++;
        if(c=='"'||c=='\\')fprintf(f,"\\%c",c);
        else if(c<32)fprintf(f,"\\u%04x",c);
        else fputc(c,f);
    }
    fputc('"',f);
}
static void value(FILE *f,RValue v) {
    uint32_t bits=0;
    if(v.type!=RVALUE_UNDEFINED)memcpy(&bits,&v.int32,4);
    fprintf(f,"[%u,%u,%u,%u]",v.type,bits,v.gmlStackType,v.assetRefType);
}
static Instance *scope_instance(VMContext *ctx,int scope) {
    return scope==INSTANCE_GLOBAL ? ctx->globalScopeInstance : ctx->currentInstance;
}
static bool add_ref(VMContext *ctx,int scope,unsigned index) {
    if(index>=ctx->dataWin->vari.variableCount)return false;
    if(scope!=INSTANCE_SELF && scope!=INSTANCE_GLOBAL && scope!=INSTANCE_LOCAL && scope!=INSTANCE_BUILTIN)return false;
    for(unsigned i=0;i<nrefs;i++)if(refs[i].scope==scope && refs[i].index==index)return true;
    if(nrefs==MAX_REFS)return false;
    Ref r={.scope=scope,.index=index,.value=RValue_makeUndefined()};
    Variable *v=&ctx->dataWin->vari.variables[index];
    if(scope!=INSTANCE_LOCAL && v->varID!=VARIABLE_BUILTIN) {
        Instance *inst=scope_instance(ctx,scope);if(!inst)return false;
        RValue *slot=IntRValueHashMap_findSlot(&inst->selfVars,v->varID);
        r.present=slot!=NULL;if(slot)r.value=*slot;
        if(!numeric(r.value))return false;
    }
    refs[nrefs++]=r;return true;
}
static bool eligible(VMContext *ctx,CodeEntry *code) {
    const unsigned char *bytes=ctx->dataWin->bytecodeBuffer + code->bytecodeAbsoluteOffset-ctx->dataWin->bytecodeBufferBase;
    if(code->length>16384 || code->length%4 || code->offset)return false;
    nrefs=0;
    for(unsigned ip=0;ip<code->length;) {
        unsigned instr;memcpy(&instr,bytes+ip,4);ip+=4;
        unsigned op=instr>>24,t1=(instr>>16)&15,t2=(instr>>20)&15;
        switch(op) {
            case OP_CONV:case OP_MUL:case OP_DIV:case OP_REM:case OP_MOD:case OP_ADD:case OP_SUB:
            case OP_AND:case OP_OR:case OP_XOR:case OP_NEG:case OP_NOT:case OP_SHL:case OP_SHR:
            case OP_CMP:case OP_POP:case OP_PUSHI:case OP_DUP:case OP_RET:case OP_EXIT:case OP_POPZ:
            case OP_B:case OP_BT:case OP_BF:case OP_PUSH:case OP_PUSHLOC:case OP_PUSHGLB:case OP_PUSHBLTN:case OP_CALL:break;
            default:return false;
        }
        if(op!=OP_B && op!=OP_BT && op!=OP_BF && (t1==GML_TYPE_STRING || t2==GML_TYPE_STRING || t1==GML_TYPE_INT64 || t2==GML_TYPE_INT64))return false;
        if(instr&0x40000000u) {
            unsigned extra=t1==GML_TYPE_DOUBLE?8:t1==GML_TYPE_INT16?0:4;
            if(ip+extra>code->length)return false;
            if(t1==GML_TYPE_VARIABLE && op!=OP_CALL) {
                unsigned operand;memcpy(&operand,bytes+ip,4);
                unsigned kind=(operand>>24)&0xf8;
                unsigned index=operand&0x07ffffff;
                if(index>=ctx->dataWin->vari.variableCount)return false;
                if(kind==VARTYPE_ARRAY && ctx->dataWin->vari.variables[index].varID==VARIABLE_BUILTIN) {
                    if(!add_ref(ctx,INSTANCE_SELF,index))return false;
                    ip+=extra;continue;
                }
                if(kind!=VARTYPE_NORMAL)return false;
                int scope=(int16_t)instr;
                if(op==OP_PUSHLOC)scope=INSTANCE_LOCAL;
                if(op==OP_PUSHGLB)scope=INSTANCE_GLOBAL;
                if(!add_ref(ctx,scope,operand&0x07ffffff))return false;
            }
            if(op==OP_CALL) {
                unsigned index;memcpy(&index,bytes+ip,4);
                if(index>=ctx->dataWin->func.functionCount || !ctx->funcCallCache[index].builtin)return false;
                const char *name=ctx->dataWin->func.functions[index].name;
                const char *safe[]={"keyboard_check","keyboard_check_pressed","keyboard_check_released","instance_exists",
                    "point_distance","point_direction","sin","cos","abs","floor","ceil","round","max","min",
                    "window_get_width","window_get_height","os_is_paused","sprite_get_width","sprite_get_height","sprite_get_number","sprite_get_xoffset","sprite_get_yoffset","clamp","lerp","lengthdir_x","lengthdir_y","random","irandom","random_range","irandom_range"};
                bool permitted=strncmp(name,"draw_",5)==0;
                for(unsigned i=0;i<sizeof(safe)/sizeof(*safe);i++)if(strcmp(name,safe[i])==0)permitted=true;
                if(!permitted)return false;
            }
            ip+=extra;
        }
    }
    return true;
}
bool battle_capture_begin(VMContext *ctx,int32_t code_index) {
    if(active){valid=false;return false;}
    const char *frames=getenv("HARNESS_CAPTURE_FRAMES");
    if(!frames || !ctx->runner || !ctx->currentInstance)return false;
    int frame=ctx->runner->frameCount;
    bool in_window=false;
    while(*frames) {int lo,hi,used=0;if(sscanf(frames,"%d-%d%n",&lo,&hi,&used)!=2)return false;
        if(frame>=lo&&frame<=hi)in_window=true;frames+=used;if(*frames==',')frames++;else break;
    }
    if(!in_window)return false;
    CodeEntry *code=&ctx->dataWin->code.entries[code_index];
    bool candidate=eligible(ctx,code);
    if(frame==2388 || frame==3138 || frame==3323)
        fprintf(stderr,"CAPTURE EVENT %d %s eligible=%d\n",frame,code->name,candidate);
    if(!candidate || !snapshot_maps(ctx,code_index))return false;
    if(!output) {output=fopen(getenv("HARNESS_CAPTURE_PATH"),"w");if(!output){perror("capture");exit(2);}}
    owner=ctx;captured_code=code_index;nio=ops=0;active=valid=true;return true;
}
void battle_capture_tick(VMContext *ctx) {if(active && ctx==owner)ops++;}
static void io(bool write,VMContext *ctx,Instance *inst,int id,int index,RValue v) {
    if(!active)return;
    if(ctx!=owner || nio==MAX_IO || !numeric(v)){valid=false;return;}
    ios[nio++]=(Io){.write=write,.id=id,.instance=inst?(int)inst->instanceId:-1,.index=index,.value=v};
}
RValue battle_capture_builtin(VMContext *ctx,unsigned index,BuiltinFunc fn,RValue *args,int count) {
    bool record=active && ctx==owner;
    unsigned slot=nio;
    if(record) {
        if(nio==MAX_IO || count<0 || count>16){valid=false;record=false;}
        else {
            Io *r=&ios[nio++];memset(r,0,sizeof(*r));r->write=2;r->id=(int)index;r->nargs=count;
            for(int i=0;i<count;i++){r->args[i]=args[i];if(!numeric(args[i]))valid=false;}
        }
    }
    RValue result=fn(ctx,args,count);
    if(record){ios[slot].value=result;if(!numeric(result))valid=false;}
    return result;
}
static void refs_json(VMContext *ctx,bool after) {
    fputc('[',output);
    for(unsigned i=0;i<nrefs;i++) {
        Ref *r=&refs[i];Variable *v=&ctx->dataWin->vari.variables[r->index];
        bool present=r->present;RValue val=r->value;
        if(after && r->scope!=INSTANCE_LOCAL && v->varID!=VARIABLE_BUILTIN) {
            RValue *slot=IntRValueHashMap_findSlot(&scope_instance(ctx,r->scope)->selfVars,v->varID);
            present=slot!=NULL;val=slot?*slot:RValue_makeUndefined();
        }
        if(i)fputc(',',output);
        fprintf(output,"[%d,%u,%d,",r->scope,r->index,present);value(output,val);fputc(']',output);
    }
    fputc(']',output);
}
void battle_capture_end(VMContext *ctx,RValue result) {
    active=false;
    if(!valid || !numeric(result) || !ops || ops>10000)return;
    for(unsigned i=0;i<nrefs;i++) {
        Ref *r=&refs[i];Variable *v=&ctx->dataWin->vari.variables[r->index];
        if(r->scope!=INSTANCE_LOCAL && v->varID!=VARIABLE_BUILTIN && !numeric(IntRValueHashMap_get(&scope_instance(ctx,r->scope)->selfVars,v->varID)))return;
    }
    DataWin *dw=ctx->dataWin;CodeEntry *code=&dw->code.entries[captured_code];
    fprintf(output,"{\"schema\":1,\"game\":");string(output,getenv("HARNESS_CAPTURE_GAME"));
    fprintf(output,",\"frame\":%d,\"room_index\":%d,\"room\":",ctx->runner->frameCount,ctx->runner->currentRoomIndex);
    string(output,dw->room.rooms[ctx->runner->currentRoomIndex].name);
    fprintf(output,",\"code_index\":%d,\"code_name\":",captured_code);string(output,code->name);
    fprintf(output,",\"event_type\":%d,\"event_subtype\":%d,\"event_object\":%d,\"self_id\":%u,\"self_object\":%d,\"global_id\":%u,\"self_context\":%d,\"other_context\":%d,\"locals_count\":%u,\"ops\":%u,\"wad\":%u,\"version\":[%u,%u,%u,%u],\"words\":[",
        ctx->currentEventType,ctx->currentEventSubtype,ctx->currentEventObjectIndex,ctx->currentInstance->instanceId,
        ctx->currentInstance->objectIndex,ctx->globalScopeInstance->instanceId,ctx->selfId,ctx->otherId,code->localsCount,ops,
        dw->gen8.wadVersion,dw->detectedFormat.major,dw->detectedFormat.minor,dw->detectedFormat.release,dw->detectedFormat.build);
    const unsigned char *bytes=dw->bytecodeBuffer + code->bytecodeAbsoluteOffset-dw->bytecodeBufferBase;
    for(unsigned i=0;i<code->length/4;i++){unsigned w;memcpy(&w,bytes+4*i,4);fprintf(output,"%s%u",i?",":"",w);}
    fprintf(output,"],\"maps_before\":[");
    map_json(NULL,self_keys,self_cap,self_count);fputc(',',output);
    map_json(NULL,global_keys,global_cap,global_count);fputc(',',output);local_json(NULL);
    fprintf(output,"],\"maps_after\":[");
    map_json(&ctx->currentInstance->selfVars,NULL,ctx->currentInstance->selfVars.capacity,ctx->currentInstance->selfVars.count);fputc(',',output);
    map_json(&ctx->globalScopeInstance->selfVars,NULL,ctx->globalScopeInstance->selfVars.capacity,ctx->globalScopeInstance->selfVars.count);fputc(',',output);
    local_json(ctx->codeLocalsSlotMaps?&ctx->codeLocalsSlotMaps[captured_code]:NULL);
    fprintf(output,"],\"variables\":[");
    for(unsigned i=0;i<nrefs;i++) {
        Variable *v=&dw->vari.variables[refs[i].index];
        if(i)fputc(',',output);fprintf(output,"{\"index\":%u,\"id\":%d,\"scope\":%d,\"builtin\":%d,\"name\":",refs[i].index,v->varID,v->instanceType,v->builtinVarId);
        string(output,v->name);fputc('}',output);
    }
    fprintf(output,"],\"before\":");refs_json(ctx,false);
    fprintf(output,",\"after\":");refs_json(ctx,true);
    fprintf(output,",\"return\":");value(output,result);
    fprintf(output,",\"builtin_io\":[");
    for(unsigned i=0;i<nio;i++) {Io *r=&ios[i];
        fprintf(output,"%s[%d,%d,%d,%d,",i?",":"",r->write,r->id,r->instance,r->index);value(output,r->value);
        fprintf(output,",[");for(int j=0;j<r->nargs;j++){if(j)fputc(',',output);value(output,r->args[j]);}
        fprintf(output,"]]");
    }
    fprintf(output,"],\"keyboard\":[");
    for(unsigned mode=0;mode<3;mode++) {
        if(mode)fputc(',',output);fputc('[',output);bool first=true;
        const bool *keys=mode==0?ctx->runner->keyboard->keyDown:mode==1?ctx->runner->keyboard->keyPressed:ctx->runner->keyboard->keyReleased;
        for(unsigned key=0;key<GML_KEY_COUNT;key++)if(keys[key]){fprintf(output,"%s%u",first?"":",",key);first=false;}
        fputc(']',output);
    }
    fprintf(output,"],\"functions\":[");
    bool first_fn=true;
    for(unsigned i=0;i<nio;i++)if(ios[i].write==2){
        if(!first_fn)fputc(',',output);first_fn=false;
        fprintf(output,"[%d,",ios[i].id);string(output,dw->func.functions[ios[i].id].name);fputc(']',output);
    }
    fprintf(output,"]}\n");fflush(output);
}
RValue VM_executeCode_original(VMContext *ctx,int32_t index);
RValue VM_executeCode(VMContext *ctx,int32_t index) {
    bool record=battle_capture_begin(ctx,index);
    RValue result=VM_executeCode_original(ctx,index);
    if(record)battle_capture_end(ctx,result);
    return result;
}
RValue VMBuiltins_getVariable_original(VMContext *,Instance *,int16_t,const char *,int32_t);
RValue VMBuiltins_getVariable(VMContext *ctx,Instance *inst,int16_t id,const char *name,int32_t index) {
    RValue v=VMBuiltins_getVariable_original(ctx,inst,id,name,index);io(false,ctx,inst,id,index,v);return v;
}
void VMBuiltins_setVariable_original(VMContext *,Instance *,int16_t,const char *,RValue,int32_t);
void VMBuiltins_setVariable(VMContext *ctx,Instance *inst,int16_t id,const char *name,RValue v,int32_t index) {
    io(true,ctx,inst,id,index,v);VMBuiltins_setVariable_original(ctx,inst,id,name,v,index);
}
