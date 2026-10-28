"""Execute the current adapter's directory and file namespace on real files."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent


class CwdTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        for name in ('repeat-0', 'repeat-1'):
            directory = self.root / name
            directory.mkdir()
            (directory / 'data.bin').write_bytes(b'asset payload')

    def compile(self, body, current=True, resolver=''):
        bridge = (ROOT / 'bench/bridge.c').read_text()
        # Include the real file bridge, including its namespace/cwd services.
        start = bridge.index('typedef struct {char *name;int fd;off_t offset,size;} Cookie;')
        marker = '/* Current-port virtual asset namespace.'
        if marker in bridge:
            start = bridge.index(marker)
        code = bridge[start:bridge.index('char *getenv(')]
        prelude = r'''
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#define CHECK(x) do {if(!(x)){fprintf(stderr,"line %d: %s (errno %d)\n",__LINE__,#x,errno);return 1;}} while(0)
int frame_host=1;
void frame_fail(const char *message){fprintf(stderr,"unexpected bridge failure: %s\n",message);exit(91);}
int frame_rpc(unsigned op,const char *name,unsigned offset,void *buf,unsigned size){exit(92);}
#ifdef __APPLE__
/* macOS exposes the same real cookie stream operations through funopen. */
typedef struct {ssize_t (*read)(void*,char*,size_t);int (*seek)(void*,off_t*,int);int (*close)(void*);} cookie_io_functions_t;
static int apple_read(void*,char*,int);
static fpos_t apple_seek(void*,fpos_t,int);
#define fopencookie(cookie,mode,io) funopen(cookie,apple_read,NULL,apple_seek,cookie_close)
#endif
'''
        suffix = r'''
#ifdef __APPLE__
static int apple_read(void *cookie,char *buf,int size){return (int)cookie_read(cookie,buf,(size_t)size);}
static fpos_t apple_seek(void *cookie,fpos_t offset,int whence){off_t result=offset;return cookie_seek(cookie,&result,whence)?-1:result;}
#endif
'''
        source = self.root / 'test.c'
        source.write_text(prelude + code + suffix + resolver + '\nint main(void){\n' + body + '\n}\n')
        compiler = shutil.which('clang') or shutil.which('cc')
        self.assertIsNotNone(compiler, 'A host C compiler is required')
        executable = self.root / 'test'
        result = subprocess.run([compiler, '-std=c11', '-DFRAME_CURRENT_PORT=' + str(int(current)),
                                 str(source), '-o', str(executable)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return executable

    def run_repeats(self, executable):
        outputs = []
        for name in ('repeat-0', 'repeat-1'):
            result = subprocess.run([str(executable)], cwd=self.root / name, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            outputs.append(result.stdout)
        return outputs

    def test_current_cwd_has_bounded_posix_and_gnu_allocation_behavior(self):
        executable = self.compile(r'''
char buffer[64]; memset(buffer,'x',sizeof(buffer));
errno=0; CHECK(getcwd(buffer,0)==NULL && errno==EINVAL);
errno=0; CHECK(getcwd(buffer,13)==NULL && errno==ERANGE);
CHECK(buffer[0]=='x');
CHECK(getcwd(buffer,14)==buffer && !strcmp(buffer,"/frame-assets"));
char *allocated=getcwd(NULL,0);CHECK(allocated && !strcmp(allocated,"/frame-assets"));free(allocated);
errno=0;CHECK(getcwd(NULL,13)==NULL && errno==ERANGE);
allocated=getcwd(NULL,64);CHECK(allocated && !strcmp(allocated,"/frame-assets"));free(allocated);
puts(buffer);return 0;
''')
        self.assertEqual(self.run_repeats(executable), ['/frame-assets\n', '/frame-assets\n'])

    def test_virtual_and_relative_file_reads_share_actual_cookie_stream(self):
        executable = self.compile(r'''
const char *names[]={"data.bin","./data.bin","/frame-assets/data.bin"};
for(unsigned i=0;i<3;i++){
 FILE *file=__wrap_fopen(names[i],"rb");CHECK(file!=NULL);
 char data[32]={0};CHECK(fread(data,1,13,file)==13 && !strcmp(data,"asset payload"));
 CHECK(fseek(file,6,SEEK_SET)==0);memset(data,0,sizeof(data));
 CHECK(fread(data,1,7,file)==7 && !strcmp(data,"payload"));CHECK(!fclose(file));
}
return 0;
''')
        self.run_repeats(executable)

    def test_other_absolute_roots_and_parent_escapes_are_rejected(self):
        # The first path physically exists: accepting it would leak host access.
        path = (self.root / 'repeat-0/data.bin').as_posix()
        executable = self.compile(r'''
const char *names[]={"%s","/frame-assets-other/data.bin","/frame-assets//data.bin","/frame-assets/../data.bin","../repeat-0/data.bin","/frame-assets","/frame-assets/",""};
for(frame_host=1;frame_host>=0;frame_host--)for(unsigned i=0;i<sizeof(names)/sizeof(*names);i++){
 errno=0;CHECK(__wrap_fopen(names[i],"rb")==NULL && errno==EACCES);
}
return 0;
''' % path)
        self.run_repeats(executable)

    def test_historical_bridge_keeps_physical_cwd_and_absolute_reads(self):
        path = (self.root / 'repeat-0/data.bin').as_posix()
        executable = self.compile(r'''
char buffer[4096];CHECK(getcwd(buffer,sizeof(buffer))!=NULL);puts(buffer);
FILE *file=__wrap_fopen("%s","rb");CHECK(file!=NULL);CHECK(fgetc(file)=='a');CHECK(!fclose(file));return 0;
''' % path, current=False)
        self.assertEqual(self.run_repeats(executable),
                         [str(self.root / 'repeat-0') + '\n', str(self.root / 'repeat-1') + '\n'])

    def test_actual_current_runner_resolver_is_independent_of_capture_directory(self):
        source = ROOT / 'experiments/preflight/current-419ef894-first/inputs/butterscotch/src/runner.c'
        if not source.exists():
            self.skipTest('Optional current-port private source snapshot is absent')
        runner = source.read_text()
        resolver = runner[runner.index('static char* getCurrentWorkingDirectory(void)'):runner.index('void Runner_setGameArgs(')]
        resolver = ('\n#define nullptr NULL\n#define safeMalloc malloc\n#define safeStrdup strdup\n'
                    'static char *getExecutablePath(void){return NULL;}\n' + resolver)
        executable = self.compile(r'''
char *directory=resolveProgramDirectory("undertale");
CHECK(directory && !strcmp(directory,"/frame-assets/"));puts(directory);
char name[64];snprintf(name,sizeof(name),"%sdata.bin",directory);
FILE *file=__wrap_fopen(name,"rb");CHECK(file && fgetc(file)=='a');CHECK(!fclose(file));
free(directory);return 0;
''', resolver=resolver)
        self.assertEqual(self.run_repeats(executable), ['/frame-assets/\n', '/frame-assets/\n'])


if __name__ == '__main__':
    unittest.main()
