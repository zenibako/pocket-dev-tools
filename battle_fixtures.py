#!/usr/bin/env python3
"""Emit freestanding replay tables only from verified capture manifests."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def captures():
    result=[]
    for game in ['undertale','deltarune']:
        folder=ROOT/'captures'/game
        manifest=json.loads((folder/'manifest.json').read_text())
        for name,sha in manifest['captures'].items():
            path=folder/name
            if digest(path)!=sha:raise RuntimeError('Capture changed: '+str(path))
            r=json.loads(path.read_text())
            if r['schema']!=1 or r['game']!=game:raise RuntimeError('Unsupported capture')
            r['fixture_name']=f'{game}_{r["phase"]}_{r["code_name"]}'
            r['capture_path']=str(path.relative_to(ROOT));r['capture_sha256']=sha
            result.append(r)
    return result

def oracle_hash(r):
    words=list(r['return'])
    for ref in r['after']:words.extend(ref[:3]+ref[3])
    for m in r['maps_after']:
        words.append(m['count'])
        if 'keys' in m:words.extend(m['keys'])
        else:
            for pair in m['entries']:words.extend(pair)
    h=2166136261
    for w in words:h=((h^(w&0xffffffff))*16777619)&0xffffffff
    return h

def generate():
    records=captures();out=['/* Generated from local captures. Do not publish game bytecode. */']
    def array(ctype,name,rows):
        out.append(f'static {ctype} {name}[] = {{'+','.join(rows or ['0'])+'};')
    def val(v):return '{'+','.join(str(x)+'u' for x in v)+'}'
    for game in ['undertale','deltarune']:
        group=[r for r in records if r['game']==game];vars={};fns={}
        for r in group:
            for v in r['variables']:
                index=v['index']
                if index in vars and vars[index]!=v:raise RuntimeError('Variable metadata conflict')
                vars[index]=v
            for index,name in r['functions']:fns[index]=name
        out.append(f'static Variable vars_{game}[{max(vars,default=0)+1}] = {{')
        for index,v in sorted(vars.items()):out.append(f'[{index}]={{.name={json.dumps(v["name"])},.varID={v["id"]},.instanceType={v["scope"]},.builtinVarId={v["builtin"]}}},')
        out.append('};')
        for index in sorted(fns):out.append(f'static RValue fn_{game}_{index}(VMContext *c,RValue *a,int32_t n){{return battle_replay_function(c,{index},a,n);}}')
        out.append(f'static Function functions_{game}[{max(fns,default=0)+1}]={{')
        for index,name in sorted(fns.items()):out.append(f'[{index}]={{.name={json.dumps(name)}}},')
        out.append('};')
        out.append(f'static FuncCallCache cache_{game}[{max(fns,default=0)+1}]={{')
        for index in sorted(fns):out.append(f'[{index}]={{.builtin=(void*)fn_{game}_{index},.scriptCodeIndex=-1}},')
        out.append('};')
    initializers=[]
    for i,r in enumerate(records):
        prefix=f'b{i}'
        array('const uint32_t',prefix+'_words',[str(w)+'u' for w in r['words']])
        for stage in ['before','after']:
            array('const BattleRef',prefix+'_'+stage,['{'+','.join(map(str,x[:3]))+','+val(x[3])+'}' for x in r[stage]])
            for j,m in enumerate(r['maps_'+stage]):
                key=prefix+'_'+stage+'_map'+str(j)
                if 'keys' in m:array('const int32_t',key,list(map(str,m['keys'])))
                else:array('const IntIntEntry',key,['{'+str(k)+','+str(v)+'u}' for k,v in m['entries']])
        for j,io in enumerate(r['builtin_io']):
            if io[5]:array('const BattleValue',prefix+'_args'+str(j),[val(v) for v in io[5]])
        array('const BattleIo',prefix+'_io',['{'+','.join(map(str,x[:4]))+','+val(x[4])+','+str(len(x[5]))+','+(prefix+'_args'+str(j) if x[5] else 'NULL')+'}' for j,x in enumerate(r['builtin_io'])])
        fields=['.name='+json.dumps(r['fixture_name']),'.wad='+str(r['wad']),'.version={'+','.join(map(str,r['version']))+'}',
                '.frame='+str(r['frame']),'.ops='+str(r['ops']),'.word_count='+str(len(r['words'])),'.words='+prefix+'_words',
                '.before='+prefix+'_before','.after='+prefix+'_after','.ref_count='+str(len(r['before'])),
                '.io='+prefix+'_io','.io_count='+str(len(r['builtin_io'])),'.result='+val(r['return']),'.hash='+str(oracle_hash(r))+'u',
                '.vars=vars_'+r['game'],'.var_count=sizeof(vars_'+r['game']+')/sizeof(Variable)',
                '.functions=functions_'+r['game'],'.function_count=sizeof(functions_'+r['game']+')/sizeof(Function)', '.cache=cache_'+r['game']]
        for name in ['self_id','global_id','self_object','self_context','other_context','event_type','event_subtype','event_object','locals_count']:fields.append('.'+name+'='+str(r[name]))
        for stage in ['before','after']:
            maps=[]
            for j,m in enumerate(r['maps_'+stage]):
                data=m.get('keys',m.get('entries'));pointer=prefix+'_'+stage+'_map'+str(j)
                maps.append('{.capacity='+str(len(data))+',.count='+str(m['count'])+',.'+('keys' if 'keys' in m else 'entries')+'='+pointer+'}')
            fields.append('.maps_'+stage+'={'+','.join(maps)+'}')
        initializers.append('{'+','.join(fields)+'}')
    array('const BattleFixture','battle_fixtures',initializers)
    (ROOT/'battle_fixtures.inc').write_text('\n'.join(out)+'\n')
    (ROOT/'captures/replay-manifest.json').write_text(json.dumps([dict(index=i,name=r['fixture_name'],game=r['game'],phase=r['phase'],frame=r['frame'],room=r['room'],code_name=r['code_name'],ops=r['ops'],code_bytes=len(r['words'])*4,hash=f'{oracle_hash(r):08x}',capture=r['capture_path'],sha256=r['capture_sha256']) for i,r in enumerate(records)],indent=2)+'\n')
    return records
if __name__=='__main__':generate()
