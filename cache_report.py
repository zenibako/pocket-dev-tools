#!/usr/bin/env python3
"""Verify passive cache evidence, then write frame tables and function rankings."""
import argparse
from collections import Counter
import json
from pathlib import Path

import cache_profile
import experiments


def pooled_distribution(frames, cache, field):
    histogram = Counter()
    for frame in frames:
        histogram.update({int(k): v for k, v in frame[cache][field]['histogram'].items()})
    count = sum(histogram.values())
    if not count:
        return dict(count=0, histogram={})
    def percentile(percent):
        target = (count - 1) * percent // 100
        seen = 0
        for value, n in sorted(histogram.items()):
            seen += n
            if seen > target:
                return value
    return dict(count=count, min=min(histogram), max=max(histogram),
                mean=sum(k*v for k, v in histogram.items()) / count,
                p50=percentile(50), p90=percentile(90), p99=percentile(99),
                histogram={str(k): v for k, v in sorted(histogram.items())})


def function_rankings(profile):
    named=[f for f in profile['functions'] if f['name']!='<padding or no function symbol>']
    by_refills=sorted(named,key=lambda f:(-f['refills'],f['name']))[:30]
    by_blocks=sorted(named,key=lambda f:(-f['i_block_cycles'],f['name']))[:30]
    total=profile['total_frame_cycles']
    refills=sum(f['refills'] for f in profile['functions'])
    return dict(top30_by_refills=by_refills,top30_by_block_cycles=by_blocks,
                top30_refill_count_share_percent=sum(f['refills'] for f in by_refills)/max(1,refills)*100,
                top30_by_refills_frame_share_percent=sum(f['i_block_cycles'] for f in by_refills)/total*100,
                top30_by_block_cycles_frame_share_percent=sum(f['i_block_cycles'] for f in by_blocks)/total*100,
                unattributed=[f for f in profile['functions'] if f not in named])


