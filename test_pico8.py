"""Benchmark seed, variable replay window and GC accounting contracts."""
import importlib.util
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest

PICO = Path(__file__).parent / 'pico8'
sys.path.insert(0, str(PICO))
import route
import snapshot
# Avoid stdlib's trace module in test runners that imported it earlier.
spec = importlib.util.spec_from_file_location('pico_trace', PICO / 'gc_trace.py')
trace = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trace)


class BenchmarkTests(unittest.TestCase):
    def test_compiled_gc_scopes(self):
        with tempfile.TemporaryDirectory() as root:
            program = str(Path(root)/'scope-test')
            subprocess.run(['c++','-std=c++17','-I'+str(PICO),str(PICO/'trace-scope-test.cpp'),'-o',program],check=True)
            subprocess.run([program],check=True)

    def test_seed_zero_and_full_uint32_range(self):
        for seed in [0, 0x5eed1234, 0xffffffff]:
            self.assertEqual(route.validate(None, 'seed7', seed)['hash_seed'], seed)
        for seed in [-1, 1 << 32, True, '7']:
            with self.assertRaises(ValueError): route.validate(None, 'seed7', seed)
        self.assertEqual(route.validate(None, 'seed7'), {})

    def test_missing_seed_hook_rejects_build(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root); folder = root / 'pico8'; folder.mkdir()
            (folder/'route.json').write_text(json.dumps({'hash_seed':0}))
            source = root/'source/.deps/fake-08/libs/z8lua/lstate.c'
            source.parent.mkdir(parents=True); source.write_text('g->seed = makeseed(L);')
            with self.assertRaises(ValueError): route.flags(folder)
            source.write_text('#ifdef P8P_BENCH_HASH_SEED\n')
            self.assertIn('-DP8P_BENCH_HASH_SEED=0u', route.flags(folder))

    def test_windows_and_trace_need_seed(self):
        self.assertEqual(route.validate(None,'seed7',0,180,12,600,True)['measured_frames'],12)
        for params in [(180,0,600),(180,61,600),(599,3,600),(-1,3,600)]:
            with self.assertRaises(ValueError): route.validate(None,'seed7',0,*params)
        with self.assertRaises(ValueError): route.validate(None,'seed7',trace_gc=True)

    def test_source_hook_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'source.c';path.write_text('anchor anchor')
            with self.assertRaises(ValueError): snapshot.replace_once(path,'anchor','replacement')
            self.assertEqual(path.read_text(),'anchor anchor')

    def test_gc_overlap_and_phase_accounting(self):
        with tempfile.TemporaryDirectory() as root:
            log=Path(root)/'trace.log'
            row=dict.fromkeys(trace.FIELDS,0)
            row.update(frame=180,alloc_time=30,alloc_gc_time=10,gc_time=100,gc_setup=40,gc_draw=60)
            def write(): log.write_text('PICOGC '+' '.join(str(row[k]) for k in trace.FIELDS)+'\n')
            write();self.assertEqual(trace.read(log,1,180)[0],row)
            raw=log.read_text();log.write_text(raw+'=== UART BEGIN ===\n'+raw+'\n=== UART END ===\n')
            self.assertEqual(trace.read(log,1,180)[0],row)
            row['gc_setup']=41;write()
            with self.assertRaises(ValueError): trace.read(log,1,180)
            row['gc_setup']=40;row['alloc_gc_time']=31;write()
            with self.assertRaises(ValueError): trace.read(log,1,180)

    def test_native_times_excluded_from_repeat_comparison(self):
        a=dict.fromkeys(trace.FIELDS,0);b=dict(a)
        b.update(frame_time=500,gc_draw=100,alloc_time=40)
        self.assertEqual(trace.counters([a]),trace.counters([b]))
        b['new_calls']=1;self.assertNotEqual(trace.counters([a]),trace.counters([b]))


if __name__ == '__main__': unittest.main()
