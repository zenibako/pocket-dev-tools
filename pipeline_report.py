#!/usr/bin/env python3
"""Verify the frozen baseline pipeline study without replacing cache v2 evidence."""
import argparse
from collections import Counter,defaultdict
import csv
import json
from pathlib import Path
import cache_profile
import cache_report
import experiments
from pipeline_analysis import BITS


def summarize(profile):
    frames=profile['frames'];counts=Counter();no_retire=Counter();partition=Counter();mix=Counter();hist=Counter()
    for frame in frames:
        p=frame['pipeline'];counts.update(p['counts']);no_retire.update(p['no_retire_by_source'])
        mix.update(p['instruction_mix']);hist.update({int(k):n for k,n in p['branch_recovery_cycles']['histogram'].items()})
        # The exact mask histogram also distinguishes an issue edge from a
        # waiting candidate in the residual of the stated reporting priority.
        priority=['execute_freeze','d_block','store_buffer_wait','raw_dependency','fp_reservation',
                  'flush_interlock','fence_interlock','i_block','branch_recovery']
        for key,n in p['mask_histogram'].items():
            mask=int(key)
            label='retirement' if mask&1 else next((k for k in priority if mask&(1<<BITS.index(k))),
                'dispatch_without_retirement' if mask&2 else 'candidate_other' if mask&4 else 'frontend_or_pipeline_empty')
            partition[label]+=n
    cycles=profile['total_frame_cycles']
    values=[k for k,n in hist.items() for _ in range(n)]
    return dict(counts=dict(counts),no_retire_by_source=dict(no_retire),exclusive_partition=dict(partition),
                cycles=cycles,retired=counts['retired'],cycles_per_retired_instruction=cycles/counts['retired'],
                no_retire_cycles=cycles-counts['retired'],instruction_mix=dict(mix),
                branch_recovery_cycles=cache_profile.distribution(values))


def branch_functions(record):
    path=Path(record['evidence']['result']).parent
    attribution=cache_profile.Attribution(cache_profile.symbols(path/'program.elf'))
    frames=record['profile']['frames'];functions=defaultdict(Counter)
    for row in csv.reader((path/'cache-profile.csv').read_text().splitlines()):
        if row and row[0]=='B':
            pc,start,end=map(int,row[1:])
            if any(f['begin']<=start<f['end'] for f in frames):
                fn=functions[attribution.name(pc)];fn['mispredicts']+=1;fn['recovery_cycles']+=end-start
    return sorted([dict(name=k,**v) for k,v in functions.items()],key=lambda f:(-f['recovery_cycles'],f['name']))


