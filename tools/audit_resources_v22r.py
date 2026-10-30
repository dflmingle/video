"""Read-only inventory. Does not modify originals or import package assets."""
import collections, hashlib, json, os, re, tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOME = Path('C:/Users/89trillion')
OUT = ROOT / 'docs/v22r'
OUT.mkdir(parents=True, exist_ok=True)
EXTS = {'.unity', '.prefab', '.fbx', '.obj', '.glb', '.gltf', '.mat', '.png', '.jpg', '.jpeg', '.tga', '.pdf', '.docx', '.unitypackage'}
SKIP = {'Library', 'Temp', 'node_modules', '.git', 'Logs', 'obj', 'bin'}
GUID = re.compile(r'guid: ([a-f0-9]{32})')

def files(root):
    for directory, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = [d for d in dirs if d not in SKIP]
        for name in names:
            yield Path(directory) / name

def save(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

def scan_disk(root, tag):
    paths = list(files(root))
    guids = {}
    for p in paths:
        if p.suffix == '.meta':
            m = GUID.search(p.read_text(encoding='utf-8', errors='replace')[:4096])
            if m: guids[m[1]] = str(p)[:-5]
    scenes = []
    for p in paths:
        if p.suffix.lower() != '.unity': continue
        refs, seen, queue = {}, set(), [str(p)]
        while queue:
            item = queue.pop()
            if item in seen: continue
            seen.add(item)
            file = Path(item)
            if file.suffix.lower() not in {'.unity', '.prefab', '.mat', '.asset', '.meta'}: continue
            if not file.is_file(): continue
            for guid in set(GUID.findall(file.read_text(encoding='utf-8', errors='replace'))):
                target = guids.get(guid)
                refs[guid] = target
                if target: queue.append(target)
        text = p.read_text(encoding='utf-8', errors='replace')
        scenes.append({'path': str(p), 'bytes': p.stat().st_size, 'names': re.findall(r'^  m_Name: (.+)$', text, re.M)[:80], 'refs': refs, 'resolvedTypes': dict(collections.Counter(Path(x).suffix.lower() for x in refs.values() if x))})
    selected = [str(p) for p in paths if p.suffix.lower() in EXTS]
    result = {'root': str(root), 'fileCount': len(paths), 'types': dict(collections.Counter(Path(x).suffix.lower() for x in selected)), 'scenes': scenes, 'files': selected}
    save(f'resources-{tag}.json', result)
    return {'root': str(root), 'fileCount': len(paths), 'types': result['types'], 'scenes': [{'path': s['path'], 'types': s['resolvedTypes']} for s in scenes]}

def scan_package(p):
    records = {}
    try:
        with tarfile.open(p, 'r:gz') as archive:
            for member in archive:
                guid, _, kind = member.name.partition('/')
                record = records.setdefault(guid, {})
                if kind == 'pathname': record['path'] = archive.extractfile(member).read().decode('utf-8', 'replace').strip()
                elif kind == 'asset': record['bytes'] = member.size
        entries = [dict(guid=k, **v) for k, v in records.items() if 'path' in v]
        return {'path': str(p), 'bytes': p.stat().st_size, 'entries': entries, 'types': dict(collections.Counter(Path(x['path']).suffix.lower() for x in entries)), 'scenes': [x for x in entries if x['path'].lower().endswith('.unity')]}
    except Exception as e:
        return {'path': str(p), 'error': str(e)}

def main():
    summary = {'disk': [], 'packages': []}
    for tag, root in [('project', HOME/'My project/Assets'), ('provided-extracted', HOME/'PveMontageShot01V22/assets/imported')]:
        summary['disk'].append(scan_disk(root, tag))
    supplied = []
    for root in [HOME/'Documents/WXWork', HOME/'Downloads', HOME/'Desktop', HOME/'Pictures']:
        for p in files(root):
            if p.suffix.lower() == '.unitypackage': supplied.append(p)
    for i, p in enumerate(sorted(set(supplied))):
        result = scan_package(p)
        save(f'package-{i:02d}.json', result)
        summary['packages'].append({k:v for k,v in result.items() if k != 'entries'})
        print(json.dumps({'package': str(p), 'scenes': [s['path'] for s in result.get('scenes',[])], 'error': result.get('error')}, ensure_ascii=False), flush=True)
    save('resource-search-summary.json', summary)
    print('DONE', len(summary['packages']), 'packages', sum(len(x['scenes']) for x in summary['disk']), 'disk scenes')

if __name__ == '__main__': main()
