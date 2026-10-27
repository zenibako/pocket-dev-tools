"""Read existing native report formats. No game execution or device writes."""
import csv
from decimal import Decimal
import json
import re

from .model import number, validate_metadata, validate_rows


FORMATS = ('butterscotch-device', 'vvvvvv-host', 'device-summary', 'harness-revision')
FOCUS_MINIMUMS = dict(zip(('encounter-reveal', 'encounter-full', 'observation-reveal',
    'observation-full', 'tiles-walk', 'tiles-reset-cycle', 'tiles-still'), (6, 20, 6, 20, 60, 90, 80)))


def _row(name, metrics, samples=None, **details):
    return dict(id=name, samples=samples, metrics=metrics, **details)


def report_blocks(raw):
    """Locate report headers without interpreting history or NUL padding as runs."""
    value = raw.split(b'\0', 1)[0].decode('utf-8').replace('\r\n', '\n')
    starts = list(re.finditer(r'^=== (?:Focused Deltarune benchmark [^\n]+|(?:Undertale|Deltarune ch\. 1) benchmark, [^\n]+) ===$', value, re.M))
    if not starts:
        raise ValueError('no recognized benchmark report')
    return [value[start.start():starts[i+1].start() if i+1 < len(starts) else len(value)]
            for i, start in enumerate(starts)]


def _device_os(block, metadata):
    match = re.search(r'^OS (\d+\.\d+\.\d+),? (?:core variant|core) (\d+),? CPU (\d+)\s*MHz$', block, re.M)
    if not match:
        raise ValueError('missing device OS/CPU line; host logs are not device evidence')
    firmware, core, mhz = match.groups()
    clock = metadata['platform']['clock_hz']
    if clock is not None and int(mhz)*1000000 != clock:
        raise ValueError('device clock differs from metadata')
    expected_firmware = metadata['platform'].get('firmware')
    if expected_firmware is not None and expected_firmware != firmware:
        raise ValueError('device firmware differs from metadata')
    return dict(firmware=firmware, core_number=int(core), clock_hz=int(mhz)*1000000)


