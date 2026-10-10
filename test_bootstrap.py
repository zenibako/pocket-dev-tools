"""Exercise import rejection, isolation and link relocation through the CLI."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

CPU = Path('inputs/os/src/fpga/vendor/vexriscv/VexiiRiscv')


class BootstrapTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.dest = self.root / 'checkout'
        self.bundle = self.root / 'snapshot'
        self.dest.mkdir()
        shutil.copy2(Path(__file__).with_name('bootstrap.py'), self.dest / 'bootstrap.py')
        sources = {}
        for name in ['inputs/butterscotch/src/vm.c', 'inputs/sdk/musl/lib/libc.a', 'inputs/os/tools/probe.py']:
            file = self.bundle / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(name.encode())
            sources[name] = self.digest(file)
        manifest = json.dumps({'sources': sources})
        for root in [self.dest, self.bundle]:
            (root / 'input-manifest.json').write_text(manifest)
        cpu = self.bundle / CPU
        cpu.mkdir(parents=True)
        (cpu / 'build.sbt').write_text('pinned generator')
        (cpu / 'VexiiRiscv_os25.v').write_text('pinned netlist')
        lock = {'files': {'build.sbt': {'sha256': self.digest(cpu / 'build.sbt')}},
                'netlist': {'path': 'VexiiRiscv_os25.v', 'sha256': self.digest(cpu / 'VexiiRiscv_os25.v')}}
        (self.dest / 'cpu-lock.json').write_text(json.dumps(lock))

    @staticmethod
    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def run_import(self, *options):
        return subprocess.run([sys.executable, str(self.dest / 'bootstrap.py'), *map(str, options)],
                              capture_output=True, text=True)

    def test_import_copies_without_linking_or_changing_source(self):
        before = self.digest(self.bundle / 'inputs/butterscotch/src/vm.c')
        result = self.run_import('--from-harness', self.bundle)
        self.assertEqual(result.returncode, 0, result.stderr)
        copied = self.dest / 'inputs/butterscotch/src/vm.c'
        self.assertEqual(self.digest(copied), before)
        copied.write_text('experiment')
        self.assertEqual(self.digest(self.bundle / 'inputs/butterscotch/src/vm.c'), before)

    def test_bad_hash_leaves_destination_uninstalled(self):
        (self.bundle / 'inputs/os/tools/probe.py').write_text('unexpected change')
        result = self.run_import('--from-harness', self.bundle)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.dest / 'inputs').exists())
        self.assertEqual(list(self.dest.glob('.bootstrap-*')), [])

    def test_existing_inputs_are_preserved(self):
        (self.dest / 'inputs').mkdir()
        sentinel = self.dest / 'inputs/keep'
        sentinel.write_text('local experiment')
        result = self.run_import('--from-harness', self.bundle)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(sentinel.read_text(), 'local experiment')

    def test_external_input_link_is_rejected(self):
        source = self.bundle / 'inputs/butterscotch/src/vm.c'
        external = self.root / 'outside.c'
        external.write_bytes(source.read_bytes())
        source.unlink()
        source.symlink_to(external)
        result = self.run_import('--from-harness', self.bundle)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('escapes', result.stderr)
        self.assertFalse((self.dest / 'inputs').exists())

    def test_evidence_links_are_rebased_inside_destination(self):
        build = self.bundle / 'build'
        build.mkdir()
        (build / 'asset').symlink_to(self.bundle / 'inputs/butterscotch/src/vm.c')
        result = self.run_import('--from-harness', self.bundle, '--with-evidence')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.dest / 'build/asset').resolve(), (self.dest / 'inputs/butterscotch/src/vm.c').resolve())
        self.assertFalse((self.dest / 'build/asset').readlink().is_absolute())

    def test_bad_cpu_or_netlist_is_rejected(self):
        for name in ['build.sbt', 'VexiiRiscv_os25.v']:
            with self.subTest(name=name):
                file = self.bundle / CPU / name
                original = file.read_bytes()
                file.write_text('unexpected change')
                result = self.run_import('--from-harness', self.bundle)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((self.dest / 'inputs').exists())
                file.write_bytes(original)

    def test_component_sources_with_private_sdk_fallback(self):
        private = self.root / 'private'
        shutil.copytree(self.bundle / 'inputs', private)
        (self.bundle / 'inputs/sdk/musl/lib/libc.a').unlink()
        result = self.run_import('--butterscotch', self.bundle / 'inputs/butterscotch',
                                 '--os', self.bundle / 'inputs/os', '--sdk', self.bundle / 'inputs/sdk',
                                 '--cpu', self.bundle / CPU, '--private-inputs', private)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.digest(self.dest / 'inputs/sdk/musl/lib/libc.a'),
                         self.digest(private / 'sdk/musl/lib/libc.a'))


if __name__ == '__main__':
    unittest.main()