def markdown(records,checks):
    table=cache_report.table
    labels=[f"{r['case']['config']['game']}/{r['case']['config']['window']}/{r['case']['config']['kind']}" for r in records]
    out=['# Frozen f1d8542 pipeline and cache profile (2026-10-10)','',
         'Simulated 100 MHz os25; Speed, SDRAM, quiet; four three-frame windows, each traced and timing. '
         'The original baseline and the earlier [cache report](RESULTS.md) are preserved. No CPU parameter was changed.','',
         'The user reports that placing sixteen sprite-draw functions together (14.7 KB) on the Pocket changed '
         'the probe from 19.87 to 19.56 µs and changed no section frame time. That experiment does not support '
         'conflicts among those functions as the explanation. These full-frame counters investigate other causes; '
         'they do not isolate that same device probe.','',
         '## Reading the counters','',
         'Retired instructions use `PrivilegedPlugin_logic_harts_0_commitMask`, the ctrl5 CommitService event '
         'used by the optional hardware instruction counter. The older cache observer’s ctrl4 whitebox commit '
         'decision is preserved for compatibility and is not the retirement count used for CPI here. '
         'UOP IDs associate dispatched PCs and decompressed instructions with retirement. CPI is native RISC-V '
         'cycles per retired instruction, not cycles per VM instruction.','',
         'All cause counters overlap. A frontend or dispatch wait can coexist with an older retirement. '
         'The no-retirement subsets and full mask histograms in private `results.json` retain that distinction. '
         'A no-retirement cycle is a pipeline observation, not proof that removing one asserted signal saves '
         'that cycle. Refill bus latency sums and branch recovery lengths are not additive CPU stall totals.','']
    for game in ['undertale','deltarune']:
        subset=[r for r in records if r['case']['config']['game']==game]
        out+=['## '+('Undertale' if game=='undertale' else 'Deltarune Chapter 1'),'']
        rows=[]
        for r in subset:
            c=r['case']['config']
            for f in r['profile']['frames']:
                p=f['pipeline'];rows.append([c['window'],c['kind'],f['frame'],f['cycles'],p['counts']['retired'],
                    f"{p['cycles_per_retired_instruction']:.3f}",f['i_block_cycles'],f['d_block_cycles'],
                    f"{100*f['union_block_cycles']/f['cycles']:.2f}%",f['I']['refill_count'],f['D']['refill_count']])
        out+=[table(['Window','Build','Frame','Cycles','Retired','CPI','I block cycles','D block cycles','I/D union','I refills','D refills'],rows),'']
        rows=[]
        for r in subset:
            c=r['case']['config']
            for cache in ['I','D']:
                d=r['distributions'][cache]['accepted_to_last_cycles']
                rows.append([c['window'],c['kind'],cache,d['count'],f"{d['mean']:.2f}",d['min'],d['p50'],d['p90'],d['p99'],d['max']])
        out+=['Pooled refill latency in cycles, accepted AR through accepted RLAST inclusive. Full distributions '
              'are retained in the private results.','',table(['Window','Build','Cache','Count','Mean','Min','p50','p90','p99','Max'],rows),'']
    out+=['## Where cycles are observed','',
          'Each entry below is a percentage of the three-frame window. These rows overlap; do not sum them. '
          '`RAW` is an unavailable source operand while a valid candidate cannot issue. Load/multiply/FP rows '
          'identify the producer of that dependency. Late integer-register FP results can remain in other RAW; '
          'the FP row is a conservative subset. Integer multiply has no separate execute-freeze source in this '
          'netlist. Hardware single-precision FPU counters exclude software double helpers.','']
    names=['execute_freeze','i_block','d_block','raw_dependency','load_dependency','multiply_dependency','fp_dependency',
           'fp_reservation','flush_interlock','fence_interlock','store_buffer_wait','integer_divider','fp_divider','fp_sqrt',
           'fp_to_int','int_to_fp','uncached_io','csr','atomic','branch_recovery']
    out+=[table(['Observed cause']+labels,[[name]+[f"{100*r['pipeline_summary']['counts'][name]/r['pipeline_summary']['cycles']:.2f}%" for r in records] for name in names]),'']
    out+=['The integer and FP divide units share a divider; `FpuDivPlugin_SEL` splits its freeze cycles. '
          'FPU reservations track shared add/pack resources, separately from sqrt and conversion freezes. '
          'Uncached-I/O freeze includes the LSU ordering/response wait and is not a D-cache refill. '
          'Store-buffer dispatch waits and flush/fence interlocks are also separate from D refills. '
          'Every sample checks that the reconstructed producer dependencies equal the RTL RAW hazard and '
          'that the seven execute-freeze sources account for the complete freeze signal.','',
          'No-retirement subset, as a percentage of the full window (also overlapping):','',
          table(['Observed cause']+labels,[[name]+[f"{100*r['pipeline_summary']['no_retire_by_source'][name]/r['pipeline_summary']['cycles']:.2f}%" for r in records] for name in names]),'',
          'Disjoint accounting of all clocks follows this explicit priority: retirement; execution freeze; '
          'D wait; store-buffer wait; RAW; FP reservation; flush interlock; fence interlock; I block; '
          'branch recovery; residual dispatch without retirement; other waiting candidate; empty frontend/pipeline. '
          'This makes the table sum to 100%; its priority assigns overlaps for presentation, not causal blame. '
          'A dispatch without retirement may reflect pipeline latency, cancelled work or recovery.','']
    keys=['retirement','execute_freeze','d_block','store_buffer_wait','raw_dependency','fp_reservation','flush_interlock',
          'fence_interlock','i_block','branch_recovery','dispatch_without_retirement','candidate_other','frontend_or_pipeline_empty']
    out+=[table(['Exclusive observation']+labels,[[name]+[f"{100*r['pipeline_summary']['exclusive_partition'].get(name,0)/r['pipeline_summary']['cycles']:.2f}%" for r in records] for name in keys]),'']
    out+=['## Branches and instruction mix','',
          'A mispredict is a firing branch/jump learn event with `wasWrong`, including direction and target '
          'corrections for calls/returns. Recovery spans that event to dispatch of its corrected target. It '
          'includes overlapping cache and execution waits; it is not a pure mispredict penalty. BTB and '
          'decoder redirect pins are additionally retained as asserted-cycle counters, not assumed to be '
          'distinct retired branch events.','']
    rows=[]
    for r,label in zip(records,labels):
        p=r['pipeline_summary'];c=p['counts'];d=p['branch_recovery_cycles']
        rows.append([label,p['retired'],f"{p['cycles_per_retired_instruction']:.3f}",c['branches_resolved'],c['branch_mispredicts'],
                     f"{100*c['branch_mispredicts']/max(1,c['branches_resolved']):.2f}%",f"{d['mean']:.2f}",d['p50'],d['p90'],d['p99'],d['max']])
    out+=[table(['Window/build','Retired','CPI','Branches/jumps','Mispredicts','Rate','Recovery mean','p50','p90','p99','Max'],rows),'']
    mix=['other_integer','load','store','branch_jump','fp_compute','integer_multiply','integer_divide_rem','system_csr']
    out+=[table(['Retired instruction class']+labels,[[name]+[f"{100*r['pipeline_summary']['instruction_mix'].get(name,0)/r['pipeline_summary']['retired']:.2f}%" for r in records] for name in mix]),'']
    out+=['The timing builds still enable `SW_DRAW_PROFILE` and `ENABLE_VM_GML_PROFILER`. '
          'In the frozen renderer, `swrDrawSprite` formats a note with `snprintf`, and `swrNote` '
          'hashes/searches descriptions and formats new descriptions. `printf_core` therefore includes '
          'renderer note formatting, not just UART output. These costs remain when VM tracing is disabled. '
          'They are measured work in this baseline; their cost in the card build has not been matched.','',
          '## Code attribution','',
          'Cache refills are attributed by line base; I block by initiating miss or held fetch PC. Sized ELF '
          'symbols keep padding explicit. These are different histograms. Pipeline dependency cycles below '
          'are charged to the waiting consumer’s dispatch PC. Retirement uses the actual retiring instruction '
          'PC. None of these function counts alone constitutes a function’s elapsed time.','']
    for r,label in zip(records,labels):
        out+=['### '+label,'']
        ranks=r['function_rankings']
        out+=[f"Top 30 by refill count account for {ranks['top30_refill_count_share_percent']:.2f}% of all I refills "
              f"and {ranks['top30_by_refills_frame_share_percent']:.2f}% of the frame in attributed I block. "
              f"Top 30 by I block account for {ranks['top30_by_block_cycles_frame_share_percent']:.2f}% of the frame.",'']
        for title,key in [('I refills','top30_by_refills'),('I block cycles','top30_by_block_cycles')]:
            out+=[title+':','',table(['Function','I refills','I block cycles','Frame share'],
                [[f['name'],f['refills'],f['i_block_cycles'],f"{f['frame_share_percent']:.3f}%"] for f in ranks[key]]),'']
        fn=r['profile']['pipeline']['functions']
        top=sorted(fn,key=lambda f:(-f.get('retired',0),f['name']))[:20]
        out+=['Top retiring functions, with overlapping waits charged to their consumers:','',
              table(['Function','Retired','RAW cycles','Load dependency','Multiply dependency','FP dependency','Store-buffer wait'],
                    [[f['name'],f.get('retired',0),f.get('raw_dependency',0),f.get('load_dependency',0),f.get('multiply_dependency',0),
                      f.get('fp_dependency',0),f.get('store_buffer_wait',0)] for f in top]),'',
              'Top branch recovery sites, grouped by function:','',table(['Function','Mispredicts','Recovery envelope cycles'],
                    [[f['name'],f['mispredicts'],f['recovery_cycles']] for f in r['branch_functions'][:20]]),'']
    out+=['## Interpretation and Pocket comparability','',
          'Timing CPI ranges from 1.789 to 1.805 across the Deltarune windows and is 1.960 in Undertale. '
          'Execution freezes occupy 0.87–2.13% of timing frames, while branch-recovery envelopes occupy '
          '10.48–14.85% and RAW dependencies 9.63–13.14%. Hardware FPU/divider freezes are not dominant; '
          'branches, dependencies, cache waits and executed work all matter. These overlapping observations '
          'do not identify a single bottleneck for the device probe.','']
    for r,label in zip(records,labels):
        p=r['pipeline_summary'];s=r['summary']
        out+=[f"{label}: CPI {p['cycles_per_retired_instruction']:.3f}; I block {s['i_block_cycles_percent']:.2f}%, "
              f"D block {s['d_block_cycles_percent']:.2f}%, cache union {s['union_block_cycles_percent']:.2f}%. "
              f"No retirement on {100*p['no_retire_cycles']/p['cycles']:.2f}% of clocks.",'']
    out+=['I-cache refill blocking does not dominate these complete frames. The recorded alternatives show '
          'where pipeline waits occur, including overlaps, but no single signal proves the cause of the '
          'device’s isolated sprite probe. The measured full-frame CPI should not be substituted for its '
          'reported roughly 10 cycles/instruction. Isolating the same probe in a matching binary would still '
          'be required to decide that path’s dominant cost. No free-refill/unlimited-cache or other hardware '
          'counterfactual was run.','',
          'Frozen runner `f1d8542`; OS `8318f25`; SDK `7882a0d`; container GCC 13.2.0. Builds use '
          '`-O2 -ffunction-sections -fdata-sections -falign-functions=64 -falign-loops=64`, matching those SDK '
          'alignment flags. The device’s v0.7/perf build has different source/compiler/link context, so its '
          'layout is not established comparable. No `hot-sprites.ld` ordering was applied. Global OF_PC, '
          'legacy services, native scripts disabled, harness-allocated cached framebuffer, fixed 800 audio '
          'pairs, deterministic free clock. Timing omits per-VM-instruction `frame_tick`/`frame_event` and '
          'in-loop PCM hashing; trace changes instructions and cache contents.','',
          'The timed loop reaches game, rendering and mixing code, but allocator/kernel/storage/audio '
          'services are substituted. No physical SD latency, interrupts, GPU/display scheduling or full '
          'production ABI is modeled. Quiet excludes diagnostic scanout traffic; board contention may change '
          'refill tails. Flowey/dodge are battle windows; field is walking; bmenu samples attack meters. '
          'Each window begins with cold CPU caches, then runs three consecutive frames.','',
          '## Verification and evidence','',
          'Each measured replay matches all original cycles and oracles. Raw CSV, ELF, simulator, copied '
          'observer/wrapper, CPU, captures and source results are hash-verified and freshly reanalyzed. '
          'CPU parameter changes are `{}`. Additional disabled, corrupted-oracle and scanout controls are '
          'recorded below. Docker mounts only an independent harness case; no game worktree, original SDK/OS '
          'or SD card is changed.','',
          table(['Window/build','Observer version','ELF SHA-256','Result SHA-256'],
                [[label,r['evidence']['observer_version'],r['evidence']['elf_sha256'],r['evidence']['result_sha256']] for label,r in zip(labels,records)]),'',
          table(['Window','Placement','Mode','Control','Result SHA-256'],
                [[f"{c['config']['game']}/{c['config']['window']}",c['config']['variant'],c['config']['mode'],
                  'corrupted oracle rejected' if c['negative_oracle_rejected'] else 'disabled, identical' if not c['observer_enabled'] else 'scanout, identical',c['result_sha256']] for c in checks]),'']
    return '\n'.join(out).rstrip()+'\n'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--results',type=Path,nargs='+',required=True);p.add_argument('--checks',type=Path,nargs='*',default=[])
    p.add_argument('--output',type=Path,required=True);p.add_argument('--markdown',type=Path,required=True)
    a=p.parse_args();records=[cache_report.checked_result(path) for path in a.results]
    records.sort(key=lambda r:(r['case']['config']['game']!='undertale',['flowey','dodge','field','bmenu'].index(r['case']['config']['window']),r['case']['config']['kind']!='timing'))
    expected={(g,w,k) for g,w in [('undertale','flowey'),('deltarune','dodge'),('deltarune','field'),('deltarune','bmenu')] for k in ['trace','timing']}
    actual=[(r['case']['config']['game'],r['case']['config']['window'],r['case']['config']['kind']) for r in records]
    if len(actual)!=8 or set(actual)!=expected:raise ValueError('Expected complete eight-case pipeline matrix')
    for r in records:
        c=r['case']['config']
        config=dict(mode='speed',variant='sdram',profile='legacy',compiler='container',native='disabled',framebuffer='cached',clock_cost=0,audio='fixed')
        if r['case']['traffic']!='quiet' or not r['case']['revision'].startswith('f1d8542') or any(c[k]!=v for k,v in config.items()) or '13.2.0' not in r['case']['compiler_version']:
            raise ValueError('Frozen baseline configuration mismatch')
        if r['profile'].get('pipeline',{}).get('schema')!=3:raise ValueError('Expected canonical-retirement pipeline observations')
        r['pipeline_summary']=summarize(r['profile']);r['branch_functions']=branch_functions(r)
    checks=[cache_report.checked_control(path) for path in a.checks]
    experiments.save(a.output,dict(study='f1d8542-speed-sdram-quiet-pipeline',cases=records,verification=checks,
        cpu_parameter_changes={},report_generator_sha256=experiments.sha(Path(__file__)),pipeline_analyzer_sha256=experiments.sha(Path(__file__).with_name('pipeline_analysis.py'))))
    a.markdown.parent.mkdir(parents=True,exist_ok=True);a.markdown.write_text(markdown(records,checks))
    print('Verified pipeline report:',a.output.resolve(),a.markdown.resolve())

if __name__=='__main__':main()
