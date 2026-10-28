"""Link and execute the actual startup transfer across near and far sections."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'bench/start.S').is_file())


class StartupRangeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compiler = next((path for name in ['riscv64-unknown-elf-gcc', 'riscv32-unknown-elf-gcc', 'riscv64-elf-gcc']
                             if (path := shutil.which(name))), None)
        cls.qemu = shutil.which('qemu-riscv32')
        cls.objcopy = shutil.which(cls.compiler.removesuffix('gcc') + 'objcopy') if cls.compiler else None
        if not cls.compiler or not cls.objcopy or not cls.qemu:
            raise unittest.SkipTest('RV32 GCC, objcopy and QEMU user tools required; run with the isolated toolchain launcher')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name)
        self.source = Path(os.environ.get('HARNESS_STARTUP_SOURCE', str(ROOT / 'bench/start.S')))
        self.count = 0

    def link(self, source, current, far):
        self.count += 1
        directory = self.out / str(self.count)
        directory.mkdir()
        command = [self.compiler, '-march=rv32imafc_zicsr_zifencei', '-mabi=ilp32f']
        preprocessed = subprocess.run([*command, '-E', '-P', '-x', 'assembler-with-cpp',
                                      '-DFRAME_CURRENT_PORT=' + str(current), '-DFRAME_FB_UNCACHED=0', str(source)],
                                     capture_output=True, text=True, check=True).stdout
        # Enter at the actual reset transfer, after its privileged/MMIO setup.
        # The real frame_restore body must restore a saved return and reach PASS.
        expression = r'(?m)^([ \t]*)(?:j|tail) frame_restore[ \t]*$'
        self.assertEqual(len(re.findall(expression, preprocessed)), 1)
        preprocessed = re.sub(expression, '.global startup_jump_probe\nstartup_jump_probe:\n\\g<0>', preprocessed)
        assembly = directory / 'startup.S'
        assembly.write_text(preprocessed)
        helper = directory / 'probe.S'
        helper.write_text(r'''
.section .probe_entry,"ax"
.global _probe_start
_probe_start:
  la t0, frame_context
  la t1, probe_pass
  sw t1, 0(t0)
  sw sp, 4(t0)
  tail startup_jump_probe
probe_pass:
  li a0, 0
  li a7, 93
  ecall
.section .probe_helper,"ax"
.global frame_host_main, frame_checkpoint, frame_trap_report
frame_host_main:
frame_checkpoint:
  ret
frame_trap_report:
  li a0, 92
  li a7, 93
  ecall
.section .data
.global frame_host
frame_host: .word 1
.section .bss
.balign 16
.global frame_context, frame_tls
frame_context: .zero 256
frame_tls: .zero 4096
''')
        script = directory / 'probe.ld'
        script.write_text('''ENTRY(_probe_start)
SECTIONS {
 . = 0x10400000;
 .probe_entry : { *(.probe_entry) }
 .text.start : { *(.text.start) }
 .probe_helper : { *(.probe_helper) }
 . = ''' + ('0x10600000' if far else '0x10400800') + ''';
 .text.host_boot : { *(.text.host_boot) }
 .data : { *(.data*) }
 __global_pointer$ = . + 0x800;
 .bss : { *(.bss*) }
 __frame_heap_start = .;
}
''')
        elf = directory / 'probe.elf'
        linked = subprocess.run([*command, '-nostdlib', '-nostartfiles', str(assembly), str(helper),
                                 '-Wl,--no-relax', '-Wl,-T,' + str(script), '-o', str(elf)],
                                capture_output=True, text=True)
        return linked, elf

    def assert_runs(self, linked, elf):
        self.assertEqual(linked.returncode, 0, linked.stderr)
        executed = subprocess.run([self.qemu, '-B', '0x100000000', str(elf)],
                                  capture_output=True, text=True, timeout=10)
        self.assertEqual(executed.returncode, 0, executed.stdout + executed.stderr)

    def test_current_near_transfer_restores_saved_return(self):
        self.assert_runs(*self.link(self.source, current=1, far=False))

    def test_current_far_transfer_restores_saved_return(self):
        self.assert_runs(*self.link(self.source, current=1, far=True))

    def test_legacy_near_transfer_keeps_original_instruction_bytes(self):
        linked, elf = self.link(self.source, current=0, far=False)
        self.assert_runs(linked, elf)
        old_linked, old_elf = self.link(ROOT / 'fullframe/start.S', current=0, far=False)
        self.assert_runs(old_linked, old_elf)
        binaries = []
        for path in [elf, old_elf]:
            binary = path.with_suffix('.bin')
            subprocess.run([self.objcopy, '-O', 'binary', '--only-section=.text.start', str(path), str(binary)], check=True)
            binaries.append(binary.read_bytes())
        self.assertEqual(binaries[0], binaries[1], 'Historical reset instruction bytes changed')

    def test_legacy_far_transfer_retains_original_range_limit(self):
        linked, _ = self.link(self.source, current=0, far=True)
        self.assertNotEqual(linked.returncode, 0)
        self.assertIn('relocation truncated', linked.stderr)


if __name__ == '__main__':
    unittest.main()
