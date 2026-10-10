#!/usr/bin/env python3
"""Preload captured RV32 process state and replay complete frames on os25 RTL."""
import argparse,hashlib,json,os,re,struct,subprocess,sys
from pathlib import Path
from elftools.elf.elffile import ELFFile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));import harness
BUILD=ROOT/'build/fullframe'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def prepare(game,variant):
 d=BUILD/game/variant;manifest=json.loads((d/'capture.json').read_text())
 if sha(d/'program.elf')!=manifest['elf_sha256']:raise RuntimeError('Full-frame ELF changed')
 for name,digest in manifest['repeats'][0].items():
  if sha(d/'repeat-0'/name)!=digest:raise RuntimeError('Captured process changed: '+name)
 for name,digest in manifest['build']['sources'].items():
  if sha(ROOT/name)!=digest:raise RuntimeError('Full-frame source changed; rebuild and recapture')
 image=bytearray((d/'repeat-0/checkpoint.bin').read_bytes())
 with (d/'program.elf').open('rb') as f:
  elf=ELFFile(f);syms={s.name:s.entry.st_value for s in elf.get_section_by_name('.symtab').iter_symbols()};bram=bytearray(struct.pack('<I',0x13)*8192)
  loop=syms['executeLoop']
  if variant=='bram' and not 0x4000<=loop<0x7800:raise RuntimeError('Interpreter was not placed in application BRAM')
  if variant=='sdram' and not 0x10400000<=loop<0x10800000:raise RuntimeError('Interpreter was not placed in SDRAM')
  if syms['_rtl_start']!=0x10400000 or elf.header.e_entry!=syms['_host_start']:raise RuntimeError('Invalid dual boot entry points')
  struct.pack_into('<II',bram,0,0x104002b7,0x00028067)
  for s in elf.iter_sections():
   if s.header.sh_flags&2 and s.header.sh_size and 0x4000<=s.header.sh_addr<0x7800:
    bram[s.header.sh_addr:s.header.sh_addr+s.header.sh_size]=s.data()
  address=syms['frame_expected'];struct.pack_into('<24I',image,address-0x10400000,*[x for r in manifest['rows'] for x in r])
 (d/'program.bin').write_bytes(image);(d/'stack.bin').write_bytes((d/'repeat-0/stack.bin').read_bytes())
 text='WIDTH=32;\nDEPTH=8192;\nADDRESS_RADIX=DEC;\nDATA_RADIX=HEX;\nCONTENT BEGIN\n'+''.join(f'{i} : {w[0]:08x};\n' for i,w in enumerate(struct.iter_unpack('<I',bram)))+'END;\n';(d/'firmware.mif').write_text(text)
 save(d/'prepared.json',dict(image_sha256=sha(d/'program.bin'),stack_sha256=sha(d/'stack.bin'),bram_sha256=sha(d/'firmware.mif'),capture_sha256=sha(d/'capture.json'),expected_address=address,heap_info=struct.unpack('<3I',(d/'repeat-0/checkpoint-info.bin').read_bytes()),execute_loop_address=syms['executeLoop'],elf_sha256=sha(d/'program.elf')))
 print('Prepared',game,variant,len(image),'bytes, heap cursor',hex(0x10400000+len(image)),flush=True)