def checked_result(path):
    path = path.resolve()
    root = path.parents[4]
    if not root.is_relative_to(cache_profile.PRIVATE.resolve()):
        raise ValueError('Expected an isolated cache-profile result')
    result = json.loads(path.read_text())
    meta = result['cache_profile']
    if not meta['enabled'] or meta['profile'] is None:
        raise ValueError('Expected a completed positive cache profile')
    config,directory,capture=experiments.checked_capture(root)
    prepared=json.loads((directory/'prepared.json').read_text())
    rtl=json.loads((root/'build/fullframe/rtl/rtl.json').read_text())
    if result['config']!=config or result['prepared']!=prepared or result['rtl']!=rtl:
        raise ValueError('Stale positive cache replay')
    # Check the measured replay, not copied source-case results from another
    # traffic/negative run made with the previous simulator.
    artifacts=[(directory/(result['traffic']+'.log'),result['log_sha256']),
               (directory/'capture.json',prepared['capture_sha256']),
               (directory/'program.bin',prepared['image_sha256']),
               (directory/'stack.bin',prepared['stack_sha256']),
               (directory/'firmware.mif',prepared['bram_sha256']),
               (root/'build/fullframe/rtl/obj/Vtb_system',rtl['simulator_sha256']),
               (root/'build/fullframe/rtl/main.cpp',rtl['source_sha256']),
               (root/'fullframe/rtl.py',rtl['generator_sha256']),
               (root/'build/rtl/rtl.json',rtl['leaf_rtl_sha256'])]
    if prepared['framebuffer_sha256']:
        artifacts.append((directory/'framebuffer.bin',prepared['framebuffer_sha256']))
    for file,digest in artifacts:
        if experiments.sha(file)!=digest:raise ValueError('Cache replay artifact changed: '+str(file))
    record=dict(case=str(root),revision=json.loads((root/'snapshot.json').read_text())['revision'],
                config=config,traffic=result['traffic'],build_kind=config['kind'],native_scripts=config.get('native','enabled' if config['profile']=='port' else 'disabled'),
                compiler_version=result['compiler_version'],source_flags=capture['build']['app_flags'],
                substitutions=capture['build']['substitutions'],rows=result['rows'],
                frame_costs=result['frame_costs'],oracle_excluded_fields=result['oracle_excluded_fields'])
    _, source_dir, _ = experiments.checked_capture(Path(meta['source_case']))
    source_result = source_dir / (result['traffic'] + '-results.json')
    if experiments.sha(source_result) != meta['source_result_sha256']:
        raise ValueError('Original replay evidence changed')
    if result['rows'] != json.loads(source_result.read_text())['rows']:
        raise ValueError('Observer cycles/oracles differ from original replay')
    probe = result['rtl']['cache_probe']
    checks = [(path.parent / 'cache-profile.csv', meta['raw_sha256']),
              (path.parent / 'program.elf', meta['elf_sha256']),
              (root / 'build/cacheprobe/top.v', probe['top_sha256'])]
    checks.extend((root/name, digest) for name, digest in probe['observer_sources'].items())
    for file, digest in checks:
        if experiments.sha(file) != digest:
            raise ValueError('Cache profile evidence changed: ' + str(file))
    actual_cpu = experiments.sha(root/'inputs/os/src/fpga/vendor/vexriscv/VexiiRiscv/VexiiRiscv_os25.v')
    if probe['cpu_parameter_changes'] or actual_cpu != probe['cpu_sha256']:
        raise ValueError('Expected the unchanged production CPU')
    profile = cache_profile.parse(path.parent/'cache-profile.csv', result['rows'],
                                  cache_profile.symbols(path.parent/'program.elf'),expected_count=config.get('probe_samples',3))
    if profile != meta['profile']:
        raise ValueError('Stored analysis disagrees with fresh raw-event analysis')
    frames = profile['frames']
    totals = {key: sum(f[key] for f in frames) for key in
              ['cycles', 'i_block_cycles', 'd_block_cycles', 'overlap_cycles', 'union_block_cycles',
               'union_no_commit_cycles', 'i_block_no_commit_cycles', 'd_block_no_commit_cycles',
               'i_fetch_hold_cycles', 'i_miss_wait_cycles', 'i_miss_events']}
    summary = dict(**totals, **{key+'_percent': totals[key]/totals['cycles']*100 for key in
                               ['i_block_cycles', 'd_block_cycles', 'union_block_cycles', 'union_no_commit_cycles']})
    distributions = {cache: {field: pooled_distribution(frames, cache, field) for field in
                            ['accepted_to_last_cycles', 'accepted_to_first_cycles', 'ar_backpressure_cycles']}
                     for cache in ['I', 'D']}
    return dict(case=record, profile=profile, summary=summary, distributions=distributions,
                function_rankings=function_rankings(profile),
                evidence=dict(result=str(path), result_sha256=experiments.sha(path),
                              source_result_sha256=meta['source_result_sha256'], raw_sha256=meta['raw_sha256'],
                              elf_sha256=meta['elf_sha256'], observer_version=meta['observer_version'],
                              original_analyzer_sha256=meta['analyzer_sha256'], cpu_sha256=actual_cpu))


def table(headers, rows):
    return '\n'.join(['| '+' | '.join(headers)+' |', '| '+' | '.join(['---']*len(headers))+' |',
                     *['| '+' | '.join(str(x) for x in row)+' |' for row in rows]]) + '\n'


