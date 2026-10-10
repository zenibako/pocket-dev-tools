"""Analyze v3 overlapping pipeline observations, preserving old cache schemas."""
from collections import Counter, defaultdict

BITS = ['retired','dispatched','candidate','execute_freeze','i_block','d_block',
        'raw_dependency','load_dependency','multiply_dependency','fp_dependency',
        'fp_reservation','flush_interlock','fence_interlock','store_buffer_wait',
        'integer_divider','fp_divider','fp_sqrt','fp_to_int','int_to_fp','uncached_io',
        'csr','atomic','branch_recovery','branches_resolved','branch_mispredicts',
        'btb_redirect_signal','decoder_redirect_signal']


def opcode(uop):
    op=uop&127
    if op in [3,7]:return 'load'
    if op in [35,39]:return 'store'
    if op in [83,67,71,75,79]:return 'fp_compute'
    if op==51 and uop>>25==1:return 'integer_multiply' if ((uop>>12)&7)<4 else 'integer_divide_rem'
    if op in [99,103,111]:return 'branch_jump'
    if op==115:return 'system_csr'
    return 'other_integer'


def analyze(frames, records, attribution, distribution):
    masks=defaultdict(Counter);blocked=defaultdict(list);retired=defaultdict(list)
    recovery=[];pending=[]
    for row in records:
        kind=row[0];v=list(map(int,row[1:]))
        if kind=='P':
            index,mask,count=v
            if mask<0 or mask>>len(BITS) or count<=0 or mask in masks[index]:
                raise ValueError('Invalid or duplicate pipeline histogram bucket')
            masks[index][mask]=count
        elif kind=='S':blocked[v[0]].append(v[1:])
        elif kind=='T':retired[v[0]].append(v[1:])
        elif kind=='B':recovery.append(v)
        elif kind=='V':pending.append(v)
    if set(masks)!=set(range(len(frames))):raise ValueError('Incomplete pipeline frame histogram')
    functions=defaultdict(Counter)
    for index,f in enumerate(frames):
        hist=masks[index]
        if sum(hist.values())!=f['cycles']:raise ValueError('Pipeline histogram does not account for all cycles')
        counts={name:sum(n for m,n in hist.items() if m&(1<<i)) for i,name in enumerate(BITS)}
        no_retire={name:sum(n for m,n in hist.items() if m&(1<<i) and not m&1) for i,name in enumerate(BITS[3:],3)}
        blocked_total=sum(n for m,n in hist.items() if m&4 and not m&2)
        if sum(v[2] for v in blocked[index])!=blocked_total:raise ValueError('Blocked-PC histogram is incomplete')
        if sum(v[2] for v in retired[index])!=counts['retired']:raise ValueError('Retired-PC histogram is incomplete')
        # Priority is explicit, for reporting a disjoint partition only. Raw bit
        # combinations remain in results.json for any alternative ordering.
        priority=['execute_freeze','d_block','store_buffer_wait','raw_dependency',
                  'fp_reservation','flush_interlock','fence_interlock','i_block','branch_recovery']
        partition=Counter()
        for m,n in hist.items():
            if m&1:label='retirement'
            else:
                label=next((k for k in priority if m&(1<<BITS.index(k))),
                           'candidate_other' if m&4 else 'frontend_or_pipeline_empty')
            partition[label]+=n
        mix=Counter()
        for pc,uop,count in retired[index]:
            functions[attribution.name(pc)]['retired']+=count;mix[opcode(uop)]+=count
        for pc,mask,count in blocked[index]:
            fn=functions[attribution.name(pc)];fn['dispatch_blocked']+=count
            for name in BITS[3:23]:
                if mask&(1<<BITS.index(name)):fn[name]+=count
        episodes=[end-start for pc,start,end in recovery if f['begin']<=start<f['end']]
        if any(f['begin']<=start<f['end'] for pc,start,end in pending):raise ValueError('Unfinished branch recovery in measured frame')
        if len(episodes)!=counts['branch_mispredicts']:raise ValueError('Branch recovery episodes disagree with redirect events')
        f['pipeline']=dict(counts=counts,no_retire_by_source=no_retire,
            cycles_per_retired_instruction=f['cycles']/counts['retired'] if counts['retired'] else None,
            no_retire_cycles=f['cycles']-counts['retired'],dispatch_blocked_cycles=blocked_total,
            instruction_mix=dict(mix),exclusive_partition=dict(partition),
            branch_recovery_cycles=distribution(episodes),
            mask_histogram={str(m):n for m,n in sorted(hist.items())})
    return dict(schema=3,mask_bits=BITS,functions=[dict(name=k,**v) for k,v in sorted(functions.items())],
                retirement_source='PrivilegedPlugin_logic_harts_0_commitMask (CommitService, ctrl5)',
                producer_hazard_equivalence_checked_every_sample=True,
                execution_freeze_source_coverage_checked_every_sample=True)
