#!/usr/bin/env python3
"""Passively profile cache refills in isolated copies of existing frame cases."""
import argparse
from bisect import bisect_right
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import experiments

ROOT=experiments.ROOT
PRIVATE=ROOT/'experiments/cache-profiles'


def symbols(elf):
    command=shutil.which('riscv64-elf-readelf') or '/opt/homebrew/bin/riscv64-elf-readelf'
    text=subprocess.check_output([command,'-Ws','--wide',str(elf)],text=True)
    functions=[]
    for line in text.splitlines():
        fields=line.split()
        if len(fields)>=8 and fields[3]=='FUNC' and fields[6]!='UND':
            address=int(fields[1],16)
            size=int(fields[2],0)
            if size:functions.append(dict(address=address,size=size,name=fields[7]))
    if not functions:raise ValueError('ELF has no sized function symbols')
    return sorted(functions,key=lambda f:(f['address'],f['name']))


class Attribution:
    def __init__(self, functions):
        grouped=defaultdict(list)
        for f in functions:grouped[f['address']].append(f)
        self.functions=[]
        for address,aliases in sorted(grouped.items()):
            self.functions.append(dict(address=address,size=max(f['size'] for f in aliases),
                                       name=' / '.join(sorted({f['name'] for f in aliases}))))
        self.starts=[f['address'] for f in self.functions]

    def name(self, address):
        index=bisect_right(self.starts,address)-1
        if index>=0:
            f=self.functions[index]
            if address<f['address']+f['size']:return f['name']
        return '<padding or no function symbol>'


