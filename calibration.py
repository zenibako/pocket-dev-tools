#!/usr/bin/env python3
"""Prepare an identical Pocket ELF and independently verified RTL calibration."""
import argparse,json,os,re,shutil,subprocess
from pathlib import Path
import cache_profile,cache_report,experiments,pipeline_report
ROOT=experiments.ROOT
PRIVATE=ROOT/'experiments/calibrations'
STAGES={0:'inside',1:'door',2:'texture-found',3:'drawing-entered',4:'clipped',5:'setup',6:'layers-flushed',7:'outside'}
SAVE_FILE='calibration_log.sav'

def parse(text,mode):
    # Pocket save slots keep old bytes beyond the terminating NUL.
    text=text.split('\0',1)[0].replace('\r\n','\n')
    if 'FRAMEHARNESS FAIL' in text:raise ValueError('Failed calibration')
    if '=== UART BEGIN ===' in text:
        blocks=re.findall(r'=== UART BEGIN ===\n(.*?)\n=== UART END ===',text,re.S)
        if len(blocks)!=1:raise ValueError('Incomplete or duplicate RTL UART transcript')
        text=blocks[0]+'\n'
    info=re.findall(r'^CALINFO (\S+) (\S+) cpu_hz=(\d+) os_version=([0-9a-f]+) core_variant=(\d+) caps_version=(\d+)$',text,re.M)
    pixels=re.findall(r'^CALPIXELS ([0-9a-f]{8})$',text,re.M)
    rows=[]
    for m in re.finditer(r'^CALRESULT (\d+) (\d+) (\d+) (\S+) (\d+) (\d+) (\d+) ([0-9a-f]{8}) ([0-9a-f]{8})$',text,re.M):
        index,job,round_,name,n,ops,cycles,value,expected=m.groups()
        rows.append(dict(index=int(index),job=int(job),round=int(round_),name=name,iterations=int(n),operations=int(ops),
                         cycles=int(cycles),value=int(value,16),expected=int(expected,16)))
    if len(info)!=1 or info[0][1]!=mode or len(pixels)!=1 or len(rows)!=72 or 'CALIBRATION PASS HAL init' not in text or 'FRAMEHARNESS FAIL' in text:
        raise ValueError('Incomplete/failed calibration or wrong execution mode')
    expected_order=[(job,r) for job in range(16) for r in range(3)]+[(16+s,r) for r in range(3) for s in [6,5,4,3,2,1,0,7]]
    for index,(row,order) in enumerate(zip(rows,expected_order)):
        if row['index']!=index or (row['job'],row['round'])!=order or row['value']!=row['expected']:
            raise ValueError('Calibration order or independent output disagrees')
        if mode=='reference' and row['cycles']!=0 or mode!='reference' and row['cycles']<=0:
            raise ValueError('Invalid timing for execution mode')
    build_id,_,hz,os_version,variant,caps_version=info[0]
    if not re.fullmatch('[0-9a-f]{16}',build_id) or int(hz)!=100000000 or mode=='hardware' and int(caps_version)<2:
        raise ValueError('Unexpected calibration identity or clock/capabilities')
    return dict(build_id=build_id,mode=mode,cpu_hz=int(hz),os_version=int(os_version,16),
                core_variant=int(variant),caps_version=int(caps_version),pixels=pixels[0],rows=rows)

def match_reference(actual,reference):
    if actual['build_id']!=reference['build_id'] or actual['pixels']!=reference['pixels']:
        raise ValueError('Calibration/reference identity or pixels disagree')
    if [{k:v for k,v in r.items() if k!='cycles'} for r in actual['rows']]!=[{k:v for k,v in r.items() if k!='cycles'} for r in reference['rows']]:
        raise ValueError('Calibration/reference numerical results disagree')

def checked_reference(d):
    ref=json.loads((d/'reference.json').read_text())
    for name,digest in ref['logs'].items():
        if experiments.sha(d/name)!=digest:raise ValueError('Reference evidence changed')
    for i in range(2):
        if parse((d/f'reference-{i}.log').read_text(),'reference')!=ref['result']:
            raise ValueError('Stored reference differs from raw log')
        if 'save_checks' in ref:
            saved=(d/f'reference-{i}'/SAVE_FILE).read_bytes()
            if not saved.endswith(b'\0') or saved.count(b'\0')!=1 or parse(saved.decode(),'reference')!=ref['result']:
                raise ValueError('Invalid saved reference')
    if 'FRAMEHARNESS FAIL calibration independent result oracle' not in (d/'negative-reference.log').read_text():
        raise ValueError('Missing negative reference rejection')
    return ref['result']

