#!/usr/bin/env python3
"""Capture and replay complete battle frames inside the isolated harness."""
import argparse,hashlib,json,os,re,struct,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));import run as leaf
BUILD=ROOT/'build/fullframe';IMAGE='undertale-vm-os25-frames:local'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def docker():return ['docker','--config',str(ROOT/'build/docker-config'),'-H',os.environ.get('HARNESS_DOCKER_HOST','unix://'+str(Path.home()/'.config/colima/default/docker.sock'))]
def container():return [*docker(),'run','--rm','-v',str(ROOT)+':/work','-w','/work',IMAGE]
def parse(log):
 rows=[]
 for m in re.finditer(r'^FRAMERESULT (\d+) (\d+) ([0-9a-f]+) ([0-9a-f]+) ([0-9a-f]+) (\d+) (\d+) (\d+) ([0-9a-f]+)$',log,re.M):
  f,c,s,p,a,n,o,e,t=m.groups();rows.append([int(f),int(s,16),int(p,16),int(a,16),int(n),int(o),int(e),int(t,16)])
 if len(rows)!=3 or 'FRAMEHARNESS PASS HAL init' not in log:raise RuntimeError('Incomplete full-frame capture')
 return rows

def capture(game,variant):
 d=BUILD/game/variant;data=ROOT/'inputs/butterscotch/src/openfpga'
 if game=='deltarune':data=data/'games/deltarune'
 results=[]
 for repeat in range(2):
  run=d/f'repeat-{repeat}';run.mkdir(parents=True,exist_ok=True)
  for name in ['data.win','textures.bin','music.bin','audiogroup1.dat','lang_en.json','music']:
   src=data/name;dest=run/name
   if src.exists() and not dest.exists():dest.symlink_to(os.path.relpath(src,run))
  cmd=[*container(),'sh','-c',f'cd /work/{run.relative_to(ROOT)} && qemu-riscv32 -B 0x100000000 /work/{(d/"program.elf").relative_to(ROOT)}']
  print('Capturing complete frames',game,variant,repeat,flush=True)
  with (run/'capture.log').open('w') as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
  results.append(parse((run/'capture.log').read_text()))
 if results[0]!=results[1]:raise RuntimeError('Complete-frame oracles changed between captures')
 for name in ['checkpoint.bin','stack.bin','checkpoint-info.bin']:
  if sha(d/'repeat-0'/name)!=sha(d/'repeat-1'/name):raise RuntimeError('RV32 checkpoint not reproducible: '+name)
 manifest=dict(game=game,variant=variant,seed=7,rows=results[0],elf_sha256=sha(d/'program.elf'),source_data_sha256=sha(data/'data.win'),build=json.loads((d/'build.json').read_text()),
               repeats=[{name:sha(d/f'repeat-{r}'/name) for name in ['checkpoint.bin','stack.bin','checkpoint-info.bin','capture.log','frame-0.ppm','frame-1.ppm','frame-2.ppm']} for r in range(2)])
 (d/'capture.json').write_text(json.dumps(manifest,indent=2)+'\n');print('PASS complete frames',game,variant,[(r[0],r[5],r[6]) for r in results[0]],flush=True)

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('action',choices=['toolchain','build','capture','prepare','rtl','run','all']);ap.add_argument('--game',choices=['undertale','deltarune']);ap.add_argument('--variant',choices=['sdram','bram'],default='sdram');ap.add_argument('--traffic',choices=['quiet','scanout'],default='quiet');ap.add_argument('--jobs',type=int,default=4);ap.add_argument('--negative',action='store_true',help='Deliberately corrupt one expected state hash; require rejection');a=ap.parse_args()
 leaf.verify_inputs();BUILD.mkdir(exist_ok=True)
 games=[a.game] if a.game else ['undertale','deltarune']
 if a.action=='toolchain':
  with (ROOT/'fullframe/Dockerfile').open('rb') as f:subprocess.run([*docker(),'build','-t',IMAGE,'-'],stdin=f,check=True)
  return
 if a.action in ['build','all']:subprocess.run([*container(),'python3','fullframe/build.py','--variant',a.variant,*(['--game',a.game] if a.game else [])],check=True)
 if a.action in ['capture','all']:
  for game in games:capture(game,a.variant)
 if a.action in ['prepare','rtl','run','all']:subprocess.run([*container(),'python3','fullframe/rtl.py',a.action,'--variant',a.variant,'--traffic',a.traffic,'--jobs',str(a.jobs),*(['--game',a.game] if a.game else []),*(['--negative'] if a.negative else [])],check=True)
 leaf.verify_inputs()
if __name__=='__main__':main()