def rtl(jobs):
 d=BUILD/'rtl';d.mkdir(exist_ok=True)
 leaf=ROOT/'build/rtl';source=(leaf/'main.cpp').read_text()
 a=source.index('static const uint32_t SDRAM_OS_WORD');b=source.index('// ========================================================================\n// Main',a)
 loader=r'''static const uint32_t SDRAM_OS_WORD = 0x10400000u/4u;
static std::vector<uint32_t> g_image;
static uint64_t rpc_calls=0,rpc_bytes=0;
static void poke_bytes(uint32_t address,const std::vector<uint8_t>& bytes) {
    auto &mem=tb->rootp->tb_system->__PVT__sdram_chip__DOT__mem;
    for(size_t i=0;i<bytes.size();i+=2) mem[((address-0x10000000u)+i)>>1]=bytes[i]|((i+1<bytes.size()?bytes[i+1]:0)<<8);
}
static std::vector<uint8_t> read_file(const char*path) {
    std::ifstream f(path,std::ios::binary);if(!f)throw std::runtime_error(std::string("missing ")+path);
    return std::vector<uint8_t>(std::istreambuf_iterator<char>(f),{});
}
static bool load_os_bin(const char*path) {
    auto bytes=read_file(path);g_image.resize((bytes.size()+3)/4,0);
    std::memcpy(g_image.data(),bytes.data(),bytes.size());poke_bytes(0x10400000u,bytes);
    auto stack=read_file("stack.bin");poke_bytes(0x13f80000u,stack);
    tick_cycle();
    for(size_t w=0;w<g_image.size();w+=(g_image.size()/31)+1)if(model_peek((SDRAM_OS_WORD+w)&0xffffff)!=g_image[w])return false;
    const char*bad=getenv("FRAME_BAD_ORACLE");
    if(bad && std::atoi(bad)) {
       uint32_t address=std::strtoul(getenv("FRAME_EXPECTED_ADDRESS"),nullptr,0)+4;
       auto &mem=tb->rootp->tb_system->__PVT__sdram_chip__DOT__mem;mem[(address-0x10000000u)>>1]^=1;
       g_image[(address-0x10400000u)>>2]^=1;
    }
    std::printf("Loaded verified full RV32 image/heap (%zu bytes) and stack (%zu bytes)\n",bytes.size(),stack.size());return true;
}
static void service_files() {
    auto &mem=tb->rootp->tb_system->cram0_mem__DOT__mem;
    uint32_t op=mem[0];if(!op)return;
    std::string name;for(unsigned i=0;i<256;i++){char c=(mem[(64+i)>>2]>>(((64+i)&3)*8))&255;if(!c)break;name+=c;}
    if(name.empty() || name[0]=='/' || name.find("..")!=std::string::npos)throw std::runtime_error("unsafe virtual asset name");
    const char*root=getenv("FRAME_ASSET_ROOT");if(!root)throw std::runtime_error("missing private asset root");
    auto base=std::filesystem::weakly_canonical(root);auto path=std::filesystem::weakly_canonical(base/name);
    if(path.string().compare(0,base.string().size()+1,base.string()+"/"))throw std::runtime_error("asset escapes private root");
    std::ifstream file(path,std::ios::binary);int32_t result=-1;
    if(file){file.seekg(0,std::ios::end);auto size=file.tellg();
      if(op==1)result=(int32_t)size;
      else if(op==2){unsigned offset=mem[1],want=mem[2];if(want>65536)throw std::runtime_error("oversized RPC");
       file.seekg(offset);std::vector<char>data(want);file.read(data.data(),want);result=(int32_t)file.gcount();
       for(int32_t i=0;i<result;i++){unsigned addr=0x1000+i;uint32_t mask=255u<<((addr&3)*8);mem[addr>>2]=(mem[addr>>2]&~mask)|((uint32_t)(uint8_t)data[i]<<((addr&3)*8));}rpc_bytes+=result;
      }else throw std::runtime_error("unsupported RPC opcode");
    }
    rpc_calls++;mem[3]=(uint32_t)result;mem[0]=0;
}

'''
 source=source[:a]+loader+source[b:]
 source=source.replace('#include <sstream>','#include <sstream>\n#include <filesystem>\n#include <stdexcept>\n#include <iterator>')
 source=source.replace('uart_buf.find("VMHARNESS FAIL")','uart_buf.find("FRAMEHARNESS FAIL")')
 source=harness.once(source,'        if (tb->inj_burst_rd)','        if ((cpu_cycles & 63u)==0) service_files();\n        if (tb->inj_burst_rd)')
 source=harness.once(source,'    std::printf("SDRAM errors=%u\\n", tb->harness_sdram_errors);','    std::printf("SDRAM errors=%u\\n", tb->harness_sdram_errors);\n    std::printf("Virtual file calls=%llu bytes=%llu\\n",(unsigned long long)rpc_calls,(unsigned long long)rpc_bytes);')
 (d/'main.cpp').write_text(source)
 # Reuse the verified Pocket wrapper, controller twin and CPU, in a separate build directory.
 test=harness.OS/'src/fpga/test';mk=(leaf/'test.mk').read_text();(d/'test.mk').write_text(mk)
 command=['make','-f',d/'test.mk',d/'obj/Vtb_system',f'SYSTEM_SDRAM_DIR={d}/obj',f'SYSTEM_SDRAM_CPP={d}/main.cpp',f'VEXII_MISTER={harness.CPU}',f'VERILATOR=verilator -j {jobs} '+ ' '.join('+define+'+x for x in json.loads((leaf/'rtl.json').read_text())['definitions'])]
 harness.run(command,d/'compile.log',cwd=test)
 save(d/'rtl.json',dict(simulator_sha256=sha(d/'obj/Vtb_system'),source_sha256=sha(d/'main.cpp'),leaf_rtl_sha256=sha(leaf/'rtl.json'),generator_sha256=sha(ROOT/'fullframe/rtl.py')))