def distribution(values):
    if not values:return dict(count=0,histogram={})
    ordered=sorted(values)
    return dict(count=len(values),min=ordered[0],mean=sum(values)/len(values),
                p50=ordered[(len(values)-1)*50//100],p90=ordered[(len(values)-1)*90//100],
                p99=ordered[(len(values)-1)*99//100],max=ordered[-1],
                histogram={str(k):v for k,v in sorted(Counter(values).items())})


def union_cycles(intervals, begin, end):
    total=0;cursor=begin
    for lo,hi in sorted(intervals):
        lo=max(begin,lo);hi=min(end,hi)
        if hi>max(cursor,lo):total+=hi-max(cursor,lo)
        cursor=max(cursor,hi)
    return total


def parse(path, expected, function_symbols):
    frames=[];holds=defaultdict(list);refills=[];unfinished=[];recoveries=[];pending_misses=[]
    for row in csv.reader(path.read_text().splitlines()):
        if not row or row[0].startswith('#'):continue
        if row[0]=='F':
            values=list(map(int,row[1:]))
            keys=['index','begin','end','cycles','i_block_cycles','d_block_cycles','overlap_cycles',
                  'i_block_no_commit_cycles','d_block_no_commit_cycles','overlap_no_commit_cycles','commit_pulses',
                  'i_fetch_hold_cycles','i_miss_wait_cycles','i_miss_events']
            if len(values)!=len(keys):raise ValueError('Cache profile frame schema mismatch')
            frames.append(dict(zip(keys,values)))
        elif row[0] in ['M','W']:
            item=dict(zip(['pc','miss','resume'],map(int,row[1:])))
            (recoveries if row[0]=='M' else pending_misses).append(item)
        elif row[0]=='H':holds[int(row[1])].append(tuple(map(int,row[2:])))
        elif row[0] in ['R','U']:
            keys=['address','id','offer','accept','first','last','beats']
            item=dict(zip(keys,map(int,row[2:])));item['cache']=row[1]
            (refills if row[0]=='R' else unfinished).append(item)
        else:raise ValueError('Unknown cache profile record')
    if len(frames)!=len(expected) or len(frames)!=3:raise ValueError('Incomplete cache profile window')
    attribution=Attribution(function_symbols)
    aggregate=defaultdict(lambda:dict(refills=0,transaction_cycles=0,i_block_cycles=0,i_block_no_commit_cycles=0))
    address_histogram=defaultdict(Counter)
    for index,(frame,expected_row) in enumerate(zip(frames,expected)):
        if frame['index']!=index or frame['cycles']!=frame['end']-frame['begin'] or frame['cycles']!=expected_row['cycles']:
            raise ValueError('Observer interval disagrees with firmware cycle timing')
        frame['frame']=expected_row['oracle'][0]
        if any(frame['begin']<=m['miss']<frame['end'] for m in pending_misses):
            raise ValueError('Uncompleted I-cache miss recovery in measured frame')
        frame['i_miss_recovery_cycles']=distribution([m['resume']-m['miss'] for m in recoveries
                                                     if frame['begin']<=m['miss']<frame['end']])
        if sum(h[1] for h in holds[index])!=frame['i_block_cycles']:
            raise ValueError('Fetch-PC histogram does not account for all I-cache blocked cycles')
        for pc,count,no_commit in holds[index]:
            f=aggregate[attribution.name(pc)]
            f['i_block_cycles']+=count;f['i_block_no_commit_cycles']+=no_commit
        frame['union_block_cycles']=frame['i_block_cycles']+frame['d_block_cycles']-frame['overlap_cycles']
        frame['union_no_commit_cycles']=frame['i_block_no_commit_cycles']+frame['d_block_no_commit_cycles']-frame['overlap_no_commit_cycles']
        for cache in ['I','D']:
            all_transfers=[r for r in refills if r['cache']==cache]
            accepted=[r for r in all_transfers if frame['begin']<=r['accept']<frame['end']]
            if any(r['beats']!=16 or r['address']%64 for r in accepted):
                raise ValueError('Observed cached read is not a 64-byte line refill')
            censored=[r for r in unfinished if r['cache']==cache and frame['begin']<=r['accept']<frame['end']]
            if censored:raise ValueError('Frame refill distribution has uncompleted transfers')
            latency=[r['last']-r['accept']+1 for r in accepted]
            first=[r['first']-r['accept']+1 for r in accepted]
            queue=[r['accept']-r['offer'] for r in accepted]
            frame[cache]=dict(refill_count=len(accepted),
                accepted_to_last_cycles=distribution(latency),accepted_to_first_cycles=distribution(first),
                ar_backpressure_cycles=distribution(queue),
                refill_service_cycle_sum=sum(latency),
                outstanding_union_cycles=union_cycles([(r['offer'],r['last']+1) for r in all_transfers],frame['begin'],frame['end']),
                left_boundary_transfers=sum(r['offer']<frame['begin']<=r['last'] for r in all_transfers),
                right_boundary_transfers=sum(r['accept']<frame['end']<=r['last'] for r in all_transfers))
            if cache=='I':
                for r,n in zip(accepted,latency):
                    f=aggregate[attribution.name(r['address'])];f['refills']+=1;f['transaction_cycles']+=n
                    address_histogram[r['address']]['refills']+=1
                    address_histogram[r['address']]['transaction_cycles']+=n
    total=sum(f['cycles'] for f in frames)
    functions=[dict(name=name,**values,frame_share_percent=values['i_block_cycles']/total*100)
               for name,values in aggregate.items()]
    by_refills=sorted(functions,key=lambda f:(-f['refills'],f['name']))[:30]
    by_stalls=sorted(functions,key=lambda f:(-f['i_block_cycles'],f['name']))[:30]
    return dict(frames=frames,total_frame_cycles=total,functions=functions,
        i_address_histogram=[dict(address=hex(addr),function=attribution.name(addr),**counts)
                             for addr,counts in sorted(address_histogram.items())],
        top30_by_refills=by_refills,top30_by_block_cycles=by_stalls,
        top30_refill_count_share_percent=sum(f['refills'] for f in by_refills)/max(1,sum(f['refills'] for f in functions))*100,
        top30_by_refills_frame_share_percent=sum(f['i_block_cycles'] for f in by_refills)/total*100,
        top30_by_block_cycles_frame_share_percent=sum(f['i_block_cycles'] for f in by_stalls)/total*100,
        limits=['Refill transactions include speculative/prefetch traffic, not just demand misses.',
                'I block is the union of valid stage-1 fetch holdHarts and a shadow of FetchL1 onEvents.waiting.',
                'The shadow includes fetch miss REDO/flush/retry until any valid non-trapped stage-3 fetch; not pure SDRAM wait.',
                'D block is the LSU refill waiter halting dispatch; excludes other store-buffer or writeback stalls.',
                'Block cycles can overlap and instructions can still commit during a frontend/dispatch block.',
                'No-commit overlap is observational, not uniquely causal lost execution cycles.',
                'Service latency is accepted AR through accepted RLAST, inclusive; concurrent sums are not frame stall.',
                'Refill count attributed by 64-byte line base; I block attributed to episode initiating miss PC or held fetch PC.',
                'Line bases in padding and missing symbols remain in an explicit unattributed bucket.'])


def observer_hash():
    files={str(p.relative_to(ROOT)):experiments.sha(p) for p in (ROOT/'cacheprobe').iterdir() if p.is_file() and p.suffix in ['.py','.hpp','.vh']}
    return hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()[:16]


def compatible_platform(source_metadata, observer_metadata):
    for field in ['generator_sha256','leaf_rtl_sha256']:
        if source_metadata[field]!=observer_metadata[field]:
            raise ValueError('Cached observer platform differs from source case: '+field)


def run(args):
    source=args.case.resolve()
    if not source.is_relative_to((ROOT/'experiments/cases').resolve()):raise ValueError('Source must be an isolated experiment case')
    config,directory,capture=experiments.checked_capture(source)
    old=json.loads((directory/(args.traffic+'-results.json')).read_text())
    functions=symbols(directory/'program.elf')
    bounds={f['name']:f for f in functions}
    version=observer_hash()
    platform=PRIVATE/('platform-'+version)
    if not platform.exists():
        experiments.copy_tree(source,platform)
        shutil.copytree(ROOT/'cacheprobe',platform/'cacheprobe',ignore=shutil.ignore_patterns('__pycache__'))
    if not (platform/'build/cacheprobe/compile-ready.json').exists():
        subprocess.run(experiments.docker(platform,'python3','cacheprobe/rtl.py'),check=True)
        experiments.save(platform/'build/cacheprobe/compile-ready.json',dict(observer=version))
    compatible_platform(json.loads((source/'build/fullframe/rtl/rtl.json').read_text()),
                        json.loads((platform/'build/fullframe/rtl/rtl.json').read_text()))
    suffix='negative' if args.negative else 'on' if not args.disabled else 'off'
    root=PRIVATE/(source.name+'-'+version+'-'+args.traffic+'-'+suffix)
    if root.exists():raise ValueError('Profile output exists; preserve it and choose another source case or observer version')
    experiments.copy_tree(source,root)
    shutil.copytree(ROOT/'cacheprobe',root/'cacheprobe',ignore=shutil.ignore_patterns('__pycache__'))
    for name in ['main.cpp','rtl.json','obj/Vtb_system']:
        shutil.copy2(platform/'build/fullframe/rtl'/name,root/'build/fullframe/rtl'/name)
    experiments.copy_tree(platform/'build/cacheprobe',root/'build/cacheprobe')
    cmd=experiments.docker(root,'python3','fullframe/rtl.py','run','--game',config['game'],
                          '--variant',config['variant'],'--traffic',args.traffic,
                          *(['--negative'] if args.negative else []))
    env=['CACHE_PROFILE='+str(int(not args.disabled)),
         *[f'CACHE_{key}_{side}={bounds[name]["address"]+(bounds[name]["size"] if side=="HI" else 0)}'
           for key,name in [('BEGIN','frame_begin'),('END','frame_end')] for side in ['LO','HI']]]
    # Place Docker environment options before its image name.
    image=cmd.index('undertale-vm-os25-frames:local')
    cmd[image:image]=[item for value in env for item in ['-e',value]]
    subprocess.run(cmd,check=True)
    target=root/'build/fullframe'/config['game']/config['variant']
    result_path=target/('negative-results.json' if args.negative else args.traffic+'-results.json')
    result=json.loads(result_path.read_text())
    if not args.negative and result['rows']!=old['rows']:
        raise ValueError('Passive observer changed frame timing or oracle values')
    profile=None
    if not args.disabled and not args.negative:
        profile=parse(target/'cache-profile.csv',result['rows'],functions)
    result['cache_profile']=dict(enabled=not args.disabled,source_case=str(source),
        source_result_sha256=experiments.sha(directory/(args.traffic+'-results.json')),
        observer_version=version,analyzer_sha256=experiments.sha(ROOT/'cache_profile.py'),clock_bounds={name:bounds[name] for name in ['frame_begin','frame_end']},
        unchanged_frame_cycles_and_oracles=not args.negative,
        raw_sha256=experiments.sha(target/'cache-profile.csv') if not args.disabled else None,
        elf_sha256=experiments.sha(target/'program.elf'),profile=profile)
    experiments.save(result_path,result)
    experiments.verify_inputs(root)
    print('PROFILE',result_path.resolve(),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case',type=Path,required=True)
    parser.add_argument('--traffic',choices=['quiet','scanout'],default='quiet')
    parser.add_argument('--disabled',action='store_true')
    parser.add_argument('--negative',action='store_true')
    run(parser.parse_args())


if __name__=='__main__':main()
