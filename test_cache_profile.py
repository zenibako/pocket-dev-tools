import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import cache_profile


class CacheObserverTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)

    def test_real_monitor_handles_backpressure_ids_overlap_and_exact_boundaries(self):
        fields=[]
        for cache in ['i','d']:
            fields.extend(f'unsigned cp_{cache}_{name}=0;' for name in
                          ['arvalid','arready','araddr','arid','arlen','rvalid','rready','rid','rlast','rresp'])
        fields.extend('unsigned cp_'+name+'=0;' for name in
                      ['i_hold','i_pc','i_miss','i_resume','i_miss_pc','d_wait','commit','clock_cmd','clock_pc','clock_latch','counter'])
        code='#include "'+str(cache_profile.ROOT/'cacheprobe/monitor.hpp')+'"\n'
        code+='struct Pins {'+''.join(fields)+'};\n'
        code+='''int main(){
          setenv("CACHE_PROFILE","1",1);setenv("CACHE_BEGIN_LO","1000",1);setenv("CACHE_BEGIN_HI","1100",1);
          setenv("CACHE_END_LO","2000",1);setenv("CACHE_END_HI","2100",1);
          CacheMonitor monitor;monitor.init();
          for(unsigned c=100;c<=220;c++){
            Pins p;p.cp_counter=c;
            if(c==100 || c==160 || c==200){p.cp_clock_cmd=p.cp_clock_latch=1;p.cp_clock_pc=1001;}
            if(c==125 || c==180 || c==220){p.cp_clock_cmd=p.cp_clock_latch=1;p.cp_clock_pc=2001;}
            if(c==101 || c==102){p.cp_i_arvalid=1;p.cp_i_arready=c==102;p.cp_i_arlen=15;p.cp_i_araddr=0x10400000;}
            if(c==103){p.cp_i_arvalid=p.cp_i_arready=1;p.cp_i_arid=1;p.cp_i_arlen=15;p.cp_i_araddr=0x10400040;}
            // ID 1 returns before ID 0, and ID 0 crosses the frame boundary.
            if(c>=104 && c<=135){p.cp_i_rvalid=p.cp_i_rready=1;p.cp_i_rid=c<=119;p.cp_i_rlast=c==119 || c==135;}
            if(c==107){p.cp_d_arvalid=p.cp_d_arready=1;p.cp_d_arlen=15;p.cp_d_araddr=0x11000000;}
            if(c>=108 && c<=123){p.cp_d_rvalid=p.cp_d_rready=1;p.cp_d_rlast=c==123;}
            p.cp_i_miss=c==104;p.cp_i_miss_pc=0x10400004;
            p.cp_i_resume=c==114;
            p.cp_i_hold=c>=105 && c<=111;p.cp_i_pc=0x10400004;
            p.cp_d_wait=c>=108 && c<=112;p.cp_commit=c==110;
            monitor.sample(p);
          }
          monitor.finish();
        }'''
        (self.root/'test.cpp').write_text(code)
        subprocess.run(['clang++','-std=c++17','-O2',str(self.root/'test.cpp'),'-o',str(self.root/'test')],check=True)
        subprocess.run([str(self.root/'test')],cwd=self.root,check=True)
        rows=[dict(cycles=n,oracle=[3323+i]) for i,n in enumerate([25,20,20])]
        profile=cache_profile.parse(self.root/'cache-profile.csv',rows,
            [dict(name='first',address=0x10400000,size=64),dict(name='second',address=0x10400040,size=64)])
        # Stale/shifted boundaries and a missing PC bucket must fail analysis.
        raw=(self.root/'cache-profile.csv').read_text()
        changed=list(rows);changed[0]=dict(cycles=26,oracle=[3323])
        with self.assertRaisesRegex(ValueError,'interval disagrees'):
            cache_profile.parse(self.root/'cache-profile.csv',changed,[])
        (self.root/'cache-profile.csv').write_text('\n'.join(line for line in raw.splitlines() if not line.startswith('H,0,')))
        with self.assertRaisesRegex(ValueError,'histogram'):
            cache_profile.parse(self.root/'cache-profile.csv',rows,[])
        (self.root/'cache-profile.csv').write_text(raw)
        first=profile['frames'][0]
        self.assertEqual((first['i_block_cycles'],first['d_block_cycles'],first['overlap_cycles']),(10,5,5))
        self.assertEqual(first['union_block_cycles'],10)
        self.assertEqual(first['i_fetch_hold_cycles'],7)
        self.assertEqual(first['i_miss_wait_cycles'],10)
        self.assertEqual(first['i_miss_events'],1)
        self.assertEqual(first['i_block_no_commit_cycles'],9)
        self.assertEqual(first['i_miss_recovery_cycles']['histogram'],{'10':1})
        self.assertEqual(first['I']['refill_count'],2)
        self.assertEqual(first['I']['ar_backpressure_cycles']['max'],1)
        self.assertEqual(first['I']['accepted_to_last_cycles']['histogram'],{'17':1,'34':1})
        self.assertEqual(first['I']['right_boundary_transfers'],1)
        self.assertEqual(first['I']['outstanding_union_cycles'],24)
        self.assertEqual(profile['top30_by_block_cycles'][0]['name'],'first')

    def test_unattributed_padding_is_not_assigned_to_nearest_function(self):
        lookup=cache_profile.Attribution([dict(name='f',address=0x1004,size=4)])
        self.assertEqual(lookup.name(0x1005),'f')
        self.assertEqual(lookup.name(0x1000),'<padding or no function symbol>')
        self.assertEqual(lookup.name(0x1008),'<padding or no function symbol>')

    def test_pooled_quantiles_weight_refills_instead_of_frame_percentiles(self):
        import cache_report
        frames=[{'I':{'latency':{'histogram':{'3':99}}}},
                {'I':{'latency':{'histogram':{'300':1}}}}]
        d=cache_report.pooled_distribution(frames,'I','latency')
        self.assertEqual((d['count'],d['p50'],d['p90'],d['p99'],d['max']),(100,3,3,3,300))
        self.assertEqual(d['histogram'],{'3':99,'300':1})

    def test_distribution_preserves_tail_and_concurrent_union(self):
        d=cache_profile.distribution([3,3,3,300])
        self.assertEqual(d['histogram'],{'3':3,'300':1})
        self.assertEqual(d['max'],300)
        self.assertEqual(cache_profile.union_cycles([(0,10),(3,12),(15,20)],5,18),10)

    def test_cached_observer_cannot_replace_a_different_platform(self):
        metadata=dict(generator_sha256='generator-a',leaf_rtl_sha256='rtl-a')
        cache_profile.compatible_platform(metadata,metadata)
        for key in metadata:
            other=dict(metadata);other[key]='different'
            with self.assertRaisesRegex(ValueError,'platform differs'):
                cache_profile.compatible_platform(metadata,other)

    def test_function_rankings_keep_padding_separate_and_share_denominator_complete(self):
        import cache_report
        functions=[dict(name=name,refills=n,i_block_cycles=n) for name,n in
                   [('f',10),('<padding or no function symbol>',90),('g',1)]]
        ranks=cache_report.function_rankings(dict(functions=functions,total_frame_cycles=1000))
        self.assertEqual([f['name'] for f in ranks['top30_by_refills']],['f','g'])
        self.assertEqual(len(ranks['unattributed']),1)
        self.assertAlmostEqual(ranks['top30_refill_count_share_percent'],11/101*100)


if __name__=='__main__':unittest.main()
