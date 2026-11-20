import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import runtimes

ROOT = Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


class RuntimeLockTests(unittest.TestCase):
    def test_committed_lock_names_both_platforms_at_100_mhz(self):
        lock = json.loads((ROOT / 'runtimes/pocket-runtime-19d9d50.json').read_text())
        self.assertRegex(lock['commit'], r'^[0-9a-f]{40}$')
        self.assertEqual(set(lock['platforms']), {'rt-os25', 'rt-os20'})
        for name, entry in lock['platforms'].items():
            self.assertEqual(entry['clock_hz'], 100000000)
            self.assertEqual(entry['variant'], name.removeprefix('rt-'))
            self.assertRegex(entry['netlist_sha256'], r'^[0-9a-f]{64}$')
        self.assertTrue(all(name.startswith(tuple(lock['export'])) for name in lock['sources']))
        self.assertIn('src/fpga/targets/pocket/variants/os20.mk', lock['sources'])

    def test_frozen_default_cannot_be_shadowed(self):
        self.assertNotIn('os25', runtimes.platforms())


class RuntimeImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.core = self.root / 'core'
        (self.core / 'src/fpga').mkdir(parents=True)
        (self.core / 'src/fpga/top.v').write_text('module top; endmodule\n')
        (self.core / 'unrelated.txt').write_text('not exported\n')
        git = ['git', '-C', str(self.core), '-c', 'user.name=t', '-c', 'user.email=t@example.invalid',
               '-c', 'commit.gpgsign=false']
        subprocess.run(['git', 'init', '-q', str(self.core)], check=True)
        subprocess.run([*git, 'add', '-A'], check=True)
        subprocess.run([*git, 'commit', '-q', '-m', 'fixture'], check=True)
        commit = subprocess.check_output(['git', '-C', str(self.core), 'rev-parse', 'HEAD'], text=True).strip()
        self.netlists = self.root / 'netlists'
        self.netlists.mkdir()
        (self.netlists / 'VexiiRiscv_os20.v').write_text('module VexiiRiscv; endmodule\n')
        self.locks = self.root / 'runtimes'
        self.locks.mkdir()
        self.lock = dict(commit=commit, export=['src/fpga'],
                         sources={'src/fpga/top.v': digest(b'module top; endmodule\n')},
                         platforms={'rt-test': dict(variant='os20', clock_hz=100000000, netlist='VexiiRiscv_os20.v',
                                                    netlist_sha256=digest(b'module VexiiRiscv; endmodule\n'))})
        (self.locks / 'fixture.json').write_text(json.dumps(self.lock))
        self.patch = patch.object(runtimes, 'LOCKS', self.locks)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.temp.cleanup()

    def test_import_exports_only_pinned_paths_and_verifies(self):
        runtimes.import_runtime('fixture', self.core, self.netlists)
        tree = runtimes.tree('fixture')
        self.assertTrue((tree / 'src/fpga/top.v').is_file())
        self.assertFalse((tree / 'unrelated.txt').exists())
        self.assertEqual(runtimes.verify('fixture'), tree)
        self.assertEqual(runtimes.platforms()['rt-test'][0], 'fixture')

    def test_wrong_netlist_is_rejected_without_a_tree(self):
        (self.netlists / 'VexiiRiscv_os20.v').write_text('module Other; endmodule\n')
        with self.assertRaisesRegex(ValueError, 'pinned netlist'):
            runtimes.import_runtime('fixture', self.core, self.netlists)
        self.assertFalse(runtimes.tree('fixture').exists())

    def test_changed_source_fails_verification(self):
        runtimes.import_runtime('fixture', self.core, self.netlists)
        (runtimes.tree('fixture') / 'src/fpga/top.v').write_text('module changed; endmodule\n')
        with self.assertRaisesRegex(ValueError, 'source changed'):
            runtimes.verify('fixture')

    def test_existing_tree_is_preserved(self):
        runtimes.import_runtime('fixture', self.core, self.netlists)
        with self.assertRaisesRegex(ValueError, 'exists'):
            runtimes.import_runtime('fixture', self.core, self.netlists)


if __name__ == '__main__':
    unittest.main()