def _butterscotch(raw, metadata, index):
    if metadata['project'] != 'butterscotch':
        raise ValueError('Butterscotch format requires the butterscotch project')
    blocks = report_blocks(raw)
    if index is None:
        if len(blocks) != 1:
            raise ValueError(f'{len(blocks)} reports found; select --report-index explicitly (zero based)')
        index = 0
    if type(index) is not int or index < 0 or index >= len(blocks):
        raise ValueError('report-index is outside the available reports')
    block = blocks[index]
    end = re.search(r'^--- end of report ---$', block, re.M)
    if not end:
        raise ValueError('incomplete report: missing end marker')
    block = block[:end.end()]
    reported = _device_os(block, metadata)
    result = dict(backend='device', rows=[], report_index=index,
                  checks=dict(complete=True, correctness='not_checked', identity='declared'),
                  reported_platform=reported, limits=[
                      'Source revision/compiler attribution is declared unless embedded; flashed binaries are not verified.',
                      'Nested rendering/audio counters are not additive components.'])
    title = block.splitlines()[0]
    if title.startswith('=== Focused'):
        if metadata['game'] != 'deltarune':
            raise ValueError('focused report game differs from metadata')
        mode = re.fullmatch(r'=== Focused Deltarune benchmark (normal|no-render|no-audio|core|profile) ===', title)
        if not mode or mode[1] != metadata['case']['mode']:
            raise ValueError('focused mode differs from metadata')
        if 'route card-castle-tiles; room 65 room_field_checkers4\n' not in block:
            raise ValueError('wrong focused route/scene')
        if metadata['case']['route_version'] != 'card-castle-tiles-v1':
            raise ValueError('unsupported focused route version')
        identity = re.search(r'^build (\S+); seed (\d+); Speed; uncapped; input-frame windows$', block, re.M)
        if not identity or int(identity[2]) != metadata['case']['seed']:
            raise ValueError('focused seed/identity differs from metadata')
        if metadata['conditions']['pacing'] != 'uncapped':
            raise ValueError('focused pacing differs from metadata')
        revision = metadata['build']['source_revision']
        if identity[1] != 'unversioned':
            if len(identity[1]) < 7 or not revision.startswith(identity[1]):
                raise ValueError('embedded build differs from source revision')
            result['checks']['identity'] = 'embedded'
        counterfactual = re.search(r'^counterfactual: render=(on|off) audio=(on|off) profile=(off|ON \(instrumented\))$', block, re.M)
        if not counterfactual:
            raise ValueError('missing focused instrumentation settings')
        expected = dict(normal=('on', 'on', 'off'), **{'no-render': ('off', 'on', 'off'),
                        'no-audio': ('on', 'off', 'off'), 'core': ('off', 'off', 'off'),
                        'profile': ('on', 'on', 'ON (instrumented)')})[mode[1]]
        if counterfactual.groups() != expected or metadata['conditions']['audio'] != expected[1]:
            raise ValueError('focused audio/render/profile settings differ')
        result['comparison_config'] = dict(focus_mode=mode[1], settings=counterfactual.groups())
        completion = re.findall(r'^FOCUS (PASS|FAIL) (\S+)$', block, re.M)
        if len(completion) != 1 or completion[0][1] != mode[1]:
            raise ValueError('missing or mismatched focused PASS/FAIL marker')
        failed = completion[0][0] == 'FAIL' or bool(re.search(r'^FOCUS (ERROR|WINDOW FAIL)', block, re.M))
        result['checks']['correctness'] = 'reported_fail' if failed else 'reported_pass'
        table = re.search(r'^window N filtered mean median p95 max flip present\n', block, re.M)
        if not table:
            raise ValueError('missing focused table')
        for match in re.finditer(r'^(\S+) ((?:\d+ ){7}\d+)$', block[table.end():], re.M):
            name = match[1]
            if name not in FOCUS_MINIMUMS:
                raise ValueError(f'unknown focused window {name}')
            n, filtered, mean, median, p95, maximum, flip, present = map(int, match[2].split())
            if not failed and n < FOCUS_MINIMUMS[name]:
                raise ValueError(f'insufficient samples for {name}')
            if not (median <= p95 <= maximum) or mean > maximum:
                raise ValueError(f'inconsistent focused statistics for {name}')
            result['rows'].append(_row(name, dict(work_mean_us=mean, work_median_us=median,
                work_p95_us=p95, work_max_us=maximum, flip_mean_us=flip,
                present_mean_us=present, filtered_frames=filtered), n))
        if {r['id'] for r in result['rows']} != FOCUS_MINIMUMS.keys():
            raise ValueError('missing focused windows')
        result['limits'].append('Window samples and block means are correlated; Profile totals include instrumentation.')
    else:
        match = re.fullmatch(r'=== (Undertale|Deltarune ch\. 1) benchmark, (speed|accuracy)(.*?) ===', title)
        game = 'undertale' if match[1] == 'Undertale' else 'deltarune'
        if game != metadata['game']:
            raise ValueError('report game differs from metadata')
        if match[2] != metadata['case']['mode']:
            raise ValueError('report mode differs from metadata')
        table = re.search(r'^ms per frame:\s+work\s+total\n(.*?)^(\d+) frames in ([\d.]+) s; full speed is 33\.3$', block, re.M | re.S)
        if not table or int(table[2]) <= 0:
            raise ValueError('missing or incomplete standard frame table')
        for line in table[1].splitlines():
            row = re.fullmatch(r'(.+?)\s+(\d+\.\d+)\s+(\d+\.\d+)', line)
            if not row:
                raise ValueError('malformed standard frame row')
            work, total = (float(Decimal(v)*1000) for v in row.groups()[1:])
            if work > total:
                raise ValueError('work exceeds total frame time')
            result['rows'].append(_row(row[1].strip(), dict(work_mean_us=work, total_mean_us=total)))
        result['reported_frames'] = int(table[2])
        result['comparison_config'] = dict(report_note=match[3], total_frames=int(table[2]))
        result['limits'].append('Standard report supplies means without per-section sample counts or correctness oracles.')
    return result


def _vvvvvv(raw, metadata):
    if metadata['project'] != 'vvvvvv' or metadata['game'] != 'vvvvvv':
        raise ValueError('VVVVVV format requires vvvvvv project/game')
    value = raw.decode('utf-8')
    complete = re.findall(r'^Final sweep passed: (\d+) cases, (\d+) scrolling cases; HOST wall time only$', value, re.M)
    if len(complete) != 1:
        raise ValueError('missing or repeated host sweep completion footer')
    rows, views, scrolls = [], 0, 0
    for line in value.splitlines():
        if not line.startswith(('SWEEP_VIEW,', 'SWEEP_RESULT,')):
            continue
        fields = next(csv.reader([line], strict=True))
        view = fields[0] == 'SWEEP_VIEW'
        if len(fields) != (12 if view else 11):
            raise ValueError('malformed host sweep CSV row')
        numeric = [int(v) for v in fields[1:-1]]
        mode, x, y, entry, camera = numeric[:5]
        if mode not in (0, 1) or camera not in (-1, 0, 192, 384, 568):
            raise ValueError('invalid sweep state/camera')
        if view:
            samples, mean, logic, draw, peak = numeric[5:]
            number(samples, 'sweep samples', integer=True, minimum=1)
            name = f'view:{mode}:{x}:{y}:{entry}:{camera}'
            metrics = dict(frame_mean_us=mean, logic_mean_us=logic, draw_mean_us=draw, frame_max_us=peak)
            views += 1
            scrolls += camera == -1
        else:
            mean, logic, draw, peak = numeric[5:]
            samples = None
            name = f'result:{mode}:{x}:{y}'
            metrics = dict(worst_view_mean_us=mean, worst_view_logic_us=logic,
                           worst_view_draw_us=draw, cross_view_max_us=peak)
        if mean > peak:
            raise ValueError('sweep mean exceeds peak')
        rows.append(_row(name, metrics, samples, room=fields[-1], stabilizer='off' if mode else 'on',
                         entry_y=entry, camera=camera))
    if (views, scrolls) != tuple(map(int, complete[0])):
        raise ValueError('host sweep count differs from completion footer')
    return dict(backend='host', rows=rows,
                checks=dict(complete=True, correctness='reported_pass', identity='declared'),
                comparison_config={}, limits=['Host wall microseconds, not physical Pocket timing.',
                    'Summary peak spans all views and need not belong to the worst-average viewport.',
                    'Smoke-test pass is reported evidence; this importer does not rerun gameplay or pixel oracles.'])


