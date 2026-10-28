"""Behavioral checks for the isolated historical/current port adapter."""
import ast
import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('bench_build', ROOT / 'bench/build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class AdapterTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.src = self.root / 'src'
        self.port = self.src / 'openfpga'
        self.vendor = self.root / 'vendor'
        self.port.mkdir(parents=True)
        self.vendor.mkdir()
        self.out = self.root / 'output'
        self.out.mkdir()
        for name, value in [('SRC', self.src), ('PORT', self.port), ('VENDOR', self.vendor)]:
            p = patch.object(build.capture, name, value)
            p.start()
            self.addCleanup(p.stop)

    def file(self, name, contents=''):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(contents)
        return p

    def compile_run(self, source, flags=()):
        compiler = shutil.which('clang') or shutil.which('cc')
        self.assertIsNotNone(compiler, 'A host C compiler is required for adapter behavior tests')
        c = self.out / 'test.c'
        c.write_text(source)
        exe = self.out / 'test'
        subprocess.run([compiler, '-std=c11', *flags, str(c), '-o', str(exe)], check=True,
                       capture_output=True, text=True)
        return subprocess.run([str(exe)], capture_output=True, text=True)

    def makefile(self, body):
        self.file('src/openfpga/Makefile', body + '\n# Neither sdk.mk rules nor desktop rules below are safe to evaluate\n$(shell touch NEVER)\n')

    def test_current_declarative_sources_select_game_and_zstd_without_pc(self):
        self.file('src/openfpga/platform/of_native.c')
        self.makefile('''GAME ?= undertale
BS = $(abspath $(CURDIR)/../..)
BS_SRC = $(BS)/src
BS_VENDOR = $(BS)/vendor
SRCS = main.c platform/game_$(GAME).c platform/of_native.c $(BS_SRC)/vm.c $(BS_VENDOR)/zstd/zstd.c
PC_SRCS = $(SRCS) platform/of_pc_audio.c
CFLAGS = -DENABLE_WAD17 -DOF_GAME_NAME='"$(GAME)"'
''')
        for name in ['src/openfpga/main.c', 'src/openfpga/platform/game_deltarune.c', 'src/vm.c', 'vendor/zstd/zstd.c']:
            self.file(name)
        self.assertEqual(build.source_generation(), 'of')
        self.assertEqual([p.relative_to(self.root).as_posix() for p in build.sources('deltarune', self.out)],
                         ['src/openfpga/main.c', 'src/openfpga/platform/game_deltarune.c',
                          'src/openfpga/platform/of_native.c', 'src/vm.c', 'vendor/zstd/zstd.c'])
        self.assertFalse((self.out / 'NEVER').exists())

    def test_make_flags_keep_c_string_values_and_never_run_shell(self):
        self.makefile('''GAME ?= undertale
CFLAGS = -DOF_GAME_NAME='"$(GAME)"' -DCOUNT='(4u*2u)'
SRCS = main.c
''')
        flags = build.port_flags('undertale', self.out)
        result = self.compile_run('#include <stdio.h>\nint main(void){printf("%s %u",OF_GAME_NAME,COUNT);}', flags)
        self.assertEqual(result.stdout, 'undertale 8')
        marker = self.out / 'escaped'
        self.makefile('CFLAGS := $(shell touch ' + str(marker) + ')\nSRCS = main.c')
        with self.assertRaisesRegex(RuntimeError, '[Dd]eclarative|[Uu]nsafe'):
            build.port_flags('undertale', self.out)
        self.assertFalse(marker.exists())

    def test_export_assignment_evaluates_safe_state_path(self):
        self.makefile('''G = assets/
export OF_STATE_DATA := $(abspath $(G)data.win)
CFLAGS = -DSTATE_PATH='"$(OF_STATE_DATA)"'
SRCS = main.c
''')
        flags = build.port_flags('undertale', self.out)
        result = self.compile_run('#include <stdio.h>\nint main(void){puts(STATE_PATH);}', flags)
        self.assertEqual(Path(result.stdout.strip()).parts[-2:], ('assets', 'data.win'))
        self.assertTrue(Path(result.stdout.strip()).is_absolute())
        self.assertFalse((self.out / 'NEVER').exists())

    def test_export_assignments_reject_unsafe_variables_and_expansions(self):
        marker = self.out / 'export-executed'
        for line in [
            'export SHELL := /bin/sh',
            'export MAKEFILES := ' + str(self.out / 'include.mk'),
            'export SHELL',
            'export MAKEFILES',
            'export OF_STATE_DATA := $(shell touch ' + str(marker) + ')',
            r'export OF_STATE_DATA := safe \# $(shell touch ' + str(marker) + ')',
        ]:
            with self.subTest(line=line):
                (self.out / 'flags.mk').unlink(missing_ok=True)
                self.makefile(line + '\nCFLAGS = -DOK\nSRCS = main.c')
                with self.assertRaisesRegex(RuntimeError, '[Dd]eclarative|[Uu]nsafe'):
                    build.port_flags('undertale', self.out)
                self.assertFalse(marker.exists())
                self.assertFalse((self.out / 'flags.mk').exists(), 'Unsafe export reached Make evaluation')

    def test_known_native_state_fingerprint_probe_is_disabled_without_running_shell(self):
        # Exact source form from the supported baseline, not a shell allowlist.
        probe = '''ifneq ($(wildcard $(G)data.win),)
ifndef STATE_GAME_ID
STATE_GAME_ID := $(shell python3 -c 'import hashlib; h=hashlib.sha256(); f=open("$(G)data.win", "rb"); [h.update(b) for b in iter(lambda:f.read(1048576), b"")]; print(h.hexdigest()[:16])')
endif
ifeq ($(STATE_GAME_ID),)
$(error Could not fingerprint data.win; when compiling in a container pass STATE_GAME_ID=<host SHA256 prefix>)
endif
endif
'''
        self.makefile('G = assets/\n' + probe + '''ifneq ($(STATE_GAME_ID),)
BS_DEFS += -DOF_STATE_GAME_ID=0x$(STATE_GAME_ID)ULL
endif
CFLAGS = -DCOUNT=7 $(BS_DEFS)
SRCS = main.c
''')
        flags = build.port_flags('undertale', self.out)
        result = self.compile_run('''#ifdef OF_STATE_GAME_ID
#error Native state fingerprints are outside the harness services
#endif
int main(void){return COUNT!=7;}
''', flags)
        self.assertEqual(result.returncode, 0, result.stderr)
        marker = self.out / 'state-probe-executed'
        altered = probe.replace("python3 -c 'import hashlib;", 'touch ' + str(marker) + "; python3 -c 'import hashlib;")
        self.makefile('G = assets/\n' + altered + 'CFLAGS = -DOK\nSRCS = main.c')
        with self.assertRaisesRegex(RuntimeError, '[Dd]eclarative|[Uu]nsafe'):
            build.port_flags('undertale', self.out)
        self.assertFalse(marker.exists())

    def test_declarative_prefix_rejects_recipes_and_source_escape(self):
        marker = self.out / 'escaped'
        self.makefile('CFLAGS = -DOK\nSRCS = main.c\nprobe:\n\ttouch ' + str(marker))
        with self.assertRaisesRegex(RuntimeError, '[Dd]eclarative|[Uu]nsafe'):
            build.port_flags('undertale', self.out)
        self.assertFalse(marker.exists())
        self.file('src/openfpga/platform/of_native.c')
        self.makefile('CFLAGS = -DOK\nSRCS = /etc/passwd')
        with self.assertRaisesRegex(RuntimeError, 'source|Source'):
            build.sources('undertale', self.out)

    def test_escaped_comment_cannot_hide_make_shell_expansion(self):
        marker = self.out / 'executed'
        self.makefile(r'CFLAGS := -DOK \# $(shell touch ' + str(marker) + ')\nSRCS = main.c')
        error = None
        try:
            build.port_flags('undertale', self.out)
        except RuntimeError as caught:
            error = caught
        self.assertFalse(marker.exists(), 'Escaped comment allowed Make to execute hidden shell expansion')
        self.assertIsInstance(error, RuntimeError, 'Escaped comment syntax must be rejected before Make runs')

    def test_declarative_flags_ignore_unrelated_asset_migration_checks(self):
        (self.out / 'data.win').write_bytes(b'private fixture')
        self.makefile('''ifneq ($(wildcard data.win),)
$(error Move old assets before using the device build)
endif
CFLAGS = -DCOUNT=8
SRCS = main.c
''')
        flags = build.port_flags('undertale', self.out)
        result = self.compile_run('int main(void){return COUNT!=8;}', flags)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_historical_source_selection_is_preserved(self):
        self.file('src/openfpga/platform/ut_native.c')
        paths = build.sources('undertale', self.out)
        self.assertEqual(build.source_generation(), 'ut')
        self.assertIn(self.port / 'platform/ut_bench.c', paths)
        self.assertIn(self.port / 'platform/ut_native.c', paths)
        self.assertNotIn(self.vendor / 'zstd/zstd.c', paths)

    def test_generated_vm_hooks_execute_for_both_dispatch_generations(self):
        for generation, dispatch, signature, setup in [
            ('ut', 'uint32_t instr = BinaryUtils_readUint32Aligned(bytecodeBase + ip);',
             'RValue VM_executeCode(VMContext* ctx, int32_t codeIndex) {', ''),
            ('of', 'OpWord opword = {BinaryUtils_readUint32Aligned(bytecodeBase + ip)};',
             'RValue VM_executeCode(VMContext* ctx, int32_t codeIndex, int extra) {', '(void)extra;')]:
            with self.subTest(generation=generation):
                original = '''#if defined(%s_FAST_LOOP) && !defined(OF_PC)
#define PLACED 1
#endif
static RValue dispatch(VMContext *ctx) {const uint8_t bytes[4]={7,0,0,0};const uint8_t *bytecodeBase=bytes;uint32_t ip=0;
        %s
return 0;}
%s %s return dispatch(ctx);}
''' % (generation.upper(), dispatch, signature, setup)
                generated = build.instrument_vm(original, generation, 'trace', 'bram')
                prelude = '''#include <stdint.h>
typedef int RValue; typedef struct {int unused;} VMContext;typedef union {uint32_t value;} OpWord;
static unsigned ops,events;
static uint32_t BinaryUtils_readUint32Aligned(const uint8_t *p){return *p;}
static void frame_tick(VMContext*c,unsigned ip,unsigned word){(void)c;if(ip==0 && word==7)ops++;}
static void frame_event(int index){if(index==3)events++;}
'''
                call = 'VM_executeCode(&ctx,3' + (',0' if generation == 'of' else '') + ')'
                result = self.compile_run(prelude + generated + '\nint main(void){VMContext ctx={0};' + call + ';return ops!=1 || events!=1;}')
                self.assertEqual(result.returncode, 0, result.stderr)
                timing = build.instrument_vm(original, generation, 'timing', 'sdram')
                result = self.compile_run(prelude + timing + '\nint main(void){VMContext ctx={0};' + call + ';return ops || events;}')
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_unknown_hook_layout_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, 'anchor|dispatch'):
            build.instrument_vm('RValue unknown(void){return 0;}', 'of', 'trace', 'sdram')

    def test_replay_selects_supported_interpreter_symbol_and_checks_placement(self):
        # Execute the real pure selection function without importing the optional
        # ELF parser needed by complete replay in the toolchain container.
        tree = ast.parse((ROOT / 'bench/rtl.py').read_text())
        functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                     and node.name == 'interpreter_address']
        self.assertEqual(len(functions), 1, 'Replay needs generation-aware interpreter selection')
        namespace = {}
        exec(compile(ast.Module(body=functions, type_ignores=[]), 'bench/rtl.py', 'exec'), namespace)
        select = namespace['interpreter_address']
        for name in ['executeLoop', 'executeLoop.constprop.0', 'executeBytecodeInstructions',
                     'executeBytecodeInstructions.constprop.0']:
            self.assertEqual(select({name: 0x4000}, 'bram'), 0x4000)
            self.assertEqual(select({name: 0x10401000}, 'sdram'), 0x10401000)
            with self.assertRaisesRegex(RuntimeError, 'BRAM'):
                select({name: 0x10401000}, 'bram')
        with self.assertRaisesRegex(RuntimeError, 'exactly one'):
            select({'executeLoop': 0x4000, 'executeBytecodeInstructions': 0x4010}, 'bram')
        with self.assertRaisesRegex(RuntimeError, 'exactly one'):
            select({'unknownLoop': 0x4000}, 'bram')

    def test_deterministic_environment_routes_selected_generation(self):
        # Execute the real bridge getenv independently of RV32-only syscalls.
        bridge = (ROOT / 'bench/bridge.c').read_text()
        environment = bridge[bridge.index('char *getenv('):bridge.index('uint64_t frame_clock;')]
        for current in [0, 1]:
            for disabled in [0, 1]:
                prefix = 'BS' if current else 'UT'
                other = 'UT' if current else 'BS'
                program = '#include <stdlib.h>\n#include <string.h>\n' + environment + '''
int main(void){
 if(!getenv("%s_SEED") || strcmp(getenv("%s_SEED"),"7"))return 1;
 if(!getenv("%s_UNCAPPED") || !getenv("%s_NOFLIP"))return 2;
 if((getenv("%s_NO_NATIVE")!=NULL)!=%d)return 3;
 if(getenv("%s_SEED") || getenv("PATH") || getenv("%s_STATE_SAVE_FRAME"))return 4;
 return 0;}
''' % (prefix, prefix, prefix, prefix, prefix, disabled, other, prefix)
                result = self.compile_run(program, ['-DFRAME_CURRENT_PORT=' + str(current),
                                                   '-DFRAME_DISABLE_NATIVE=' + str(disabled)])
                self.assertEqual(result.returncode, 0, (current, disabled, result.stderr))

    def test_current_runtime_traverses_statics_and_rejects_live_callframe(self):
        # Structural fixtures provide both source-generation APIs; compile the
        # entire runtime.c and execute its actual state traversal and cleanup.
        header = r'''#ifndef TEST_FRAME_H
#define TEST_FRAME_H
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#define FRAME_META
#define IS_WAD17_OR_HIGHER_ENABLED 0
#define FRAME_TARGET 2399
#define FRAME_TIMING 0
#define FRAME_AUDIO_REALTIME 0
#define FRAME_FB_UNCACHED 0
#define FRAME_SPEED 0
#define arrlen(p) ((p)?1:0)
typedef struct Instance Instance;
typedef struct GMLArray GMLArray;
typedef struct {unsigned type,gmlStackType,assetRefType;union {int32_t int32;char *string;GMLArray *array;Instance *structInst;};} RValue;
enum {RVALUE_UNDEFINED,RVALUE_INT32,RVALUE_BOOL,RVALUE_REAL,RVALUE_ASSETREF,RVALUE_STRING,RVALUE_ARRAY,RVALUE_STRUCT};
typedef struct {int key;RValue value;} IntRValueEntry;
struct Instance {struct {unsigned capacity;IntRValueEntry *entries;} selfVars;};
typedef struct {int length;RValue *data;} GMLArrayRow;
struct GMLArray {int type,refCount;struct {int rowCount;GMLArrayRow *rows;} legacy;struct {int length;RValue *data;} modern;};
#define GML_LEGACY_ARRAY 0
typedef struct {int key,value;} IntIntEntry;
typedef struct {unsigned capacity,count;IntIntEntry *entries;} IntIntHashMap;
typedef struct {struct {unsigned count;} code;} DataWin;
typedef struct CallFrame {int codeIndex;} CallFrame;
typedef struct {Instance *globalScopeInstance;struct {unsigned top;} stack;void *envStack;IntIntHashMap *codeLocalsSlotMaps;DataWin *dataWin;
#if FRAME_CURRENT_PORT
CallFrame *currentCallFrame;Instance **staticStructs;bool *staticInitialized;int savearefBalance;
#else
void *localVars,*callStack;int callDepth,currentCodeIndex;
#endif
} VMContext;
typedef struct {int frameCount,currentRoomIndex,pendingRoom;VMContext *vmContext;Instance **instances,**structInstances;} Runner;
extern unsigned frame_pcm_pairs,frame_pcm_hash,frame_expected[3][8];
extern int frame_host;extern uint64_t frame_clock;extern uintptr_t frame_heap_cursor;
int frame_suspend(void);void frame_fail(const char*) __attribute__((noreturn));
void frame_output(const char*);long frame_syscall(long,long,long,long,long,long,long);
#endif
'''
        (self.out / 'frame.h').write_text(header)
        for name in ['instance.h', 'gml_array.h', 'gml_method.h']:
            (self.out / name).write_text('#include "frame.h"\n')
        harness = '''
#include <stdlib.h>
#include "frame.h"
unsigned frame_pcm_pairs,frame_pcm_hash,frame_expected[3][8],frame_clock_reads,frame_audio_consumed,frame_audio_underruns;
int frame_host=1;uint64_t frame_clock;uintptr_t frame_heap_cursor;
char __frame_heap_start[1],__bss_end[1];
int frame_suspend(void){return 0;}void frame_fail(const char *s){(void)s;_Exit(9);}
void frame_output(const char*s){(void)s;}void frame_platform_begin(void){}void frame_platform_end(void){}
unsigned frame_pixels(void){return 0;}void frame_ppm(unsigned x){(void)x;}
long frame_syscall(long a,long b,long c,long d,long e,long f,long g){return -1;}
int game_main(int c,char**v){return 0;}
#include "%s"
''' % (ROOT / 'bench/runtime.c')
        for current in [0, 1]:
            for live in [0, 1]:
                body = '''int main(void){DataWin dw={.code.count=1};VMContext ctx={.dataWin=&dw};Runner r={.vmContext=&ctx};
#if FRAME_CURRENT_PORT
CallFrame cf={.codeIndex=3};Instance inst={0};Instance *statics[1]={&inst};bool initialized[1]={true};ctx.staticStructs=statics;ctx.staticInitialized=initialized;
if(LIVE){ctx.currentCallFrame=&cf;state_hash(&r);return 8;}
unsigned before=state_hash(&r);IntRValueEntry entry={.key=10,.value={.type=RVALUE_INT32,.int32=4}};inst.selfVars.capacity=1;inst.selfVars.entries=&entry;
if(before==state_hash(&r))return 1;
ctx.currentCallFrame=&cf;frame_tick(&ctx,0,7);unsigned first=frame_trace;cf.codeIndex=4;frame_tick(&ctx,0,7);if(first==frame_trace || frame_ops!=2)return 2;
#else
if(LIVE){ctx.callDepth=1;state_hash(&r);return 8;}state_hash(&r);
#endif
return 0;}
'''
                try:
                    result = self.compile_run(harness + body, ['-I' + str(self.out),
                                              '-DFRAME_CURRENT_PORT=' + str(current), '-DLIVE=' + str(live)])
                except subprocess.CalledProcessError as error:
                    self.fail(error.stderr)
                self.assertEqual(result.returncode, 9 if live else 0, (current, live, result.stderr))

    def test_async_service_substitutions_fail_closed_without_writing_memory(self):
        platform = (ROOT / 'bench/platform.c').read_text()
        substitutions = platform[platform.index('/* Device branches compile'):]
        program = '''#include <stdint.h>
#include <stdlib.h>
struct of_capabilities {unsigned heap_base,heap_size,cpu_freq_hz;};
''' + substitutions + '''
static int called;static void callback(int a,int b){called++;}
int main(void){uint32_t slot=123;char dest[4]="abc";
of_file_slot_register(4,"data.win");of_file_set_idle_hook(NULL);
if(of_file_slot_find("data.win",&slot)!=-1 || slot!=123)return 1;
if(of_file_async_max_read()!=0 || of_file_dma_stage_alloc(4,4)!=NULL)return 2;
if(of_file_read_async(4,0,dest,4,callback)!=-1 || called || dest[0]!='a')return 3;
if(of_file_async_poll() || of_file_async_busy() || of_has_feature(0xffffffffu))return 4;
return 0;}
'''
        result = self.compile_run(program)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