def create(args):
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]*',args.snapshot):raise ValueError('Snapshot must be a local name')
    source=ROOT/'experiments/snapshots'/args.snapshot;experiments.verify_inputs(source)
    record=cache_report.checked_result(args.platform_result)
    platform=Path(record['case']['case']);sdk=args.sdk.resolve()
    extras={name:experiments.sha(sdk/name) for name in ['app.ld','of_init.c']}
    config=dict(snapshot=args.snapshot,snapshot_sha256=experiments.sha(source/'snapshot.json'),
                sources={str(p.relative_to(ROOT)):experiments.sha(p) for p in (ROOT/'calibration').iterdir() if p.is_file()},
                launcher_sha256=experiments.sha(Path(__file__)),sdk_extra=extras,
                sdk_revision=subprocess.check_output(['git','--no-optional-locks','-C',str(sdk),'rev-parse','HEAD'],text=True).strip(),
                sdk_local_changes=subprocess.check_output(['git','--no-optional-locks','-C',str(sdk),'status','--porcelain','--','app.ld','of_init.c'],text=True),
                platform_result=str(args.platform_result.resolve()),platform_result_sha256=record['evidence']['result_sha256'],
                cpu_sha256=record['evidence']['cpu_sha256'],observer_version=record['evidence']['observer_version'],
                measured_binary='same ELF for Pocket and RTL',renderer_profiling=False,gml_profiling=False,
                validation='after_all_72_intervals',clock='MMIO 0x40000004',expected_cpu_hz=100000000,
                fixture='generated 40x40 sprite, cached 320x240 framebuffer, half-scale',sprite_order=[6,5,4,3,2,1,0,7],
                save_log=dict(filename=SAVE_FILE,slot=11,transport='benchmark fopen/fwrite/NUL/fclose',
                              phase='after_all_72_intervals',history='latest_run',rtl_file_write=False))
    import hashlib
    config['id']=hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()[:16]
    case=PRIVATE/('cal-'+config['id'])
    if case.exists():raise ValueError('Case exists; preserve it and use verify/replay instead')
    experiments.tooling(case);experiments.copy_tree(source/'inputs',case/'inputs')
    for name in ['input-manifest.json','snapshot.json']:shutil.copy2(source/name,case/name)
    shutil.copytree(ROOT/'calibration',case/'calibration',ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copy2(ROOT/'calibration.py',case/'calibration.py')
    (case/'hardware-sdk').mkdir()
    for name,digest in extras.items():
        shutil.copy2(sdk/name,case/'hardware-sdk'/name)
        if experiments.sha(case/'hardware-sdk'/name)!=digest:raise ValueError('SDK changed during private copy')
    for name in ['rtl','fullframe/rtl','cacheprobe']:
        experiments.copy_tree(platform/'build'/name,case/'build'/name)
    shutil.copytree(platform/'cacheprobe',case/'cacheprobe',ignore=shutil.ignore_patterns('__pycache__'))
    experiments.save(case/'calibration.json',config)
    subprocess.run(experiments.docker(case,'python3','calibration/build.py'),check=True)
    print('CALCASE',case,flush=True);return case

def checked(case):
    case=case.resolve()
    if not case.is_relative_to(PRIVATE.resolve()):raise ValueError('Expected an isolated calibration case')
    experiments.verify_inputs(case)
    build=json.loads((case/'build/calibration/build.json').read_text());config=json.loads((case/'calibration.json').read_text())
    if build['config']!=config or build['cpu_parameter_changes']:raise ValueError('Stale calibration config/CPU parameters')
    for name,digest in {**config['sources'],'calibration.py':config['launcher_sha256']}.items():
        if experiments.sha(case/name)!=digest:raise ValueError('Calibration adapter changed: '+name)
    for name,digest in build['sources'].items():
        if experiments.sha(case/name)!=digest:raise ValueError('Calibration source changed: '+name)
    d=case/'build/calibration'
    for name,digest in build['artifacts'].items():
        if experiments.sha(d/name)!=digest:raise ValueError('Calibration binary/artifact changed: '+name)
    rtl=json.loads((case/'build/fullframe/rtl/rtl.json').read_text());probe=rtl['cache_probe']
    files={**probe['observer_sources'],'build/fullframe/rtl/obj/Vtb_system':rtl['simulator_sha256'],
           'build/fullframe/rtl/main.cpp':rtl['source_sha256'],'build/cacheprobe/top.v':probe['top_sha256'],
           'inputs/os/src/fpga/vendor/vexriscv/VexiiRiscv/VexiiRiscv_os25.v':config['cpu_sha256']}
    for name,digest in files.items():
        if experiments.sha(case/name)!=digest:raise ValueError('Calibration platform changed: '+name)
    if probe['cpu_parameter_changes'] or probe['cpu_sha256']!=config['cpu_sha256']:raise ValueError('Changed calibration CPU')
    return d,build,rtl

def reference(case):
    d,build,_=checked(case);runs=[];artifacts=[]
    for i in range(2):
        path=d/f'reference-{i}.log'
        if path.exists():raise ValueError('Preserve previous reference evidence')
        work=d/f'reference-{i}';work.mkdir()
        command=f'cd /work/{work.relative_to(case)} && qemu-riscv32 -B 0x100000000 /work/build/calibration/app.elf --reference'
        with path.open('w') as log:subprocess.run(experiments.docker(case,'sh','-c',command),stdout=log,stderr=subprocess.STDOUT,check=True)
        runs.append(parse(path.read_text(),'reference'))
        saved=work/SAVE_FILE;data=saved.read_bytes()
        if not data.endswith(b'\0') or data.count(b'\0')!=1 or len(data)>16385:raise ValueError('Invalid reference save text/NUL')
        expected=''.join(line for line in path.read_text().splitlines(keepends=True) if not line.startswith('CALSAVE ')).encode()+b'\0'
        if data!=expected or parse(data.decode(),'reference')!=runs[-1]:raise ValueError('Saved log differs from stdout')
        artifacts.append(saved)
    if runs[0]!=runs[1] or experiments.sha(d/'reference-0.log')!=experiments.sha(d/'reference-1.log'):
        raise ValueError('QEMU calibration reference was not repeatable')
    path=d/'negative-reference.log'
    work=d/'negative-reference';work.mkdir()
    command=f'cd /work/{work.relative_to(case)} && qemu-riscv32 -B 0x100000000 /work/build/calibration/app.elf --negative-reference'
    with path.open('w') as log:p=subprocess.run(experiments.docker(case,'sh','-c',command),stdout=log,stderr=subprocess.STDOUT)
    if p.returncode!=2 or 'FRAMEHARNESS FAIL calibration independent result oracle' not in path.read_text():
        raise ValueError('QEMU failed to reject the corrupt oracle')
    if runs[0]['build_id']!=build['config']['id']:raise ValueError('Reference belongs to a different binary')
    saved=work/SAVE_FILE
    if 'FRAMEHARNESS FAIL calibration independent result oracle' not in saved.read_text():raise ValueError('Failed run not saved')
    artifacts.append(saved)
    work=d/'save-failure-reference';work.mkdir();(work/SAVE_FILE).mkdir()
    path=d/'save-failure-reference.log'
    command=f'cd /work/{work.relative_to(case)} && qemu-riscv32 -B 0x100000000 /work/build/calibration/app.elf --reference'
    with path.open('w') as log:p=subprocess.run(experiments.docker(case,'sh','-c',command),stdout=log,stderr=subprocess.STDOUT)
    if p.returncode!=2 or 'FRAMEHARNESS FAIL calibration save log write' not in path.read_text() or 'CALIBRATION PASS' in path.read_text():
        raise ValueError('Save failure did not fail closed')
    experiments.save(d/'reference.json',dict(result=runs[0],logs={str(p.relative_to(d)):experiments.sha(p) for p in [*d.glob('*reference*.log'),*artifacts]},
        save_checks=dict(saved_text_matches_stdout=True,failed_run_saved=True,save_failure_rejected=True)))
    print('PASS repeated QEMU/saved logs, negative oracle and rejected save failure',flush=True)

def replay(case,traffic='quiet',disabled=False,negative=False):
    d,build,rtl=checked(case);label=traffic+'-'+('negative' if negative else 'off' if disabled else 'on')
    dest=d/label
    if dest.exists():raise ValueError('Preserve previous replay evidence: '+str(dest))
    dest.mkdir()
    for name in ['stack.bin','firmware.mif']:shutil.copy2(d/name,dest/name)
    shutil.copy2(d/('negative.bin' if negative else 'program.bin'),dest/'program.bin')
    bounds=build['symbols'];env={**os.environ,'CACHE_PROFILE':str(int(not disabled)),
        'SCAN_ENABLE':str(int(traffic=='scanout')),'SCAN_PERIOD':'3175','SCAN_LEN':'80','SCAN_ACTIVE':'480','SCAN_TOTAL':'525',
        'SCAN_BASE_HW':'0x1800000','STRIKE_SCAN_PERIOD':'1000000000'}
    for key,name in [('BEGIN','calibration_begin'),('END','calibration_end')]:
        for side in ['LO','HI']:env['CACHE_'+key+'_'+side]=str(bounds[name]['address']+(bounds[name]['size'] if side=='HI' else 0))
    cmd=experiments.docker(case,'sh','-c',f'cd /work/{dest.relative_to(case)} && /work/build/fullframe/rtl/obj/Vtb_system program.bin 80000000')
    index=cmd.index('undertale-vm-os25-frames:local');cmd[index:index]=[x for k,v in env.items() if k.startswith(('CACHE_','SCAN_','STRIKE_SCAN_')) for x in ['-e',k+'='+v]]
    with (dest/'rtl.log').open('w') as log:p=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=900)
    finish_replay(case,label,p.returncode)

