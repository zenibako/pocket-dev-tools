#!/usr/bin/env python3
"""Verify the complete eight-configuration replay matrix and collect its evidence."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'build/fullframe'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_hash(path, expected):
    if sha(path) != expected:
        raise RuntimeError(f'Evidence changed: {path}')


def main():
    inputs = json.loads((ROOT / 'input-manifest.json').read_text())
    for name, digest in inputs['sources'].items():
        verify_hash(ROOT / name, digest)
    rtl = json.loads((BUILD / 'rtl/rtl.json').read_text())
    verify_hash(BUILD / 'rtl/obj/Vtb_system', rtl['simulator_sha256'])
    verify_hash(BUILD / 'rtl/main.cpp', rtl['source_sha256'])
    verify_hash(ROOT / 'fullframe/rtl.py', rtl['generator_sha256'])
    verify_hash(ROOT / 'build/rtl/rtl.json', rtl['leaf_rtl_sha256'])
    cases, negatives, captures = [], [], []
    for game in ['undertale', 'deltarune']:
        for variant in ['sdram', 'bram']:
            directory = BUILD / game / variant
            capture = json.loads((directory / 'capture.json').read_text())
            prepared = json.loads((directory / 'prepared.json').read_text())
            loop = prepared['execute_loop_address']
            if not ((variant == 'bram' and 0x4000 <= loop < 0x7800) or (variant == 'sdram' and 0x10400000 <= loop < 0x10800000)):
                raise RuntimeError('Wrong interpreter placement')
            verify_hash(directory / 'capture.json', prepared['capture_sha256'])
            verify_hash(directory / 'program.elf', capture['elf_sha256'])
            for name, field in [('program.bin', 'image_sha256'), ('stack.bin', 'stack_sha256'), ('firmware.mif', 'bram_sha256')]:
                verify_hash(directory / name, prepared[field])
            for name, digest in capture['build']['sources'].items():
                verify_hash(ROOT / name, digest)
            for repeat, files in enumerate(capture['repeats']):
                for name, digest in files.items():
                    verify_hash(directory / f'repeat-{repeat}' / name, digest)
            for name in ['checkpoint.bin', 'stack.bin', 'checkpoint-info.bin']:
                if capture['repeats'][0][name] != capture['repeats'][1][name]:
                    raise RuntimeError('Non-reproducible checkpoint')
            captures.append(dict(game=game, variant=variant, capture=capture, prepared=prepared))
            for traffic in ['quiet', 'scanout']:
                result = json.loads((directory / f'{traffic}-results.json').read_text())
                if result['prepared'] != prepared or result['rtl'] != rtl:
                    raise RuntimeError('Stale replay result')
                verify_hash(directory / f'{traffic}.log', result['log_sha256'])
                if [row['oracle'] for row in result['rows']] != capture['rows']:
                    raise RuntimeError('Wrong complete-frame oracles')
                cases.append(result)
            negative = json.loads((directory / 'negative-results.json').read_text())
            if not negative['rejected'] or negative['prepared'] != prepared or negative['rtl'] != rtl:
                raise RuntimeError('Stale or missing intentional failure')
            verify_hash(directory / 'negative.log', negative['log_sha256'])
            negatives.append(negative)
    report = dict(passed=True, configurations=len(cases), frame_rows=sum(len(case['rows']) for case in cases),
                  negative_cases=len(negatives), frozen_inputs=len(inputs['sources']), cases=cases,
                  negatives=negatives, captures=captures, isolation='Standalone snapshot; only this directory is mounted in Docker. Active checkout and SD card are not used.',
                  limits='Instrumented software-rendered game-loop frames. Virtual clock/input/audio queue and read-only file service. GPU execution, physical SD latency, display hardware, and production malloc are not measured.')
    (BUILD / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f"PASS {len(cases)} configurations, {report['frame_rows']} complete frames, {len(negatives)} rejected bad state oracles; {report['frozen_inputs']} frozen inputs unchanged")
    for case in cases:
        print(case['game'], case['variant'], case['traffic'], [row['cycles'] for row in case['rows']])


if __name__ == '__main__':
    main()