def run(game,variant,traffic,negative=False):
 d=BUILD/game/variant;meta=json.loads((d/'prepared.json').read_text());capture=json.loads((d/'capture.json').read_text());rtl=BUILD/'rtl'
 for name,field in [('program.bin','image_sha256'),('stack.bin','stack_sha256'),('firmware.mif','bram_sha256')]:
  if sha(d/name)!=meta[field]:raise RuntimeError('Prepared artifact changed')
 if sha(d/'capture.json')!=meta['capture_sha256']:raise RuntimeError('Capture changed')
 if sha(d/'program.elf')!=meta['elf_sha256']:raise RuntimeError('ELF changed')
 for source,digest in capture['build']['sources'].items():
  if sha(ROOT/source)!=digest:raise RuntimeError('Full-frame source changed; rebuild and recapture: '+source)
 assets=ROOT/'inputs/butterscotch/src/openfpga'
 if game=='deltarune':assets=assets/'games/deltarune'
 if sha(assets/'data.win')!=capture['source_data_sha256']:raise RuntimeError('Game data changed')
 rmeta=json.loads((rtl/'rtl.json').read_text())
 if sha(rtl/'obj/Vtb_system')!=rmeta['simulator_sha256']:raise RuntimeError('Simulator changed')
 if sha(ROOT/'fullframe/rtl.py')!=rmeta['generator_sha256'] or sha(rtl/'main.cpp')!=rmeta['source_sha256'] or sha(ROOT/'build/rtl/rtl.json')!=rmeta['leaf_rtl_sha256']:raise RuntimeError('RTL source changed; rebuild simulator')
 env=dict(os.environ,SCAN_ENABLE=str(int(traffic=='scanout')),SCAN_PERIOD='3175',SCAN_LEN='320',SCAN_ACTIVE='480',SCAN_TOTAL='525',SCAN_BASE_HW='0x1800000',STRIKE_SCAN_PERIOD='1000000000',FRAME_ASSET_ROOT=str(assets),FRAME_EXPECTED_ADDRESS=hex(meta['expected_address']),FRAME_BAD_ORACLE=str(int(negative)))
 name='negative' if negative else traffic;log=d/(name+'.log');print('Running complete-frame RTL',game,variant,name,flush=True)
 with log.open('w') as out:proc=subprocess.run([str(rtl/'obj/Vtb_system'),'program.bin','300000000'],cwd=d,env=env,stdout=out,stderr=subprocess.STDOUT,timeout=1800)
 text=log.read_text()
 if negative:
  if proc.returncode!=2 or 'FRAMEHARNESS FAIL frame ' not in text:raise RuntimeError('Negative full-frame oracle did not fail closed')
  save(d/'negative-results.json',dict(game=game,variant=variant,rejected=True,prepared=meta,rtl=rmeta,log_sha256=sha(log)))
  print('PASS wrong full-frame state oracle rejected',game,flush=True);return
 if proc.returncode or 'FRAMEHARNESS PASS HAL init' not in text or 'FRAMEHARNESS FAIL' in text:raise RuntimeError('Full-frame RTL failed; inspect '+str(log))
 for token in ['WCONF: mism=0 spurious=0 exp_fifo=0 aw_fifo=0 run_left=0','R mismatches=0  scanout mismatches=0  rlast slips=0  orphan beats=0  DRAM strikes=0','SDRAM errors=0']:
  if token not in text:raise RuntimeError('Memory oracle failed: '+token)
 uart=text.split('=== UART BEGIN ===')[1].split('=== UART END ===')[0]
 rows=[]
 for m in re.finditer(r'^FRAMERESULT (\d+) (\d+) ([0-9a-f]+) ([0-9a-f]+) ([0-9a-f]+) (\d+) (\d+) (\d+) ([0-9a-f]+)$',uart,re.M):
  f,c,s,p,a,n,o,e,t=m.groups();row=[int(f),int(s,16),int(p,16),int(a,16),int(n),int(o),int(e),int(t,16)];rows.append(dict(oracle=row,cycles=int(c),simulated_ms=int(c)/100000))
 if [r['oracle'] for r in rows]!=capture['rows'] or any(r['cycles']<=0 for r in rows):raise RuntimeError('Full-frame results do not match capture')
 save(d/(name+'-results.json'),dict(game=game,variant=variant,traffic=traffic,rows=rows,prepared=meta,rtl=rmeta,log_sha256=sha(log),scope='Complete instrumented real game-loop frames; simulated CPU/SDRAM with deterministic platform clock/input/audio queue and virtual read-only files. No physical Pocket FPS measurement.'))
 print('PASS complete-frame RTL',game,variant,name,[(r['oracle'][0],r['cycles']) for r in rows],flush=True)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('action',choices=['prepare','rtl','run','all']);ap.add_argument('--game',choices=['undertale','deltarune']);ap.add_argument('--variant',choices=['sdram','bram'],default='sdram');ap.add_argument('--traffic',choices=['quiet','scanout'],default='quiet');ap.add_argument('--jobs',type=int,default=4);ap.add_argument('--negative',action='store_true');a=ap.parse_args();games=[a.game] if a.game else ['undertale','deltarune']
 if a.action in ['prepare','all']:
  for game in games:prepare(game,a.variant)
 if a.action in ['rtl','all']:rtl(a.jobs)
 if a.action in ['run','all']:
  for game in games:run(game,a.variant,a.traffic,a.negative)
if __name__=='__main__':main()