def checked_control(path):
    path=path.resolve();root=path.parents[4]
    if not root.is_relative_to(cache_profile.PRIVATE.resolve()):
        raise ValueError('Control evidence must be an isolated cache-profile result')
    result=json.loads(path.read_text())
    meta=result['cache_profile']
    config,directory,_=experiments.checked_capture(root)
    rtl=json.loads((root/'build/fullframe/rtl/rtl.json').read_text())
    prepared=json.loads((directory/'prepared.json').read_text())
    negative=path.name=='negative-results.json'
    if result['rtl']!=rtl or result['prepared']!=prepared:
        raise ValueError('Stale control replay')
    probe=rtl['cache_probe']
    checks=[(directory/('negative.log' if negative else result['traffic']+'.log'),result['log_sha256']),
            (root/'build/fullframe/rtl/obj/Vtb_system',rtl['simulator_sha256']),
            (root/'build/fullframe/rtl/main.cpp',rtl['source_sha256']),
            (root/'fullframe/rtl.py',rtl['generator_sha256']),
            (root/'build/rtl/rtl.json',rtl['leaf_rtl_sha256']),
            (root/'build/cacheprobe/top.v',probe['top_sha256']),
            (directory/'program.elf',meta['elf_sha256'])]
    checks.extend((root/name,digest) for name,digest in probe['observer_sources'].items())
    if meta['enabled']:checks.append((directory/'cache-profile.csv',meta['raw_sha256']))
    for file,digest in checks:
        if experiments.sha(file)!=digest:raise ValueError('Changed control evidence: '+str(file))
    _,source_dir,_=experiments.checked_capture(Path(meta['source_case']))
    originals=[source_dir/(traffic+'-results.json') for traffic in ['quiet','scanout']]
    originals=[p for p in originals if p.exists() and experiments.sha(p)==meta['source_result_sha256']]
    if len(originals)!=1:raise ValueError('Control source replay changed or ambiguous')
    original=originals[0]
    actual_cpu=experiments.sha(root/'inputs/os/src/fpga/vendor/vexriscv/VexiiRiscv/VexiiRiscv_os25.v')
    if probe['cpu_parameter_changes'] or actual_cpu!=probe['cpu_sha256']:
        raise ValueError('Control changed production CPU')
    if negative:
        if not result['rejected']:raise ValueError('Bad state oracle was not rejected')
    else:
        if result['rows']!=json.loads(original.read_text())['rows']:
            raise ValueError('Control observer changed cycles or output')
        if meta['enabled']:checked_result(path)
    return dict(result=str(path),result_sha256=experiments.sha(path),config=config,
                observer_version=meta['observer_version'],negative_oracle_rejected=negative,
                observer_enabled=meta['enabled'],cpu_parameter_changes=probe['cpu_parameter_changes'],
                unchanged_frame_cycles_and_oracles=not negative)


