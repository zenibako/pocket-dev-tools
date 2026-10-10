#!/usr/bin/env python3
"""Build one SDK ELF for hardware, QEMU oracles and bare RTL entry."""
import hashlib,json,struct,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import capture
from elftools.elf.elffile import ELFFile

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def expected():
    n=2047;mask=(1<<32)-1;x=1000000
    for _ in range(n*8):x=x//7+101
    bits=lambda value:struct.unpack('<I',struct.pack('<f',value))[0]
    return dict(INTEGER_DEP=1+n*24,INTEGER_INDEPENDENT=28+n*24,MULTIPLY=pow(3,n*8,1<<32),
                DIVIDE=x,STREAM=((8191*8)*(8191*8-1)//2*2654435761)&mask,
                FP_ADD=bits(1+n*8),CONVERT=1+n*8)

def build():
    config=json.loads((ROOT/'calibration.json').read_text());d=ROOT/'build/calibration';d.mkdir(parents=True,exist_ok=True)
    (d/'expected.h').write_text('\n'.join(f'#define EXPECTED_{k} 0x{v:08x}u' for k,v in expected().items())+'\n')
    (d/'build_id.h').write_text('#define CAL_BUILD_ID "'+config['id']+'"\n')
    # Each 64-byte block has observable arithmetic and an explicit next jump.
    asm=['.section .text.cal_icache_stream,"ax"','.balign 64','.global cal_icache_stream',
         '.type cal_icache_stream,@function','cal_icache_stream:','li a1,0','.Lagain:']
    for i in range(1024):asm+=['.balign 64',f'.Lblock{i}:','addi a1,a1,1',f'j .Lblock{i+1}' if i<1023 else 'j .Ldone']
    asm+=['.Ldone:','addi a0,a0,-1','bnez a0,.Lagain','mv a0,a1','ret','.size cal_icache_stream,.-cal_icache_stream']
    (d/'icache.S').write_text('\n'.join(asm)+'\n')
    src=ROOT/'inputs/butterscotch/src';vendor=ROOT/'inputs/butterscotch/vendor'
    header=capture.once((src/'sw/sw_call_notes.h').read_text(),'#ifdef SW_DRAW_PROFILE','#if defined(SW_DRAW_PROFILE) || defined(SWR_SPRITE_PROBE)')
    (d/'sw_call_notes.h').write_text(header)
    (d/'renderer.c').write_text((src/'sw/sw_renderer.c').read_text()+'\n'+(ROOT/'calibration/sprite.inc').read_text())
    # Quote includes in the copied drawing file resolve the independent probe gates.
    (d/'drawing.c').write_text((src/'sw/sw_drawing.c').read_text())
    pack=(src/'sw/sw_texture_pack.c').read_text()
    pack+='\nvoid calibration_pack_init(void){static PackPage page={512,512,0};packPages=&page;packCount=1;packProbed=true;}\n'
    (d/'pack.c').write_text(pack)
    # Only retained renderer paths survive GC; never compile the port's main.
    paths=[p for p in sorted(src.glob('*.c')) if p.name!='log.c']
    paths += [d/'renderer.c' if p.name=='sw_renderer.c' else d/'drawing.c' if p.name=='sw_drawing.c' else d/'pack.c' if p.name=='sw_texture_pack.c' else p for p in sorted((src/'sw').glob('*.c'))]
    paths += [*sorted((src/'image').glob('*.c')),*sorted((src/'debug_font').glob('*.c')),src/'embedded/stb_impl.c',
              *sorted((vendor/'bzip2').glob('*.c')),*[vendor/p for p in ['sha1/sha1.c','md5/md5.c','base64/base64.c','miniz/miniz.c','miniz/miniz_tdef.c','miniz/miniz_tinfl.c']]]
    paths += [ROOT/'calibration'/p for p in ['runtime.c','kernels.c','save_log.c','start.S']]+[d/'icache.S',ROOT/'hardware-sdk/of_init.c']
    flags=['-march=rv32imafc_zicsr_zifencei','-mabi=ilp32f','-O2','-g','-ffunction-sections','-fdata-sections',
           '-falign-functions=64','-falign-loops=64','-fno-tree-loop-distribute-patterns','-nostdinc',
           '-isystem',str(ROOT/'inputs/sdk/musl/include'),'-DENABLE_WAD17','-DUSE_FLOAT_REALS','-DNO_RVALUE_INT64',
           '-DENABLE_SW_RENDERER','-DPIXEL_SIZE=16','-DSWR_SPRITE_PROBE']
    includes=[d,ROOT/'calibration',ROOT/'inputs/sdk/include',src,src/'sw',src/'image',src/'video',src/'debug_font',
              *[vendor/p for p in ['stb/ds','stb/image','stb/vorbis','bzip2','sha1','md5','base64','miniz']]]
    musl=ROOT/'inputs/sdk/musl/lib';compiler='riscv64-unknown-elf-gcc'
    command=[compiler,*flags,*['-I'+str(p) for p in includes],'-nostdlib','-nostartfiles','-static',
             str(musl/'crt1.o'),str(musl/'crti.o'),*map(str,paths),str(musl/'crtn.o'),
             '-Wl,-T,'+str(ROOT/'hardware-sdk/app.ld'),'-Wl,--gc-sections','-Wl,-u,_rtl_start',
             '-Wl,-Map,'+str(d/'app.map'),'-L'+str(musl),'-Wl,--start-group','-lc','-lm','-lgcc','-Wl,--end-group','-o',str(d/'app.elf')]
    with (d/'compile.log').open('w') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
    with (d/'app.elf').open('rb') as f:
        elf=ELFFile(f);symbols={s.name:dict(address=s.entry.st_value,size=s.entry.st_size) for s in elf.get_section_by_name('.symtab').iter_symbols()}
        if elf.header.e_entry!=symbols['_start']['address'] or symbols['_rtl_start']['address']!=0x10400000:
            raise ValueError('Expected normal SDK entry and separate bare RTL entry')
        if any(name.startswith(('SWRenderer_prof','VMProfiler_')) or name in ['frame_tick','frame_event','swrNoteKeyed'] for name in symbols):
            raise ValueError('Calibration contains unwanted profiling')
        end=max(s.header.sh_addr+s.header.sh_size for s in elf.iter_sections() if s.header.sh_flags&2 and s.header.sh_size)
        if not 0x10400000<end<0x10800000:raise ValueError('Calibration image exceeds the supported static map')
        image=bytearray(end-0x10400000)
        for s in elf.iter_sections():
            if s.header.sh_flags&2 and s.header.sh_size and s.header.sh_type!='SHT_NOBITS':
                image[s.header.sh_addr-0x10400000:s.header.sh_addr-0x10400000+s.header.sh_size]=s.data()
        entry=elf.header.e_entry
    # Regular and corrupted-oracle images differ at exactly the designated word.
    (d/'program.bin').write_bytes(image);bad=bytearray(image)
    struct.pack_into('<I',bad,symbols['calibration_expected_bias']['address']-0x10400000,1)
    (d/'negative.bin').write_bytes(bad);(d/'stack.bin').write_bytes(bytes(0x80000))
    bram=bytearray(struct.pack('<I',0x13)*8192);struct.pack_into('<II',bram,0,0x104002b7,0x00028067)
    (d/'firmware.mif').write_text('WIDTH=32;\nDEPTH=8192;\nADDRESS_RADIX=DEC;\nDATA_RADIX=HEX;\nCONTENT BEGIN\n'+
        ''.join(f'{i} : {struct.unpack_from("<I",bram,i*4)[0]:08X};\n' for i in range(8192))+'END;\n')
    dump=subprocess.check_output(['riscv64-unknown-elf-objdump','-d',str(d/'app.elf')],text=True)
    (d/'app.disassembly.txt').write_text(dump)
    tracked=[*paths,ROOT/'calibration/calibration.h',ROOT/'calibration/save_log.h',ROOT/'calibration/sprite.inc',ROOT/'calibration/build.py',
             ROOT/'hardware-sdk/app.ld',ROOT/'calibration.json',d/'expected.h',d/'build_id.h',d/'sw_call_notes.h']
    manifest=dict(config=config,compiler_version=subprocess.check_output([compiler,'--version'],text=True).splitlines()[0],
        flags=flags,command=command,entry=entry,rtl_entry=symbols['_rtl_start']['address'],
        sources={str(p.relative_to(ROOT)):sha(p) for p in tracked},
        artifacts={p.name:sha(p) for p in d.iterdir() if p.is_file()},
        symbols=symbols,expected=expected(),cpu_parameter_changes={})
    (d/'build.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n');print('BUILT identical hardware/reference/RTL ELF',d/'app.elf',flush=True)

if __name__=='__main__':build()
