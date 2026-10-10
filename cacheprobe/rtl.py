#!/usr/bin/env python3
"""Build an observer-only wrapper around an existing full-frame simulator."""
import argparse
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import harness
from pipeline_fields import FIELDS


def build(jobs):
    leaf=ROOT/'build/rtl'
    full=ROOT/'build/fullframe/rtl'
    dest=ROOT/'build/cacheprobe'
    dest.mkdir(parents=True,exist_ok=True)
    signals=(ROOT/'cacheprobe/signals.vh').read_text()
    declarations=[]
    for name in ['i','d']:
        for field,width in [('arvalid',1),('arready',1),('araddr',32),('arid',2),
                            ('arlen',8),('rvalid',1),('rready',1),('rid',2),('rlast',1),('rresp',2)]:
            declarations.append('output wire '+(f'[{width-1}:0] ' if width>1 else '')+f'cp_{name}_{field},')
    for name,width in [('i_hold',1),('i_pc',32),('i_miss',1),('i_resume',1),('i_miss_pc',32),('d_wait',1),('commit',1),
                       ('clock_cmd',1),('clock_pc',32),('clock_latch',1),('counter',32)]:
        declarations.append('output wire '+(f'[{width-1}:0] ' if width>1 else '')+'cp_'+name+',')
    for name,width in FIELDS.items():
        declarations.append('output wire '+(f'[{width-1}:0] ' if width>1 else '')+'cp_'+name+',')
    top=(leaf/'top.v').read_text()
    top=harness.once(top,'module tb_system (','module tb_system (\n`ifdef HARNESS_CACHE_PROFILE\n'+
                     '\n'.join(declarations)+'\n`endif\n')
    top=harness.once(top,'endmodule','`ifdef HARNESS_CACHE_PROFILE\n'+signals+'\n`endif\nendmodule')
    (dest/'top.v').write_text(top)
    cpp=(full/'main.cpp').read_text()
    cpp=harness.once(cpp,'static Vtb_system *tb;',
        '#include "'+str(ROOT/'cacheprobe/monitor.hpp')+'"\nstatic CacheMonitor cache_monitor;\nstatic Vtb_system *tb;')
    cpp=harness.once(cpp,'    tb = new Vtb_system;', '    tb = new Vtb_system;\n    cache_monitor.init();')
    cpp=harness.once(cpp,'        tick_half(false);\n        const bool aw_take',
                     '        tick_half(false);\n        cache_monitor.sample(*tb);\n        const bool aw_take')
    cpp=harness.once(cpp,'    uint32_t final_pc =','    cache_monitor.finish();\n    uint32_t final_pc =')
    (full/'main.cpp').write_text(cpp)
    mk=(leaf/'test.mk').read_text()
    mk+='\nSYSTEM_SDRAM_SRCS := $(subst '+str(leaf/'top.v')+','+str(dest/'top.v')+',$(SYSTEM_SDRAM_SRCS))\n'
    (dest/'test.mk').write_text(mk)
    definitions=json.loads((leaf/'rtl.json').read_text())['definitions']
    command=['make','-f',dest/'test.mk',dest/'obj/Vtb_system',
             f'SYSTEM_SDRAM_DIR={dest}/obj',f'SYSTEM_SDRAM_CPP={full}/main.cpp',
             f'VEXII_MISTER={harness.CPU}',f'VERILATOR=verilator -j {jobs} '+
             ' '.join('+define+'+x for x in definitions+['HARNESS_CACHE_PROFILE'])]
    harness.run(command,dest/'compile.log',cwd=harness.OS/'src/fpga/test')
    shutil.copy2(dest/'obj/Vtb_system',full/'obj/Vtb_system')
    metadata=json.loads((full/'rtl.json').read_text())
    metadata.update(simulator_sha256=harness.digest(full/'obj/Vtb_system'),
                    source_sha256=harness.digest(full/'main.cpp'))
    metadata['cache_probe']=dict(define='HARNESS_CACHE_PROFILE',runtime_switch='CACHE_PROFILE',
        cpu_parameter_changes={},cpu_sha256=harness.digest(harness.CPU),
        top_sha256=harness.digest(dest/'top.v'),
        observer_sources={str(p.relative_to(ROOT)):harness.digest(p) for p in (ROOT/'cacheprobe').iterdir() if p.is_file()},
        source='CPU-side AXI handshakes, internal cache waiters, architectural commit pulse, exact MMIO latch')
    harness.save(full/'rtl.json',metadata)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--jobs',type=int,default=4)
    build(parser.parse_args().jobs)