def markdown(records, checks=()):
    out = ['# Frozen f1d8542 cache profile (2026-10-10)', '',
           'Simulated 100 MHz os25, Speed mode, SDRAM, quiet traffic. Each window has three consecutive frames; '
           'the first starts with cold CPU caches. Traced and timing are separate ELFs. '
           'Timing omits `frame_tick`, `frame_event` and in-loop PCM hashing.', '',
           'I block is the union of the fetch refill hold and the pinned CPU’s miss-to-fetch-recovery waiting event. '
           'D block is the LSU refill waiter halting dispatch. These are cycles of cache-related pipeline blocking, '
           'not uniquely attributable lost execution cycles: older instructions can still commit. '
           'The union removes I/D overlap; its no-commit subset is reported separately. '
           'A refill’s full bus latency is not a CPU stall; speculative next-line I-cache prefetches are included.', '']
    for game in ['undertale', 'deltarune']:
        subset = [r for r in records if r['case']['config']['game'] == game]
        out += ['## '+('Undertale' if game == 'undertale' else 'Deltarune Chapter 1'), '']
        rows = []
        for r in subset:
            c=r['case']['config']
            for f in r['profile']['frames']:
                rows.append([c['window'], c['kind'], f['frame'], f['cycles'], f['i_block_cycles'], f['d_block_cycles'],
                             f['overlap_cycles'], f['I']['refill_count'], f['D']['refill_count'],
                             f"{f['I']['accepted_to_last_cycles']['mean']:.2f}",
                             f"{f['D']['accepted_to_last_cycles']['mean']:.2f}"])
        out += [table(['Window','Build','Frame','Frame cycles','I block','D block','Overlap',
                       'I refills','D refills','I cycles/refill','D cycles/refill'],rows), '']
    out += ['## Frame shares and measured distributions', '',
            'Shares are weighted by the three frames’ cycles. Distribution quantiles are pooled over accepted '
            'refills in the window, using order statistic floor((N−1)×p/100). Latency includes both handshake edges. '
            'The machine-readable report retains exact histograms, per-frame distributions, first-beat latency, '
            'AR backpressure, boundary-crossing transfers and outstanding-transaction unions.', '']
    rows=[]
    for r in records:
        c=r['case']['config'];s=r['summary']
        rows.append([c['game'],c['window'],c['kind'],
                     *[f'{s[k]:.2f}%' for k in ['i_block_cycles_percent','d_block_cycles_percent',
                                              'union_block_cycles_percent','union_no_commit_cycles_percent']],
                     s['i_fetch_hold_cycles'],s['i_miss_wait_cycles'],s['i_miss_events']])
    out += [table(['Game','Window','Build','I block','D block','Union','Union without commit',
                   'Fetch hold cycles','Miss recovery cycles','Miss events'],rows), '']
    rows=[]
    for r in records:
        c=r['case']['config']
        for cache in ['I','D']:
            d=r['distributions'][cache]['accepted_to_last_cycles']
            rows.append([c['game'],c['window'],c['kind'],cache,d['count'],d['min'],
                         f"{d['mean']:.2f}",d['p50'],d['p90'],d['p99'],d['max']])
    out += [table(['Game','Window','Build','Cache','Refills','Min','Mean','p50','p90','p99','Max'],rows), '']
    out += ['The 22/39-cycle I-cache observations are rare refills at boot-BRAM addresses '
            '`0x0`/`0x40`, outside the application ELF’s function ranges. They remain in the '
            'unattributed bucket. The distribution covers the actual I-cache bus, including '
            'those non-SDRAM addresses, rather than filtering to SDRAM code alone.', '']
    out += ['## Top 30 functions in each window and build', '',
            'Counts use the 64-byte refill line base. Blocking cycles use the initiating miss PC while the '
            'miss-recovery event is active, otherwise the held fetch PC. Consequently a function with many '
            'prefetched lines need not have many blocked cycles. ELF padding and absent symbols stay explicitly '
            'unattributed and are reported separately from the 30 named functions. Per-function “bus service” '
            'sums overlapping refill latencies; never interpret it as '
            'frame time. `executeLoop` is in SDRAM in all these cases.', '']
    for r in records:
        c=r['case']['config'];p=r['function_rankings']
        out += [f"### {c['game']} {c['window']} — {c['kind']}", '',
                f"Top 30 by count cover {p['top30_refill_count_share_percent']:.2f}% of I refills and "
                f"{p['top30_by_refills_frame_share_percent']:.2f}% of frame cycles in I blocking. "
                f"Top 30 by blocking cover {p['top30_by_block_cycles_frame_share_percent']:.2f}% of frame cycles.", '']
        for bucket in p['unattributed']:
            out += [f"Unattributed: {bucket['refills']} refills, {bucket['i_block_cycles']} I-block cycles "
                    f"({bucket['frame_share_percent']:.3f}% of the frame cycles).", '']
        for label,key in [('By refill count','top30_by_refills'),('By I-cache blocking cycles','top30_by_block_cycles')]:
            out += [label, '', table(['Rank','ELF function','I refills','I bus service cycles','I block cycles','Frame share'],
                                    [[n, '`'+f['name'].replace('|','\\|')+'`', f['refills'],f['transaction_cycles'],
                                      f['i_block_cycles'],f"{f['frame_share_percent']:.3f}%"]
                                     for n,f in enumerate(p[key],1)]), '']
    out += ['## Build and fidelity', '',
            'Frozen runner `f1d8542`; legacy profile, Ubuntu container GCC 13.2.0, `-O2`, RV32IMAFC, ILP32F, '
            '`-ffunction-sections -fdata-sections -falign-functions=64 -falign-loops=64`, global `OF_PC`, '
            'native script replacements disabled. The ELF, full flags, substitutions and exact source revision '
            'are recorded in the JSON. The copied SDK also adds those alignment flags; matching alignment alone '
            'does not establish parity with the v0.7 card’s compiler, link order or addresses. '
            'This does not use the `f42a23c` sprite section-ordering experiment.', '',
            '32 KiB two-way I-cache with next-line hardware prefetch; 128 KiB two-way D-cache; 64-byte lines. '
            'No CPU RTL parameters were changed. The observer is compiled only behind `HARNESS_CACHE_PROFILE` '
            'and runtime-enabled by `CACHE_PROFILE=1`. It adds no firmware instructions and preserves the '
            'original cycles and oracles. The optional free/unlimited I-cache counterfactual was not run.', '',
            'Cached harness-allocated framebuffer, fixed 800 audio pairs, deterministic virtual clock, '
            'substituted allocator/kernel/storage/audio services, no hardware interrupts/GPU/display scheduling '
            'or physical SD latency. The timed loop includes reached game, render and mix code, but neither '
            'production kernel ABI nor the physical board is reproduced. Quiet removes diagnostic scanout '
            'traffic; actual device traffic can change refill tails. D-block excludes other store-buffer/writeback '
            'backpressure. Field is walking; bmenu samples attack meters, not an entire battle phase.', '',
            'The frame-level result does not show I-cache refills dominating these complete frames. The narrower '
            'claim about scattered sprite/culling code remains undecided: this baseline and these windows '
            'do not isolate the device’s 150-instruction path, and the waiting counters are observational. '
            'Use the timing rankings as measured candidates for a layout experiment, then compare an isolated '
            'same-build path or a separately captured candidate; no speedup bound was measured here.', '',
            '## Evidence', '',
            'Raw CSV, ELF, simulator, wrapper, copied observer sources, original replay results and capture '
            'artifacts are hash-checked when generating this report. All inputs are private and stay under '
            'the harness directory; Docker mounts only the independent measurement copy.', '']
    out += [table(['Game/window/build','Observer','ELF SHA-256','Profile result SHA-256'],
                  [[f"{r['case']['config']['game']}/{r['case']['config']['window']}/{r['case']['config']['kind']}",
                    r['evidence']['observer_version'],r['evidence']['elf_sha256'],r['evidence']['result_sha256']]
                   for r in records]), '']
    if checks:
        out += ['Additional observer checks (each in its own independent copy):', '',
                table(['Game/window','Placement','Mode','Check','Result SHA-256'],
                      [[f"{r['config']['game']}/{r['config']['window']}",r['config']['variant'],r['config']['mode'],
                        'bad state rejected' if r['negative_oracle_rejected'] else
                        'observer disabled, identical' if not r['observer_enabled'] else 'scanout, identical',
                        r['result_sha256']] for r in checks]), '']
    return '\n'.join(out).rstrip()+'\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results',type=Path,nargs='+',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--markdown',type=Path,required=True)
    parser.add_argument('--checks',type=Path,nargs='*',default=[])
    args=parser.parse_args()
    records=[checked_result(p) for p in args.results]
    records.sort(key=lambda r:(r['case']['config']['game']!='undertale',
                               ['flowey','dodge','field','bmenu'].index(r['case']['config']['window']),
                               r['case']['config']['kind']!='timing'))
    # This report is deliberately the named baseline study, not a generic label
    # silently applied to other compiler/revision/service configurations.
    for r in records:
        c=r['case']['config']
        expected=dict(mode='speed',variant='sdram',profile='legacy',compiler='container',
                      native='disabled',framebuffer='cached',clock_cost=0,audio='fixed')
        if r['case']['traffic']!='quiet' or not r['case']['revision'].startswith('f1d8542') or any(c[k]!=v for k,v in expected.items()):
            raise ValueError('Baseline report configuration mismatch')
        if '13.2.0' not in r['case']['compiler_version']:
            raise ValueError('Baseline report compiler version mismatch')
    checks=[checked_control(p) for p in args.checks]
    experiments.save(args.output,dict(study='f1d8542-speed-sdram-quiet-cache',cases=records,verification=checks,
                                     report_generator_sha256=experiments.sha(Path(__file__))))
    args.markdown.parent.mkdir(parents=True,exist_ok=True)
    args.markdown.write_text(markdown(records,checks))
    print('Verified cache report:',args.output.resolve(),args.markdown.resolve())


if __name__=='__main__':main()