def finish_replay(case,label,returncode):
    d,build,rtl=checked(case);dest=d/label
    if (dest/'results.json').exists():raise ValueError('Preserve previous replay analysis')
    negative=label.endswith('-negative');disabled=label.endswith('-off')
    for name in ['program.bin','stack.bin','firmware.mif']:
        source='negative.bin' if negative and name=='program.bin' else name
        if experiments.sha(dest/name)!=experiments.sha(d/source):raise ValueError('Replay input changed: '+name)
    text=(dest/'rtl.log').read_text();profile=None;actual=None
    for token in ['WCONF: mism=0 spurious=0 exp_fifo=0 aw_fifo=0 run_left=0','R mismatches=0  scanout mismatches=0  rlast slips=0  orphan beats=0  DRAM strikes=0','SDRAM errors=0']:
        if token not in text:raise ValueError('Calibration memory oracle failed: '+token)
    if negative:
        if returncode!=2 or 'FRAMEHARNESS FAIL calibration independent result oracle' not in text:
            raise ValueError('RTL did not reject corrupt independent oracle')
    else:
        actual=parse(text,'rtl')
        if returncode:raise ValueError('RTL failed')
        match_reference(actual,checked_reference(d))
        if not disabled:
            expected=[dict(cycles=r['cycles'],oracle=[r['index']]) for r in actual['rows']]
            profile=cache_profile.parse(dest/'cache-profile.csv',expected,cache_profile.symbols(d/'app.elf'),expected_count=72)
    experiments.save(dest/'results.json',dict(label=label,actual=actual,profile=profile,negative_oracle_rejected=negative,
        observer_enabled=not disabled,elf_sha256=experiments.sha(d/'app.elf'),build_sha256=experiments.sha(d/'build.json'),
        rtl=rtl,artifacts={p.name:experiments.sha(p) for p in dest.iterdir() if p.is_file()}))
    print('PASS calibration',label,flush=True)

