#!/usr/bin/env python3
"""Build the real port with complete-frame hooks; run only inside the private container."""
from pathlib import Path
import argparse,json,subprocess,sys,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));import capture
SRC=capture.SRC

def once(s,a,b):return capture.once(s,a,b)
def build(game,variant):
 d=ROOT/'build/fullframe'/game/variant;d.mkdir(parents=True,exist_ok=True)
 meta=json.loads((ROOT/'build/capture'/game/'build.json').read_text())
 paths=[ROOT/p for p in meta['sources']]
 paths=[p for p in paths if p not in [ROOT/'capture/capture_hooks.c',ROOT/'capture/sdk/of_sdl2.c']]
 paths=[SRC/'vm.c' if p.name=='vm.c' else SRC/'vm_builtins.c' if p.name=='vm_builtins.c' else p for p in paths]
 loop=(SRC/'loop.c').read_text()
 loop=once(loop,'            uint64_t frameStartNow = nowNanos();','            frame_begin(runner);\n            uint64_t frameStartNow = nowNanos();')
 loop=once(loop,'            lastFrameTime = nowNanos();\n        }','            lastFrameTime = nowNanos();\n            frame_end(runner);\n        }')
 (d/'loop.c').write_text('#include "frame.h"\n'+loop)
 vm=(SRC/'vm.c').read_text()
 # OF_PC selects the headless platform, but the executable still targets RV32
 # and must retain the SDK's BRAM section attribute for this variant.
 if variant=='bram':vm=once(vm,'#if defined(UT_FAST_LOOP) && !defined(OF_PC)','#if defined(UT_FAST_LOOP)')
 vm=once(vm,'        uint32_t instr = BinaryUtils_readUint32Aligned(bytecodeBase + ip);','        uint32_t instr = BinaryUtils_readUint32Aligned(bytecodeBase + ip);\n        frame_tick(ctx,ip,instr);')
 vm=once(vm,'RValue VM_executeCode(VMContext* ctx, int32_t codeIndex) {','RValue VM_executeCode(VMContext* ctx, int32_t codeIndex) {\n    frame_event(codeIndex);')
 (d/'vm.c').write_text('#include "frame.h"\n'+vm)
 main=(capture.PORT/'main.c').read_text().replace('int main(int argc, char **argv)', 'int game_main(int argc, char **argv)')
 (d/'main.c').write_text(main)
 paths=[d/'loop.c' if p==SRC/'loop.c' else d/'vm.c' if p==SRC/'vm.c' else d/'main.c' if p==capture.PORT/'main.c' else p for p in paths]
 paths += [ROOT/'fullframe'/p for p in ['bridge.c','platform.c','runtime.c','start.S']]
 includes=[capture.PORT,capture.PORT/'platform',SRC,SRC/'sw',SRC/'image',SRC/'video',SRC/'debug_font',ROOT/'fullframe',ROOT/'inputs/sdk/include',*[capture.VENDOR/p for p in ['stb/ds','stb/image','stb/vorbis','bzip2','sha1','md5','base64','miniz']]]
 flags=['-march=rv32imafc_zicsr_zifencei','-mabi=ilp32f','-O2','-g','-ffunction-sections','-fdata-sections','-falign-functions=64','-falign-loops=64','-fno-tree-loop-distribute-patterns','-nostdinc','-nostdlib','-nostartfiles','-ffreestanding','-isystem',str(ROOT/'inputs/sdk/musl/include')]
 defines=['OF_PC','USE_FLOAT_REALS','NO_RVALUE_INT64','ENABLE_WAD'+str(capture.SCENARIOS[game]['wad']),'ENABLE_SW_RENDERER','PIXEL_SIZE=16','SW_DRAW_PROFILE','PLATFORM_BUSY_TICK','ENABLE_VM_GML_PROFILER','BUTTERSCOTCH_VIDEO_NULL','USE_PLATFORM_AUDIO','USE_PLATFORM_FILE_SYSTEM','SW_PLATFORM_FRAMEBUFFER','DATAWIN_LOG_CHUNKS','BUTTERSCOTCH_COMMIT_HASH="fullframe"','BUTTERSCOTCH_COMMIT_DATE="snapshot"','UT_GAME_NAME="'+game+'"','UT_SAVE_SLOT_FILE="'+game+'_0.sav"','UT_LOG_SLOT_FILE="'+game+'_1.sav"','UT_BUILD_NOTE="isolated complete frames"','FRAME_TARGET='+('2399' if game=='undertale' else '3322'),'TEXTURE_CACHE_BYTES=(40u*1024u*1024u)','TEXTURE_CACHE_RESERVE_BYTES=(4u*1024u*1024u)']
 if game=='deltarune':defines+=['UT_GAME_DELTARUNE']
 if variant=='bram':defines+=['UT_FAST_LOOP']
 wraps=['fopen','printf','fprintf','vfprintf','vprintf','puts','fputs','putchar','fwrite']
 cmd=['riscv64-unknown-elf-gcc',*flags,*['-D'+x for x in defines],*['-I'+str(p) for p in includes],*map(str,paths),'-Wl,-T,'+str(ROOT/'fullframe/link.ld'),'-Wl,--gc-sections','-Wl,-Map,'+str(d/'program.map'),*['-Wl,--wrap='+x for x in wraps],'-L'+str(ROOT/'inputs/sdk/musl/lib'),'-lc','-lm','-lgcc','-o',str(d/'program.elf')]
 print('Building complete frames',game,variant,flush=True)
 with (d/'compile.log').open('w') as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
 (d/'build.json').write_text(json.dumps(dict(command=cmd,sources={str(p.relative_to(ROOT)):capture.sha(p) for p in [*paths,ROOT/'fullframe/frame.h',ROOT/'fullframe/link.ld',ROOT/'fullframe/build.py']}),indent=2)+'\n')
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--game',choices=['undertale','deltarune']);ap.add_argument('--variant',choices=['sdram','bram'],default='sdram');a=ap.parse_args()
 for g in ([a.game] if a.game else ['undertale','deltarune']):build(g,a.variant)
