#!/usr/bin/env python3
"""Verify and report the profiling-disabled repeated sprite draw microprobe."""
import argparse,csv,json
from collections import Counter,defaultdict
from pathlib import Path
import cache_profile,cache_report,experiments,pipeline_report
from pipeline_analysis import BITS

STAGES={0:'whole inside draw',1:'renderer door',2:'texture found',3:'drawing entered',4:'clipped',5:'setup complete',6:'held layers flushed',7:'outside view'}


def analyze(record):
    config=record['case']['config']
    expected=dict(workload='sprite-probe',kind='timing',game='deltarune',mode='speed',profile='port',
                  renderer_profiling=False,gml_profiling=False,probe_calls=2000,probe_samples=24)
    if any(config.get(k)!=v for k,v in expected.items()):raise ValueError('Unexpected probe configuration')
    flags=record['case']['source_flags']
    if any(f in flags for f in ['-DSW_DRAW_PROFILE','-DENABLE_VM_GML_PROFILER']):raise ValueError('Profiling was not disabled')
    rows=record['case']['rows'];profile=record['profile'];groups=defaultdict(list)
    if len(rows)!=24 or len(profile['frames'])!=24:raise ValueError('Incomplete staged probe')
    for f,row in zip(profile['frames'],rows):
        values=row['oracle'];stage=values[7]>>16
        if stage!=[6,5,4,3,2,1,0,7][f['index']%8] or values[0]!=f['index'] or values[4]!=2000:
            raise ValueError('Bad probe sample metadata')
        groups[stage].append(f)
    if set(groups)!=set(STAGES) or any(len(v)!=3 for v in groups.values()):raise ValueError('Incomplete staged probe')
    attribution=cache_profile.Attribution(cache_profile.symbols(Path(record['evidence']['result']).parent/'program.elf'))
    pc_functions=defaultdict(lambda:defaultdict(Counter))
    sample_stage={f['index']:row['oracle'][7]>>16 for f,row in zip(profile['frames'],rows)}
    for row in csv.reader((Path(record['evidence']['result']).parent/'cache-profile.csv').read_text().splitlines()):
        if not row or row[0] not in ['S','T']:continue
        index,pc,value,count=map(int,row[1:]);fn=pc_functions[sample_stage[index]][attribution.name(pc)]
        if row[0]=='T':fn['retired']+=count
        else:
            fn['dispatch_blocked']+=count
            for name in ['raw_dependency','load_dependency','fp_dependency','multiply_dependency','integer_divider','fp_divider','store_buffer_wait']:
                if value&(1<<BITS.index(name)):fn[name]+=count
    stages=[]
    for stage,frames in sorted(groups.items()):
        sub=dict(frames=frames,total_frame_cycles=sum(f['cycles'] for f in frames));summary=pipeline_report.summarize(sub)
        calls=6000
        stages.append(dict(stage=stage,name=STAGES[stage],frames=frames,summary=summary,calls=calls,
            cycles_per_call=summary['cycles']/calls,microseconds_per_call=summary['cycles']/calls/100,
            batch_cycles_per_call=[f['cycles']/2000 for f in frames],
            i_block_cycles=sum(f['i_block_cycles'] for f in frames),d_block_cycles=sum(f['d_block_cycles'] for f in frames),
            cache_union_cycles=sum(f['union_block_cycles'] for f in frames),
            refills={c:sum(f[c]['refill_count'] for f in frames) for c in ['I','D']},
            refill_distributions={c:cache_report.pooled_distribution(frames,c,'accepted_to_last_cycles') for c in ['I','D']},
            functions=sorted([dict(name=k,**v) for k,v in pc_functions[stage].items()],key=lambda f:(-f.get('retired',0),f['name']))))
    return stages