def analyze(case,traffic,disabled,negative):
    label=traffic+'-'+('negative' if negative else 'off' if disabled else 'on')
    text=(case/'build/calibration'/label/'rtl.log').read_text()
    verdict=re.findall(r'^cycles=\d+ PC=0x[0-9a-f]+ exit=(\d+)$',text,re.M)
    if len(verdict)!=1:raise ValueError('Missing complete simulator verdict')
    finish_replay(case,label,int(verdict[0]))

def verify_replay(case,label):
    d,build,rtl=checked(case);dest=d/label;result=json.loads((dest/'results.json').read_text())
    if result['build_sha256']!=experiments.sha(d/'build.json') or result['elf_sha256']!=experiments.sha(d/'app.elf') or result['rtl']!=rtl:
        raise ValueError('Stale calibration replay')
    for name,digest in result['artifacts'].items():
        if experiments.sha(dest/name)!=digest:raise ValueError('Calibration replay changed: '+name)
    if not result['negative_oracle_rejected']:
        actual=parse((dest/'rtl.log').read_text(),'rtl')
        if actual!=result['actual']:raise ValueError('Stored calibration rows differ from raw log')
        match_reference(actual,checked_reference(d))
        if result['observer_enabled']:
            p=cache_profile.parse(dest/'cache-profile.csv',[dict(cycles=r['cycles'],oracle=[r['index']]) for r in actual['rows']],cache_profile.symbols(d/'app.elf'),expected_count=72)
            if p!=result['profile']:raise ValueError('Stored calibration profile differs from raw events')
    elif 'FRAMEHARNESS FAIL calibration independent result oracle' not in (dest/'rtl.log').read_text():
        raise ValueError('Missing negative RTL rejection')
    return result

