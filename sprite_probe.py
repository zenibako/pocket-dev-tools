#!/usr/bin/env python3
"""Capture/replay the pinned renderer probe in independent harness-only cases."""
import argparse,hashlib,json,os,re,shutil,subprocess
from pathlib import Path
import experiments
ROOT=experiments.ROOT


def create(args):
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9._-]*',args.snapshot):
        raise ValueError('Snapshot must be a local name, not a path')
    source=ROOT/'experiments/snapshots'/args.snapshot;experiments.verify_inputs(source)
    config=dict(snapshot=args.snapshot,game='deltarune',window='dodge',first_frame=3323,
                mode='speed',kind='timing',variant='bram',profile='port',alignment=True,native='enabled',
                framebuffer='cached',clock_cost=0,audio='fixed',compiler=args.compiler,
                snapshot_sha256=experiments.sha(source/'snapshot.json'),workload='sprite-probe',
                selection=args.selection,probe_samples=24,probe_calls=2000,probe_repeats=3,
                probe_begin_symbol='sprite_probe_begin',probe_end_symbol='sprite_probe_end',
                renderer_profiling=False,gml_profiling=False,
                adapter_sources={str(p.relative_to(ROOT)):experiments.sha(p) for folder in ['bench','spriteprobe'] for p in (ROOT/folder).iterdir() if p.is_file()},
                launcher_sha256=experiments.sha(Path(__file__)))
    key=hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()[:16]
    case=ROOT/'experiments/cases'/('sprite-'+args.snapshot+'-'+args.selection+'-'+key)
    if case.exists():raise ValueError('Preserve existing probe evidence; choose a new snapshot name')
    platform=experiments.platform();experiments.tooling(case)
    experiments.copy_tree(source/'inputs',case/'inputs')
    for name in ['snapshot.json','input-manifest.json']:shutil.copy2(source/name,case/name)
    shutil.copytree(ROOT/'spriteprobe',case/'spriteprobe',ignore=shutil.ignore_patterns('__pycache__'))
    experiments.save(case/'experiment.json',config)
    experiments.copy_tree(platform/'build/rtl',case/'build/rtl')
    experiments.copy_tree(platform/'build/fullframe/rtl',case/'build/fullframe/rtl')
    return case,config


def capture(case,config):
    directory=case/'build/fullframe/deltarune/bram';assets=case/'inputs/butterscotch/src/openfpga/games/deltarune'
    rows=[];repeats=[];settings=[]
    for repeat in range(2):
        dest=directory/('repeat-'+str(repeat));dest.mkdir()
        for name in ['data.win','textures.bin','music.bin','audiogroup1.dat','lang_en.json','music']:
            path=assets/name
            if path.exists():(dest/name).symlink_to(os.path.relpath(path,dest))
        cmd=experiments.docker(case,'sh','-c',f'cd /work/{dest.relative_to(case)} && qemu-riscv32 -B 0x100000000 /work/{directory.relative_to(case)}/program.elf')
        with (dest/'capture.log').open('w') as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
        text=(dest/'capture.log').read_text()
        found=[]
        for m in re.finditer(r'^FRAMERESULT (\d+) (\d+) ([0-9a-f]+) ([0-9a-f]+) ([0-9a-f]+) (\d+) (\d+) (\d+) ([0-9a-f]+)$',text,re.M):
            f,c,s,p,a,n,o,e,t=m.groups();found.append([int(f),int(s,16),int(p,16),int(a,16),int(n),int(o),int(e),int(t,16)])
        if len(found)!=24 or 'FRAMEHARNESS PASS HAL init' not in text:raise ValueError('Incomplete sprite capture')
        rows.append(found);settings.append(re.findall(r'^SPRITECONFIG .+$',text,re.M))
        files=['checkpoint.bin','stack.bin','checkpoint-info.bin','capture.log']+[f'frame-{i}.{ext}' for i in range(24) for ext in ['ppm','rgb555','pcm']]
        repeats.append({name:experiments.sha(dest/name) for name in files})
    if rows[0]!=rows[1] or repeats[0]!=repeats[1] or settings[0]!=settings[1]:raise ValueError('Probe capture/checkpoint/raw output was not reproducible')
    experiments.save(directory/'capture.json',dict(game='deltarune',variant='bram',seed=7,rows=rows[0],
        elf_sha256=experiments.sha(directory/'program.elf'),source_data_sha256=experiments.sha(assets/'data.win'),
        build=json.loads((directory/'build.json').read_text()),repeats=repeats,probe_settings=settings[0],
        oracle_fields=['sample','same-binary game state','pixels','sprite','calls','width','height','stage/path']))
    print('PASS two identical probe captures and checkpoints',case,flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--snapshot',required=True);p.add_argument('--compiler',default='container');p.add_argument('--selection',choices=['40x40','grid'],default='40x40');args=p.parse_args()
    case,config=create(args)
    command=['spriteprobe/build.py','--game','deltarune','--variant','bram']
    if args.compiler=='container':subprocess.run(experiments.docker(case,'python3',*command),check=True)
    else:subprocess.run(['python3',str(case/command[0]),*command[1:],'--compiler',args.compiler],check=True)
    capture(case,config)
    for action in ['prepare','run']:subprocess.run(experiments.docker(case,'python3','fullframe/rtl.py',action,'--game','deltarune','--variant','bram'),check=True)
    experiments.verify_inputs(case);print('PROBECASE',case,flush=True)

if __name__=='__main__':main()
