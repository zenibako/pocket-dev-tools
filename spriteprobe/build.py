#!/usr/bin/env python3
"""Compile probe-only generated adaptations; frozen runner inputs stay intact."""
import argparse,importlib.util,json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import capture
spec=importlib.util.spec_from_file_location('framebuild',ROOT/'fullframe/build.py');base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)


def build(game,variant,compiler):
    config=json.loads((ROOT/'experiment.json').read_text());dest=ROOT/'build/fullframe'/game/variant;dest.mkdir(parents=True,exist_ok=True)
    renderer=(capture.SRC/'sw/sw_renderer.c').read_text()
    lo=renderer.index('void swrSpriteCostProbe(');hi=renderer.index('\n#ifdef SW_DRAW_PROFILE\n// Times each kind',lo)
    probe=renderer[lo:hi]
    probe=capture.once(probe,'#ifdef SW_DRAW_PROFILE','#if defined(SW_DRAW_PROFILE) || defined(SWR_SPRITE_PROBE)')
    # The original older measured probe selected a 40x40 sprite. Current grid
    # selection is also available and explicitly recorded, never silently guessed.
    if config['selection']=='40x40':
        probe=capture.once(probe,'    int32_t sprite = -1;','    swrProbeGridSprite = -2; // probe adapter: force the documented 40x40 fallback\n    int32_t sprite = -1;')
    probe=capture.once(probe,'        uint64_t start = nowNanos();','        sprite_probe_begin(stage, renderer, sprite, calls, *width, *height, *path);')
    probe=capture.once(probe,'        nanos[stage] = (uint32_t) ((nowNanos() - start) / (uint64_t) calls);','        sprite_probe_end(renderer);')
    probe=capture.once(probe,'    uint64_t start = nowNanos();','    sprite_probe_begin(7, renderer, sprite, calls, *width, *height, *path);')
    probe=capture.once(probe,'    *outside = (uint32_t) ((nowNanos() - start) / (uint64_t) calls);','    sprite_probe_end(renderer);')
    renderer='#include "sprite_probe.h"\n'+renderer[:lo]+probe+renderer[hi:]
    (dest/'probe_renderer.c').write_text(renderer)
    (dest/'probe_drawing.c').write_text((capture.SRC/'sw/sw_drawing.c').read_text())
    header=(capture.SRC/'sw/sw_call_notes.h').read_text()
    header=capture.once(header,'#ifdef SW_DRAW_PROFILE','#if defined(SW_DRAW_PROFILE) || defined(SWR_SPRITE_PROBE)')
    (dest/'sw_call_notes.h').write_text(header)
    (dest/'sprite_probe.h').write_text((ROOT/'spriteprobe/probe.h').read_text())
    runtime=(ROOT/'fullframe/runtime.c').read_text();lo=runtime.index('void frame_begin(');hi=runtime.index('extern char __frame_heap_start',lo)
    runtime=runtime[:lo]+(ROOT/'spriteprobe/runtime.c').read_text()+'\n'+runtime[hi:]
    (ROOT/'fullframe/runtime.c').write_text(runtime)
    p=ROOT/'fullframe/frame.h';p.write_text(p.read_text().replace('frame_expected[3][8]','frame_expected[24][8]'))
    p=ROOT/'fullframe/bridge.c';p.write_text(p.read_text().replace('frame_expected[3][8]','frame_expected[24][8]'))
    original_sources=base.sources
    base.sources=lambda:[dest/'probe_renderer.c' if p==capture.SRC/'sw/sw_renderer.c' else dest/'probe_drawing.c' if p==capture.SRC/'sw/sw_drawing.c' else p for p in original_sources()]
    original_flags=base.port_flags
    base.port_flags=lambda g,d:[flag for flag in original_flags(g,d) if flag not in ['-DSW_DRAW_PROFILE','-DENABLE_VM_GML_PROFILER']]+['-DSWR_SPRITE_PROBE','-I'+str(capture.SRC/'sw')]
    base.build(game,variant,compiler)
    metadata=json.loads((dest/'build.json').read_text())
    tracked=[dest/'sw_call_notes.h',dest/'sprite_probe.h',ROOT/'spriteprobe/build.py',ROOT/'spriteprobe/runtime.c',ROOT/'spriteprobe/probe.h']
    metadata['sources'].update({str(p.relative_to(ROOT)):capture.sha(p) for p in tracked})
    metadata['workload']='sprite-probe';metadata['profiling']='renderer and GML disabled; stop/path hooks retained independently'
    (dest/'build.json').write_text(json.dumps(metadata,indent=2)+'\n')
    # Reject accidental profiler inclusion and in-loop tracing in the actual ELF.
    import subprocess,re
    symbols=subprocess.check_output([compiler.removesuffix('gcc')+'nm',str(dest/'program.elf')],text=True)
    for name in ['SWRenderer_profDrawSprite','swrNoteKeyed','frame_tick','frame_event']:
        if re.search(r'\b'+name+r'$',symbols,re.M):raise RuntimeError('Probe retained unwanted profiler/trace symbol: '+name)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--game',required=True);p.add_argument('--variant',required=True);p.add_argument('--compiler',default='riscv64-unknown-elf-gcc');a=p.parse_args();build(a.game,a.variant,a.compiler)