def markdown(record,stages,checks):
    c=record['case'];cfg=c['config'];table=cache_report.table
    out=['# Isolated sprite probe (perf/mirrored-blend)','',
         f"Pinned revision `{c['revision']}`. Deltarune Chapter 1, Speed, {cfg['selection']} selection, "
         f"{cfg['variant'].upper()} interpreter, quiet traffic. Compiler: `{c['compiler_version']}`. "
         'Renderer/GML profiling and VM tracing are disabled; independent stop/path hooks remain. '
         'All timings below are simulated at 100 MHz.','',
         'The current staged `swrSpriteCostProbe` is copied from the snapshot. It warms a sprite, then calls '
         '`Renderer_drawSprite` 2,000 times per stage in order 6,5,4,3,2,1,0,outside. The suite runs three '
         'times consecutively. Outside uses `(viewX - 10000, viewY + 60)`; inside uses '
         '`(viewX + 60, viewY + 60)`, frame 0 of the sprite. Audio top-ups are suppressed as in the original '
         'probe. This bypasses VM/GML dispatch.','',
         'The adapter enables only the probe’s compile-time stop/path gates while removing `SW_DRAW_PROFILE` '
         'and `ENABLE_VM_GML_PROFILER`. It replaces the probe’s two `nowNanos` calls around each batch with '
         'exact MMIO-counter interval hooks. Setup, output formatting, game-state/pixel validation and logs '
         'are outside each interval. The loop, call/return path and small boundary overhead remain measured; '
         'boundary overhead is amortized over 2,000 calls. No kernel clock/ecall cost is charged.','',
         'State/pixel hashing and UART logs run between batches, unlike the original device probe. '
         'They can evict cache contents and change predictor history before the next batch. This is '
         'an additional comparability limit even though those clocks are excluded. The observed refill '
         'counts and three batch means retain its effect rather than assuming it is absent.','',
         '## Per-call cost','',table(['Stage','Cycles/call','µs/call','Three batch means (cycles/call)','Retired/call','Native CPI','I block/call','D block/call','I/D refills (6,000 calls)'],
         [[s['name'],f"{s['cycles_per_call']:.3f}",f"{s['microseconds_per_call']:.3f}",', '.join(f'{v:.3f}' for v in s['batch_cycles_per_call']),
           f"{s['summary']['retired']/s['calls']:.3f}",f"{s['summary']['cycles_per_retired_instruction']:.3f}",
           f"{s['i_block_cycles']/s['calls']:.3f}",f"{s['d_block_cycles']/s['calls']:.3f}",f"{s['refills']['I']}/{s['refills']['D']}"] for s in stages]),'',
         'The three values are consecutive batch averages in a deterministic model, not physical-device '
         'variance or a per-call latency distribution. The first suite follows restoration with cold CPU '
         'caches, but the original warm draw occurs before its first measured batch.','',
         '## Pipeline observations','',
         'Values are cycles per call, averaged over all three batches. Rows overlap and can coexist with '
         'retirement; they must not be summed as causal lost cycles. Canonical retirement uses the ctrl5 '
         'CommitService event. Source dependency categories identify the waiting operand’s producer.','']
    sources=['raw_dependency','load_dependency','multiply_dependency','fp_dependency','fp_reservation','execute_freeze',
             'integer_divider','fp_divider','fp_sqrt','fp_to_int','int_to_fp','store_buffer_wait','uncached_io','csr','atomic','branch_recovery']
    out+=[table(['Observation']+[s['name'] for s in stages],[[name]+[f"{s['summary']['counts'][name]/s['calls']:.3f}" for s in stages] for name in sources]),'',
          'Disjoint no-retirement accounting follows the same explicit priority as the '
          '[full-frame pipeline report](../cacheprobe/PIPELINE-RESULTS.md): execute freeze, D wait, '
          'store-buffer wait, RAW, FP reservation, flush/fence interlocks, I block, branch recovery, '
          'then residual issue/candidate/frontend clocks. This assigns overlaps for presentation; it '
          'does not predict the saving from removing a source.','']
    keys=['retirement','execute_freeze','d_block','store_buffer_wait','raw_dependency','fp_reservation','flush_interlock','fence_interlock','i_block','branch_recovery','dispatch_without_retirement','candidate_other','frontend_or_pipeline_empty']
    out+=[table(['Exclusive clock category']+[s['name'] for s in stages],[[name]+[f"{s['summary']['exclusive_partition'].get(name,0)/s['calls']:.3f}" for s in stages] for name in keys]),'',
          '## Refill and branch distributions','']
    rows=[]
    for s in stages:
        for cache,d in s['refill_distributions'].items():
            rows.append([s['name'],cache,d['count'],f"{d.get('mean',0):.2f}" if d['count'] else '—',*[d.get(k,'—') for k in ['min','p50','p90','p99','max']]])
    out+=[table(['Stage','Cache','Refills','Mean cycles','Min','p50','p90','p99','Max'],rows),'']
    rows=[]
    for s in stages:
        p=s['summary'];d=p['branch_recovery_cycles'];rows.append([s['name'],f"{p['counts']['branches_resolved']/s['calls']:.3f}",f"{p['counts']['branch_mispredicts']/s['calls']:.3f}",f"{d.get('mean',0):.2f}" if d['count'] else '—',*[d.get(k,'—') for k in ['p50','p90','p99','max']]])
    out+=[table(['Stage','Branches/call','Mispredicts/call','Recovery mean cycles','p50','p90','p99','Max'],rows),'',
          'Refill latency is accepted AR through RLAST, inclusive, including speculative prefetch. Branch '
          'recovery is a firing direction/target correction through dispatch of its corrected target and '
          'includes overlapping waits. Full histograms and raw event hashes remain in private results.','',
          '## Culling code','']
    for number in [1,3,7]:
        s=next(s for s in stages if s['stage']==number)
        out+=[f"### {s['name']}",'',table(['Function','Retired/call','RAW/call','Load dependency/call','FP dependency/call','Multiply dependency/call','Dispatch blocked/call'],
            [[f['name'],*[f"{f.get(k,0)/s['calls']:.3f}" for k in ['retired','raw_dependency','load_dependency','fp_dependency','multiply_dependency','dispatch_blocked']]] for f in s['functions'][:20]]),'']
    door=next(s for s in stages if s['stage']==1);outside=next(s for s in stages if s['stage']==7)
    out+=['## Result and comparability','',
          f"The outside-view call costs {outside['cycles_per_call']:.3f} cycles ({outside['microseconds_per_call']:.3f} µs), "
          f"versus {door['cycles_per_call']:.3f} cycles at the renderer door. The difference is "
          f"{outside['cycles_per_call']-door['cycles_per_call']:.3f} cycles. Outside native CPI is "
          f"{outside['summary']['cycles_per_retired_instruction']:.3f}. Cache blocking occupies "
          f"{100*outside['cache_union_cycles']/outside['summary']['cycles']:.3f}% of its clocks. "
          'See the counters above for the actual waits; broad full-frame shares were not used to infer them.','',
          f"The door-to-outside difference contains {(outside['summary']['retired']-door['summary']['retired'])/outside['calls']:.3f} "
          'additional retired native instructions per call. Refills do not dominate this warmed repeated '
          'sprite path in this binary. The physical-device hypothesis remains undecided because the '
          'simulated timing is substantially smaller.','',
          'The device’s reported 19.87/19.56 µs results were from f42a23c with profiling compiled but per-draw '
          'timing/notes disabled at runtime. This requested build removes that profiling code entirely and '
          'uses a newer pinned branch revision. The same call geometry and 40×40 fallback are recorded, but '
          'exact device compiler/link layout and v0.7 CPU/runtime parity are unverified. The simulated '
          'numbers therefore reproduce the workload under these stated conditions, not a proven match '
          'to the physical 19.9 µs result.','',
          'The checkpoint is taken immediately before benchmark frame 3323, not after the entire 3,600-frame '
          'device benchmark. Selection `40x40` explicitly bypasses the newer last-grid-sprite preference to '
          'use the old probe’s fallback search. Renderer geometry is recorded below. The SDK’s 64-byte '
          'function/loop alignment is applied; native scripts follow the port build. Firmware services, '
          'allocator, virtual file access and deterministic game clock are harness substitutions. The '
          'cached framebuffer matters for drawn stages; culling writes no pixels. Audio mixing and physical '
          'SD/display scheduling are outside the probe. The CPU/cache RTL and parameters are unchanged.','',
          '## Verification and source references','',
          'Two captures have identical RAM/stack checkpoints, all 24 oracles and raw pixel/PCM artifacts. '
          'The regular replay and passive-observer replay must agree exactly on cycles and oracles; disabled '
          'and corrupted-oracle controls are hash-verified below. Producer hazard and complete freeze-source '
          'checks run on every observer sample. Frozen baseline inputs and earlier reports are retained. '
          'Only independently copied harness directories are mounted in Docker.','',
          'The active performance checkout advanced independently during this experiment; this task '
          'read Git objects for the pinned snapshot and issued no write or deployment command there.','',
          f"Source revision: `{c['revision']}`; source files `src/sw/sw_renderer.c:swrSpriteCostProbe`, "
          '`src/sw/sw_call_notes.h:SWR_PROBE_STOP`, `src/sw/sw_drawing.c:swrDrawSpriteInternal`. '
          'Generated adaptations are recorded in `build.json`; their tooling is '
          '[build.py](build.py), [runtime.c](runtime.c) and [sprite_probe.py](../sprite_probe.py). '
          'Counter definitions and pinned RTL source references are in '
          '[cacheprobe/README.md](../cacheprobe/README.md).','',
          f"Observer `{record['evidence']['observer_version']}`; ELF SHA-256 `{record['evidence']['elf_sha256']}`; "
          f"profile result SHA-256 `{record['evidence']['result_sha256']}`.",'',
          table(['Control','Result SHA-256'],[['corrupted oracle rejected' if v['negative_oracle_rejected'] else 'observer disabled, identical',v['result_sha256']] for v in checks]),'']
    summary=outside['summary']
    out+=['Outside-view instruction mix (retired instructions per call):','',
          table(['Instruction class','Retired/call'],[[name,f"{count/outside['calls']:.3f}"] for name,count in sorted(summary['instruction_mix'].items())]),'',
          f"The outside interval has {summary['no_retire_cycles']/outside['calls']:.3f} clocks per call without retirement. "
          'Its largest exclusive non-retirement categories are '+', '.join(
              f"{name}: {count/outside['calls']:.3f} cycles/call" for name,count in
              sorted(((k,v) for k,v in summary['exclusive_partition'].items() if k!='retirement'),key=lambda kv:-kv[1])[:4])+'. '
          'These are observations of this binary; they do not explain the remaining device/simulation timing gap.','']
    cap=json.loads((Path(record['evidence']['result']).parent/'capture.json').read_text())
    out+=['Geometry fields: sample, stage, sprite, width, height, viewX/Y/W/H, portW/H, scaleX/Y IEEE-754 bits.','',
          '```text',*cap['probe_settings'][:8],'```','']
    return '\n'.join(out).rstrip()+'\n'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--result',type=Path,required=True);p.add_argument('--checks',type=Path,nargs='+',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--markdown',type=Path,required=True);a=p.parse_args()
    record=cache_report.checked_result(a.result);stages=analyze(record);checks=[cache_report.checked_control(v) for v in a.checks]
    if any(v['config']!=record['case']['config'] or v['observer_version']!=record['evidence']['observer_version'] for v in checks):
        raise ValueError('Controls must use this exact probe and observer')
    if not any(v['negative_oracle_rejected'] for v in checks) or not any(not v['observer_enabled'] for v in checks):raise ValueError('Probe needs both negative and disabled controls')
    experiments.save(a.output,dict(study='profiling-disabled-perf-sprite-probe',scope='24 intervals of repeated direct renderer calls, not whole game frames; simulated 100 MHz os25',record=record,stages=stages,verification=checks,
        report_generator_sha256=experiments.sha(Path(__file__))))
    a.markdown.parent.mkdir(parents=True,exist_ok=True);a.markdown.write_text(markdown(record,stages,checks));print('Verified sprite report',a.output.resolve(),flush=True)

if __name__=='__main__':main()
