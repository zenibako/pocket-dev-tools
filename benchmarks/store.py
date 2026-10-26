"""Copy explicit inputs into new private bundles and detect stale evidence."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil

from .adapters import parse_report, report_blocks
from .model import validate_metadata, validate_rows


MAX_FILE_BYTES = 32 * 1024 * 1024


def _encode(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _read(path):
    path = Path(path)
    with path.open('rb') as stream:
        data = stream.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise ValueError(f'file exceeds {MAX_FILE_BYTES} bytes: {path}')
    return data


def inspect_source(source):
    reports = []
    for index, block in enumerate(report_blocks(_read(source))):
        identity = re.search(r'^build (\S+);', block, re.M)
        reports.append(dict(index=index, title=block.splitlines()[0],
                            complete=bool(re.search(r'^--- end of report ---$', block, re.M)),
                            embedded_build=identity[1] if identity else None))
    return reports


def collect(source, metadata_path, format_name, *, output, attachments=(), report_index=None):
    source = Path(source)
    raw, original_metadata = _read(source), _read(metadata_path)
    metadata = validate_metadata(json.loads(original_metadata))
    result = parse_report(format_name, raw, metadata, report_index)
    extra = [(Path(path), _read(path)) for path in attachments]
    if format_name == 'device-summary':
        signatures = (b'\x89PNG\r\n\x1a\n', b'\xff\xd8\xff', b'GIF87a', b'GIF89a')
        if not extra or any(not data.startswith(signatures) for _, data in extra):
            raise ValueError('device-summary requires original PNG/JPEG/GIF screenshot attachments')
    files = {'metadata.json': original_metadata}
    evidence = []
    for index, (path, data) in enumerate([(source, raw)] + extra):
        # Paths are assigned locally; source names never become destination paths.
        name = f'raw/{index:03d}{path.suffix.lower() if path.suffix.lower() in (".sav", ".json", ".csv", ".txt", ".png", ".jpg", ".jpeg", ".gif") else ".bin"}'
        files[name] = data
        evidence.append(dict(path=name, original_name=path.name, sha256=_sha(data), bytes=len(data)))
    identity = dict(adapter=result['adapter'], metadata=metadata,
                    report_index=result.get('report_index'),
                    evidence=[dict(sha256=item['sha256'], bytes=item['bytes']) for item in evidence])
    run_id = _sha(_encode(identity))[:24]
    result.update(run_id=run_id, evidence=evidence,
                  imported_at=datetime.now(timezone.utc).isoformat())
    files['result.json'] = _encode(result)
    folder = Path(output) / run_id
    folder.parent.mkdir(parents=True, exist_ok=True)
    try:
        folder.mkdir()
    except FileExistsError as exc:
        raise ValueError(f'run already exists; original evidence preserved: {folder}') from exc
    try:
        for name, data in files.items():
            target = folder / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as stream:
                stream.write(data)
        # Written last: an interrupted bundle is incomplete, never a valid run.
        manifest = dict(schema_version=1, run_id=run_id,
                        files={name: _sha(data) for name, data in files.items()})
        with (folder / 'manifest.json').open('xb') as stream:
            stream.write(_encode(manifest))
    except BaseException:
        shutil.rmtree(folder)
        raise
    return folder.resolve()


def load_run(directory):
    folder = Path(directory).resolve()
    manifest = json.loads(_read(folder / 'manifest.json'))
    if manifest.get('schema_version') != 1 or not isinstance(manifest.get('files'), dict):
        raise ValueError('unsupported bundle manifest')
    for name, expected in manifest['files'].items():
        if not isinstance(name, str):
            raise ValueError('invalid evidence path')
        path = folder / name
        if Path(name).is_absolute() or '..' in Path(name).parts or not path.resolve().is_relative_to(folder):
            raise ValueError('evidence path escapes bundle')
        if _sha(_read(path)) != expected:
            raise ValueError(f'evidence hash mismatch: {name}')
    if not {'metadata.json', 'result.json'}.issubset(manifest['files']):
        raise ValueError('incomplete bundle manifest')
    result = json.loads(_read(folder / 'result.json'))
    metadata = validate_metadata(json.loads(_read(folder / 'metadata.json')))
    if result.get('schema_version') != 1 or result.get('run_id') != manifest.get('run_id') or result.get('metadata') != metadata:
        raise ValueError('bundle metadata/result identity mismatch')
    validate_rows(result.get('rows'), metadata)
    for evidence in result.get('evidence', []):
        if manifest['files'].get(evidence['path']) != evidence['sha256']:
            raise ValueError('raw evidence hash is missing from manifest')
    if not result.get('evidence'):
        raise ValueError('missing raw evidence')
    return result