def summarize(result):
    groups={}
    for frame,row in zip(result['profile']['frames'],result['actual']['rows']):groups.setdefault(row['job'],[]).append((frame,row))
    summary=[]
    for job,rows in sorted(groups.items()):
        frames=[f for f,_ in rows];s=pipeline_report.summarize(dict(frames=frames,total_frame_cycles=sum(f['cycles'] for f in frames)))
        ops=sum(r['operations'] for _,r in rows)
        summary.append(dict(job=job,name=rows[0][1]['name'] if job<16 else 'sprite-'+STAGES[job-16],
            operations=ops,cycles=s['cycles'],cycles_per_operation=s['cycles']/ops,cpi=s['cycles_per_retired_instruction'],
            batch_cycles=[f['cycles'] for f in frames],pipeline=s,
            i_block=sum(f['i_block_cycles'] for f in frames),d_block=sum(f['d_block_cycles'] for f in frames),
            refills={k:sum(f[k]['refill_count'] for f in frames) for k in ['I','D']},
            distributions={k:cache_report.pooled_distribution(frames,k,'accepted_to_last_cycles') for k in ['I','D']}))
    return summary

def report(case,output):
    d,build,_=checked(case)
    checked_reference(d)
    enabled=verify_replay(case,'quiet-on');disabled=verify_replay(case,'quiet-off');negative=verify_replay(case,'quiet-negative')
    if enabled['actual']!=disabled['actual'] or not negative['negative_oracle_rejected']:raise ValueError('Calibration controls failed')
    scan=verify_replay(case,'scanout-on');summary=summarize(enabled);scan_summary=summarize(scan)
    bundle=case/'hardware'
    hardware_manifest=dict(build_id=build['config']['id'],elf_sha256=experiments.sha(d/'app.elf'),
        hardware_entry=build['entry'],rtl_entry=build['rtl_entry'],compiler=build['compiler_version'],flags=build['flags'],
        source_revision=json.loads((case/'snapshot.json').read_text())['revision'],sdk=build['config']['sdk_extra'],
        sdk_revision=build['config']['sdk_revision'],sdk_local_changes=build['config']['sdk_local_changes'],
        cpu_rtl_sha256=build['config']['cpu_sha256'],observer_version=build['config']['observer_version'],
        same_elf_for_hardware_qemu_rtl=True,hardware_run_performed=False,assets_required=False)
    if 'save_log' in build['config']:hardware_manifest['save_log']=build['config']['save_log']
    if not bundle.exists():
        bundle.mkdir();shutil.copy2(d/'app.elf',bundle/'calibration.elf');shutil.copy2(d/'app.disassembly.txt',bundle/'calibration.disassembly.txt')
        (bundle/'SHA256SUMS').write_text(experiments.sha(bundle/'calibration.elf')+'  calibration.elf\n')
        experiments.save(bundle/'manifest.json',hardware_manifest)
        (bundle/'README.txt').write_text('Prepared only; no hardware run or installation occurred.\n'
            'Load calibration.elf as an application under a compatible openfpgaOS Pocket os25 runtime.\n'
            'Use no application arguments. It runs automatically and prints CALINFO, CALPIXELS and 72 CALRESULT rows to stdout.\n'
            'Wait for CALSAVE saved and CALIBRATION PASS, then exit through the Analogue menu.\n'
            'Retrieve Saves/butterscotch/common/calibration_log.sav; text ends at the first NUL.\n'
            'The latest run replaces the dedicated calibration log; game saves are separate.\n'
            'Verify SHA256SUMS and retain the exact ELF alongside the log. Do not infer core identity from variant=0 alone.\n'
            'Normal SDK/musl entry is used on hardware; the separate RTL entry is simulator-only.\n'
            'Physical performance remains unverified. GPU/audio/display/interrupt activity can differ from RTL.\n')
    if experiments.sha(bundle/'calibration.elf')!=experiments.sha(d/'app.elf'):raise ValueError('Hardware and simulated ELF differ')
    if json.loads((bundle/'manifest.json').read_text())!=hardware_manifest:raise ValueError('Hardware provenance changed')
    if experiments.sha(bundle/'calibration.disassembly.txt')!=experiments.sha(d/'app.disassembly.txt'):raise ValueError('Hardware disassembly changed')
    if (bundle/'SHA256SUMS').read_text()!=experiments.sha(d/'app.elf')+'  calibration.elf\n':raise ValueError('Hardware checksum changed')
    overlay=None
    if 'save_log' in build['config']:
        overlay=case/'pocket-overlay';common=overlay/'Assets/butterscotch/common'
        instance=overlay/'Assets/butterscotch/zenibako.Butterscotch09os25/OS25 Calibration.json'
        payload={common/'os25_calibration.elf':d/'app.elf',common/'os25_calibration.ini':case/'calibration/pocket.ini',
                 instance:case/'calibration/pocket-instance.json'}
        if not overlay.exists():
            for destination,source in payload.items():destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,destination)
        for destination,source in payload.items():
            if experiments.sha(destination)!=experiments.sha(source):raise ValueError('Pocket overlay changed: '+str(destination))
        if {p for p in overlay.rglob('*') if p.is_file()}!=set(payload):raise ValueError('Unexpected Pocket overlay payload')
        experiments.save(case/'pocket-overlay-manifest.json',dict(uses_existing_runtime='Butterscotch09os25 / os09.bin',
            elf_sha256=experiments.sha(d/'app.elf'),save_file=SAVE_FILE,save_slot=11,
            files={str(p.relative_to(overlay)):experiments.sha(p) for p in payload},hardware_run_performed=False,sd_card_touched=False))
    evidence=dict(case=str(case.resolve()),elf_sha256=experiments.sha(d/'app.elf'),build_sha256=experiments.sha(d/'build.json'),
        replay_hashes={label:experiments.sha(d/label/'results.json') for label in ['quiet-on','quiet-off','quiet-negative','scanout-on']},
        reference_sha256=experiments.sha(d/'reference.json'),hardware_artifacts={p.name:experiments.sha(p) for p in bundle.iterdir() if p.is_file()},
        analysis_sources={name:experiments.sha(ROOT/name) for name in
            ['calibration.py','cache_profile.py','cache_report.py','pipeline_analysis.py','pipeline_report.py','experiments.py']})
    if overlay:evidence['pocket_overlay_manifest_sha256']=experiments.sha(case/'pocket-overlay-manifest.json')
    experiments.save(d/'results.json',dict(scope='Same ELF calibration; simulated 100 MHz, hardware run pending',
        build=build,evidence=evidence,quiet=summary,scanout=scan_summary,hardware_bundle=str(bundle.resolve()),
        pocket_overlay=str(overlay.resolve()) if overlay else None,
        controls=dict(passive_observer_cycles_identical=True,qemu_negative_rejected=True,rtl_negative_rejected=True,
                      **json.loads((d/'reference.json').read_text()).get('save_checks',{}))))
    table=cache_report.table
    text=['# Identical-binary calibration','',f"Build `{build['config']['id']}`, compiler `{build['compiler_version']}`. "
          'Hardware, QEMU and RTL use the same ELF; hardware execution is pending. All timings are simulated.','',
          table(['Workload','Quiet cycles/op','Scanout cycles/op','Quiet CPI','Quiet I/D refills','Three quiet batch cycle totals'],
                [[s['name'],f"{s['cycles_per_operation']:.3f}",f"{scan_summary[i]['cycles_per_operation']:.3f}",f"{s['cpi']:.3f}",
                  f"{s['refills']['I']}/{s['refills']['D']}",', '.join(map(str,s['batch_cycles']))] for i,s in enumerate(summary)]),
          'An operation is one explicit tested instruction (or one divide+add / conversion-roundtrip group), '
          'one loaded word, one I-cache block, or one sprite call. Loop, call and MMIO boundary overhead remain included. '
          'Do not compare differently defined operations. No validation or logging occurs between measured batches.','',
          table(['Workload','I block/op','D block/op','RAW hold/op','Execute freeze/op','Branch recovery/op','Int→FP freeze/op'],
                [[s['name'],f"{s['i_block']/s['operations']:.3f}",f"{s['d_block']/s['operations']:.3f}",
                  *[f"{s['pipeline']['counts'].get(k,0)/s['operations']:.3f}" for k in
                    ['raw_dependency','execute_freeze','branch_recovery','int_to_fp']]] for s in summary]),
          'These are overlapping observed conditions, including cycles with retirement; do not add them '
          'or interpret them as recoverable time. The machine-readable report also retains instruction '
          'mix, FP/multiply/load dependencies, divider/conversion waits, branch mispredict counts and a '
          'disjoint no-retirement partition using the documented observer priority.','',
          table(['Workload','Quiet I refill cycles min/p50/p90/p99/max','Quiet D refill cycles min/p50/p90/p99/max'],
                [[s['name'],*[('/'.join(str(s['distributions'][k][p]) for p in ['min','p50','p90','p99','max'])
                    if s['distributions'][k]['count'] else 'none') for k in ['I','D']]] for s in summary]),
          'Refill durations run from accepted AXI read to last response. They are transaction latency, '
          'not CPU stall; outstanding transactions can overlap. All three batches are pooled by refill '
          'count when computing quantiles.','',
          'Two byte-identical QEMU reference logs, all numerical/pixel oracles, both quiet and diagnostic '
          'scanout memory checks, identical enabled/disabled-observer quiet cycles, and QEMU/RTL corrupted-oracle '
          'rejection passed. CPU/cache parameters are unchanged. Per-batch histograms, masks and CPI are retained '
          'in the private machine-readable report.','',
          f"ELF SHA-256: `{evidence['elf_sha256']}`. SDK hardware entry `{build['entry']:#x}`; "
          f"bare RTL entry `{build['rtl_entry']:#x}`. Source revision "
          f"`{json.loads((case/'snapshot.json').read_text())['revision']}`. The artifact is an SDK application ELF, "
          'not a replacement FPGA bitstream or SD-card image.','',
          'The generated sprite is deterministic calibration artwork using the real renderer/item-cache '
          'path. It has static geometry and precomputed texture copies, no asset reads or timed allocation. '
          'This does not recreate the original Deltarune checkpoint or establish physical Pocket timing. '
          'Hardware startup uses real musl/SDK ABI; bare RTL skips kernel startup. OS interrupts and actual '
          'display/audio traffic, stack/TLS placement and initial cache state remain unmatched. '
          'Diagnostic scanout is the 80-word, 480/525-line injector.','',
          f"Private hardware deliverable: `{bundle.relative_to(ROOT)}/calibration.elf`. No source checkout, "
          'SDK source or SD card was modified. See [README.md](README.md) for preparation and comparison instructions.','',
          ('This revision saves the latest complete calibration log as NUL-terminated text through save slot 11 '
          '`calibration_log.sav`, after every measurement and oracle check. QEMU saved text matches stdout; '
          'failed-run logging and failure to create the log were checked. Bare RTL skips file writes. '
          'Physical save-slot persistence awaits the device run and exit through the Analogue menu.'
           if 'save_log' in build['config'] else 'This original revision prints to stdout only.'),'']
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text('\n'.join(text));print('VERIFIED CALIBRATION',d/'results.json','HARDWARE',bundle/'calibration.elf',flush=True)

