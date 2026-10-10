#!/usr/bin/env python3
"""Build an observing desktop runner and capture the existing benchmark battle route."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
SRC = ROOT / 'inputs/butterscotch/src'
VENDOR = ROOT / 'inputs/butterscotch/vendor'
PORT = SRC / 'openfpga'
BUILD = ROOT / 'build/capture'
SCENARIOS = {
    'undertale': dict(wad=16, windows='2388-2402', stop=2405, phases=[('flowey',2388,2402)]),
    'deltarune': dict(wad=17, windows='3323-3327', stop=3330,
                      phases=[('dodging',3323,3327)])}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def once(text, old, new):
    if text.count(old)!=1: raise RuntimeError('Capture hook anchor changed: '+old)
    return text.replace(old,new)


def build(game):
    dest=BUILD/game
    dest.mkdir(parents=True,exist_ok=True)
    vm=once((SRC/'vm.c').read_text(),'RValue VM_executeCode(VMContext* ctx, int32_t codeIndex) {',
            'RValue VM_executeCode_original(VMContext* ctx, int32_t codeIndex) {')
    vm=once(vm,'        uint32_t instr = BinaryUtils_readUint32Aligned(bytecodeBase + ip);',
            '        battle_capture_tick(ctx);\n        uint32_t instr = BinaryUtils_readUint32Aligned(bytecodeBase + ip);')
    vm=once(vm,'        RValue result = builtin(ctx, args, argCount);',
            '        RValue result = battle_capture_builtin(ctx, funcIndex, cache->builtin, args, argCount);')
    (dest/'vm.c').write_text('#include "capture_hooks.h"\n'+vm)
    builtins=(SRC/'vm_builtins.c').read_text()
    builtins=once(builtins,'RValue VMBuiltins_getVariable(', 'RValue VMBuiltins_getVariable_original(')
    builtins=once(builtins,'void VMBuiltins_setVariable(', 'void VMBuiltins_setVariable_original(')
    (dest/'vm_builtins.c').write_text(builtins)
    sources=[PORT/'main.c',*[PORT/'platform'/n for n in ['of_platform.c','of_diag.c','of_log.c','of_perf.c',
             'of_audio_system.c','ut_bench.c','ut_strings.c','ut_save_fs.c','ut_native.c']],
             *[p for p in sorted(SRC.glob('*.c')) if p.name not in ['vm.c','vm_builtins.c']],
             dest/'vm.c',dest/'vm_builtins.c',ROOT/'capture/capture_hooks.c',
             *sorted((SRC/'sw').glob('*.c')),*sorted((SRC/'image').glob('*.c')),
             *sorted((SRC/'debug_font').glob('*.c')),SRC/'video/null_video.c',SRC/'embedded/stb_impl.c',
             *sorted((VENDOR/'bzip2').glob('*.c')),
             *[VENDOR/p for p in ['sha1/sha1.c','md5/md5.c','base64/base64.c','miniz/miniz.c','miniz/miniz_tdef.c','miniz/miniz_tinfl.c']],
             SRC/'physics/physics.c',SRC/'physics/disabled/physics_disabled.c',ROOT/'capture/sdk/of_sdl2.c']
    includes=[PORT/'platform',SRC,SRC/'sw',SRC/'image',SRC/'video',SRC/'debug_font',
              *[VENDOR/p for p in ['stb/ds','stb/image','stb/vorbis','bzip2','sha1','md5','base64','miniz']],
              ROOT/'capture',ROOT/'inputs/sdk/include']
    flags=['-DOF_PC','-O2','-g','-DENABLE_WAD'+str(SCENARIOS[game]['wad']),'-DENABLE_SW_RENDERER','-DPIXEL_SIZE=16',
           '-DUSE_FLOAT_REALS','-DNO_RVALUE_INT64','-DSW_DRAW_PROFILE','-DPLATFORM_BUSY_TICK','-DENABLE_VM_GML_PROFILER',
           '-DBUTTERSCOTCH_VIDEO_NULL','-DUSE_PLATFORM_AUDIO','-DUSE_PLATFORM_FILE_SYSTEM','-DSW_PLATFORM_FRAMEBUFFER',
           '-DDATAWIN_LOG_CHUNKS','-DBUTTERSCOTCH_COMMIT_HASH="capture"','-DBUTTERSCOTCH_COMMIT_DATE="snapshot"',
           '-DUT_GAME_NAME="'+game+'"','-DUT_SAVE_SLOT_FILE="'+game+'_0.sav"','-DUT_LOG_SLOT_FILE="'+game+'_1.sav"',
           '-DUT_BUILD_NOTE="isolated capture"',*(['-DUT_GAME_DELTARUNE'] if game=='deltarune' else [])]
    sdl=subprocess.run(['pkg-config','--cflags','--libs','sdl2'],capture_output=True,text=True,check=True).stdout.split()
    command=['clang',*flags,*['-I'+str(p) for p in includes],*map(str,sources),*sdl,'-lm','-o',str(dest/'runner')]
    print('Building observing runner:',game,flush=True)
    with (dest/'build.log').open('w') as log:
        subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
    (dest/'build.json').write_text(json.dumps(dict(command=command,sources={str(p.relative_to(ROOT)):sha(p) for p in sources}),indent=2)+'\n')


def capture(game):
    dest=BUILD/game
    data_dir=PORT if game=='undertale' else PORT/'games/deltarune'
    for repeat in range(2):
        run_dir=dest/f'run-{repeat}'
        run_dir.mkdir(exist_ok=True)
        # Only read-only asset links, with saves/output confined to a new run directory.
        for name in ['data.win','textures.bin','music.bin','audiogroup1.dat','lang_en.json','music']:
            source=data_dir/name
            if source.exists() and not (run_dir/name).exists(): (run_dir/name).symlink_to(source)
        path=dest/f'raw-{repeat}.jsonl'
        env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',DYLD_FALLBACK_LIBRARY_PATH='/opt/homebrew/lib',
                 UT_NOFLIP='1',UT_UNCAPPED='1',UT_NO_NATIVE='1',UT_SEED='7',UT_EXIT_FRAME=str(SCENARIOS[game]['stop']+100),
                 HARNESS_CAPTURE_GAME=game,HARNESS_CAPTURE_FRAMES=SCENARIOS[game]['windows'],HARNESS_CAPTURE_PATH=str(path),
                 UT_DUMP_FRAME=str(SCENARIOS[game]['stop']),UT_DUMP_PATH=str(dest/f'scene-{repeat}.ppm'))
        # An inherited debugging variable must not change the replay or touch other paths.
        for name in list(env):
            if name.startswith('UT_') and name not in ['UT_NOFLIP','UT_UNCAPPED','UT_NO_NATIVE','UT_SEED','UT_EXIT_FRAME','UT_DUMP_FRAME','UT_DUMP_PATH']:
                del env[name]
        print('Capturing',game,'repeat',repeat,flush=True)
        with (dest/f'run-{repeat}.log').open('w') as log:
            subprocess.run([str(dest/'runner'),'--bench'],cwd=run_dir,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=300,check=True)
    records=[json.loads(line) for line in (dest/'raw-0.jsonl').read_text().splitlines()]
    again={json.dumps(r,sort_keys=True) for r in map(json.loads,(dest/'raw-1.jsonl').read_text().splitlines())}
    stable=[r for r in records if json.dumps(r,sort_keys=True) in again]
    chosen=[]
    for phase,lo,hi in SCENARIOS[game]['phases']:
        pool=[r for r in stable if lo<=r['frame']<=hi]
        if game=='deltarune':
            pool=[r for r in pool if any(n in r['code_name'] for n in ['obj_heart_', 'obj_grazebox_', 'obj_growtangle_', 'obj_shake_', 'obj_battle', 'obj_attack', 'obj_bullet'])]
        seen=set()
        for r in sorted(pool,key=lambda r:(-r['ops'],-len(r['words']),r['frame'],r['self_id'])):
            if r['code_name'] in seen: continue
            seen.add(r['code_name']);r['phase']=phase;chosen.append(r)
            if len(seen)==3:break
        if not seen: raise RuntimeError('No reproducible numeric leaf events in '+game+'/'+phase)
    output=ROOT/'captures'/game
    output.mkdir(parents=True,exist_ok=True)
    selected=[]
    for i,r in enumerate(chosen):
        path=output/f'{i:02d}-{r["phase"]}.json'
        path.write_text(json.dumps(r,indent=2)+'\n');selected.append(path)
    manifest=dict(game=game,scenario=SCENARIOS[game],seed=7,source_data_sha256=sha(data_dir/'data.win'),
                  snapshot_sha256=sha(ROOT/'input-manifest.json'),runner_sha256=sha(dest/'runner'),
                  hook_sha256=sha(ROOT/'capture/capture_hooks.c'),build=json.loads((dest/'build.json').read_text()),
                  repeat_capture_equal_records=len(stable),observed_records=len(records),
                  scene_hashes=[sha(dest/f'scene-{i}.ppm') for i in range(2)],
                  captures={p.name:sha(p) for p in selected})
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(game,'selected',[(r['phase'],r['code_name'],r['ops'],r['room']) for r in chosen],flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('action',choices=['build','capture','all'])
    ap.add_argument('--game',choices=list(SCENARIOS))
    args=ap.parse_args()
    for game in ([args.game] if args.game else list(SCENARIOS)):
        if args.action in ['build','all']:build(game)
        if args.action in ['capture','all']:capture(game)