def _summary(raw, metadata):
    value = json.loads(raw)
    if not isinstance(value, dict) or not isinstance(value.get('rows'), list):
        raise ValueError('device summary must contain rows')
    return dict(backend='device', rows=value['rows'], comparison_config={},
                checks=dict(complete=True, correctness='not_checked', identity='declared'),
                limits=['Manually transcribed device values; inspect attached screenshots.',
                        'Completeness means the declared row roster, not independent gameplay validation.',
                        'No percentiles or missing metrics are inferred from screenshots.'])


def _harness(raw, metadata, index):
    value = json.loads(raw)
    cases = value.get('cases') if isinstance(value, dict) else None
    if not isinstance(cases, list) or not cases:
        raise ValueError('expected an experiments.py revision report with cases')
    if index is None:
        if len(cases) != 1:
            raise ValueError('select --report-index for the revision case')
        index = 0
    if type(index) is not int or not 0 <= index < len(cases):
        raise ValueError('report-index is outside revision cases')
    case = cases[index]
    config = case['config']
    if metadata['project'] != 'butterscotch' or config['game'] != metadata['game']:
        raise ValueError('simulation game/project differs from metadata')
    if config['mode'] != metadata['case']['mode'] or case['revision'] != metadata['build']['source_revision']:
        raise ValueError('simulation mode/revision differs from metadata')
    rows = []
    for row in case['rows']:
        cycles = number(row['cycles'], 'simulation cycles', integer=True, minimum=1)
        milliseconds = number(row['simulated_ms'], 'simulated milliseconds')
        frame = number(row['oracle'][0], 'simulation frame', integer=True)
        # Existing revision reports explicitly use the 100 MHz os25 model.
        if abs(milliseconds - cycles / 100000) > 0.000001:
            raise ValueError('simulation cycles/ms disagree at the source model clock')
        rows.append(_row(f'frame:{frame}', dict(frame_cycles=cycles,
                         simulated_frame_us=cycles / 100), 1))
    if metadata['platform']['variant'] != 'os25' or metadata['platform']['clock_hz'] != 100000000:
        raise ValueError('revision report requires its original os25/100MHz platform')
    # Only the application snapshot is expected to change across revisions.
    # Preserve adapter/launcher hashes and future model settings automatically.
    context = {key: val for key, val in config.items() if key not in ('snapshot', 'snapshot_sha256')}
    for key in ('compiler_version', 'source_flags', 'build_kind', 'native_scripts',
                'substitutions', 'oracle_excluded_fields'):
        context[key] = case.get(key)
    limits = value.get('limits', [])
    if not isinstance(limits, list) or any(not isinstance(v, str) for v in limits):
        raise ValueError('revision limits must be strings')
    return dict(backend='simulation', rows=rows, report_index=index, source_config=config,
                substitutions=case.get('substitutions', []),
                oracle_excluded_fields=case.get('oracle_excluded_fields', []),
                comparison_config=context,
                checks=dict(complete=True, identity='declared', correctness=(
                    'reported_pass' if case.get('negative_oracle_rejected') is True else 'not_checked')),
                limits=limits + ['Archived revision report; original private source/capture hashes have not been reverified.',
                                'Simulated cycles, not physical Pocket performance.'])


def parse_report(format_name, raw, metadata, report_index=None):
    metadata = validate_metadata(metadata)
    if format_name not in FORMATS:
        raise ValueError('unsupported report format')
    if report_index is not None and format_name not in ('butterscotch-device', 'harness-revision'):
        raise ValueError('this format has no selectable report-index')
    try:
        if format_name == 'butterscotch-device':
            result = _butterscotch(raw, metadata, report_index)
        elif format_name == 'vvvvvv-host':
            result = _vvvvvv(raw, metadata)
        elif format_name == 'device-summary':
            result = _summary(raw, metadata)
        else:
            result = _harness(raw, metadata, report_index)
        validate_rows(result['rows'], metadata)
    except (KeyError, TypeError, UnicodeError, csv.Error, IndexError) as exc:
        raise ValueError(f'malformed {format_name} report: {exc}') from exc
    result.update(schema_version=1, adapter=format_name + ':v1', metadata=metadata)
    return result