def compare(case,elf,log,core_note):
    d,build,_=checked(case)
    if experiments.sha(elf)!=experiments.sha(d/'app.elf'):raise ValueError('Hardware ELF differs from calibrated ELF')
    actual=parse(log.read_bytes().split(b'\0',1)[0].decode(),'hardware');match_reference(actual,checked_reference(d))
    quiet=verify_replay(case,'quiet-on');scan=verify_replay(case,'scanout-on')
    rows=[]
    for job in range(24):
        physical=[r for r in actual['rows'] if r['job']==job]
        simulated=[r for r in quiet['actual']['rows'] if r['job']==job]
        contended=[r for r in scan['actual']['rows'] if r['job']==job]
        ops=sum(r['operations'] for r in physical);cycles=sum(r['cycles'] for r in physical)
        rtl_cycles=sum(r['cycles'] for r in simulated)
        rows.append(dict(job=job,name=physical[0]['name'] if job<16 else 'sprite-'+STAGES[job-16],
            hardware_cycles_per_operation=cycles/ops,quiet_rtl_cycles_per_operation=rtl_cycles/ops,
            scanout_rtl_cycles_per_operation=sum(r['cycles'] for r in contended)/ops,
            hardware_to_quiet_ratio=cycles/rtl_cycles,hardware_batch_cycles=[r['cycles'] for r in physical]))
    # Preserve supplied evidence locally; never contact or write to the device.
    destination=d/('hardware-'+experiments.sha(log)[:16])
    if destination.exists():raise ValueError('Preserve previous hardware comparison')
    destination.mkdir();shutil.copy2(log,destination/'hardware.log')
    experiments.save(destination/'results.json',dict(rows=rows,hardware=actual,
        elf_sha256=experiments.sha(elf),log_sha256=experiments.sha(log),core_note=core_note,
        core_identity_independently_verified=False,execution_evidence='user-supplied stdout and ELF',
        quiet_result_sha256=experiments.sha(d/'quiet-on/results.json'),scanout_result_sha256=experiments.sha(d/'scanout-on/results.json')))
    (destination/'RESULTS.md').write_text('# Supplied hardware / RTL calibration comparison\n\n'+
        cache_report.table(['Workload','Hardware cycles/op','Quiet RTL cycles/op','Scanout RTL cycles/op','Hardware/quiet'],
            [[r['name'],f"{r['hardware_cycles_per_operation']:.3f}",f"{r['quiet_rtl_cycles_per_operation']:.3f}",
              f"{r['scanout_rtl_cycles_per_operation']:.3f}",f"{r['hardware_to_quiet_ratio']:.3f}"] for r in rows])+\
        '\nSame supplied ELF hash, build ID, 72 numerical results, pixel hash and 100 MHz clock checked. '
        'Device execution/core identity rely on supplied evidence; OS interrupts and display/audio traffic remain unmatched.\n')
    print('VERIFIED supplied hardware comparison',destination/'RESULTS.md',flush=True)

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    new=sub.add_parser('build');new.add_argument('--snapshot',required=True);new.add_argument('--sdk',type=Path,required=True)
    new.add_argument('--platform-result',type=Path,required=True)
    for action in ['reference','replay','analyze','report','compare']:
        q=sub.add_parser(action);q.add_argument('--case',type=Path,required=True)
        if action in ['replay','analyze']:q.add_argument('--traffic',choices=['quiet','scanout'],default='quiet');q.add_argument('--disabled',action='store_true');q.add_argument('--negative',action='store_true')
        if action=='report':q.add_argument('--output',type=Path,default=ROOT/'calibration/RESULTS.md')
        if action=='compare':q.add_argument('--elf',type=Path,required=True);q.add_argument('--log',type=Path,required=True);q.add_argument('--core-note',default='Unverified; confirm os25 core separately')
    a=p.parse_args()
    if a.action=='build':create(a)
    elif a.action=='reference':reference(a.case.resolve())
    elif a.action=='replay':replay(a.case.resolve(),a.traffic,a.disabled,a.negative)
    elif a.action=='analyze':analyze(a.case.resolve(),a.traffic,a.disabled,a.negative)
    elif a.action=='report':report(a.case.resolve(),a.output)
    else:compare(a.case.resolve(),a.elf,a.log,a.core_note)

if __name__=='__main__':main()
