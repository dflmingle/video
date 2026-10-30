"""Audit archived source assets and the current preview without running combat."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'docs/materials/manifest.json'
VARIANT = 'V22R-topfield-T1'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def inventory():
    result = set()
    for folder in ['assets/imported', 'assets/runtime', 'assets/references',
                   'assets/source-packages', 'docs/requirements/original']:
        result.update(p for p in (ROOT / folder).rglob('*') if p.is_file())
    native = ROOT / 'public/native-scenes'
    result.update(p for p in native.rglob('*') if p.is_file()
                  and p.relative_to(native).parts[0] != 'native-scenes')
    variant = ROOT / 'variants' / VARIANT
    result.update(p for p in variant.iterdir() if p.suffix in {'.f32', '.json'})
    result.add(ROOT / 'variants' / (VARIANT + '-seed') / 'params.json')
    return sorted(result)


def dependencies():
    required = set()
    builtins = set()

    def original(path):
        if path == 'Resources/unity_builtin_extra':
            builtins.add(path)
        elif path:
            required.add(ROOT / 'assets/imported' / path)

    armies = json.loads((ROOT / 'assets/runtime/manifest.json').read_text('utf-8'))
    for entry in armies.values():
        for field in ['file', 'texture']:
            required.add(ROOT / entry[field].lstrip('/'))
        for field, hash_field in [('source', 'sourceSHA256'),
                                  ('textureSource', 'textureSHA256')]:
            original(entry[field])
            path = ROOT / 'assets/imported' / entry[field]
            assert digest(path) == entry[hash_field], f'Source hash mismatch: {path}'
    for path in (ROOT / 'public/native-scenes').glob('*/manifest.json'):
        manifest = json.loads(path.read_text('utf-8-sig'))
        required.add(path)
        original(manifest.get('source'))
        for mesh in manifest.get('meshes', []):
            required.add(path.parent / mesh['file'])
            original(mesh.get('asset'))
        for material in manifest.get('materials', []):
            for field in ['path', 'texturePath', 'authoredShaderPath']:
                original(material.get(field))
            for texture in material.get('textures', []):
                original(texture.get('path'))
    required.add(ROOT / 'public/native-scenes/textures/08ce35de-decoded.png')
    base = ROOT / 'variants' / VARIANT
    required.update(base / name for name in [
        'params.json', 'simulation.json', 'trajectories.f32', 'hit-times.f32',
        'gait-distance.f32', 'blue-control.f32', 'red-control.f32',
        'gait-cycles.f32', 'melee-control.f32', 'blue-hit-times.f32'])
    config = json.loads((base / 'params.json').read_text('utf-8'))
    texture = config['sceneLayout']['groundTextureOverride']
    required.add(ROOT / 'public' / texture.lstrip('/'))
    assert config['meleeContinuation'], 'Wrong preview variant'
    assert config['fps'] == 60, 'Unexpected time base'
    return required, sorted(builtins)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true', help='Write inventory snapshot')
    parser.add_argument('--check-index', action='store_true', help='Require all assets in Git index')
    args = parser.parse_args()
    files = inventory()
    required, builtins = dependencies()
    provenance = json.loads((ROOT / 'docs/requirements/original-document.json').read_text('utf-8'))
    assert digest(ROOT / provenance['repositoryPath']) == provenance['sha256'], 'Original PDF hash differs'
    missing = sorted(str(p.relative_to(ROOT)) for p in required if not p.is_file())
    assert not missing, f'Missing dependencies: {missing}'
    assert required <= set(files), 'Dependency not included in inventory'
    records = [{'path': p.relative_to(ROOT).as_posix(), 'bytes': p.stat().st_size,
                'sha256': digest(p)} for p in files]
    report = {'variant': VARIANT, 'fileCount': len(records),
              'totalBytes': sum(r['bytes'] for r in records),
              'requiredDependencyCount': len(required),
              'engineBuiltinIdentifiers': builtins, 'files': records}
    if args.write:
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    else:
        assert report == json.loads(REPORT.read_text('utf-8')), 'Archive differs from snapshot'
    if args.check_index:
        tracked = set(subprocess.check_output(
            ['git', 'ls-files', '-z'], cwd=ROOT).decode('utf-8').split('\0'))
        assert all(r['path'] in tracked for r in records), 'Archive files missing from Git index'
    print(f'PASS: {len(records)} archived files, {len(required)} dependencies, '
          f'{report["totalBytes"] / 1024**2:.2f} MiB; no missing dependencies')


if __name__ == '__main__':
    main()
