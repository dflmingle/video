"""Resolve package dependencies, inspect embedded packages, hash scene sources."""
import collections, hashlib, io, json, re, tarfile
from pathlib import Path
from audit_resources_v22r import ROOT, OUT, save

def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def read_index(archive):
    records={}
    with tarfile.open(fileobj=archive, mode='r:gz') as tar:
        for m in tar:
            guid,_,kind=m.name.partition('/')
            r=records.setdefault(guid,{})
            if kind=='pathname': r['path']=tar.extractfile(m).read().decode('utf8','replace').strip()
            elif kind=='asset': r['bytes']=m.size
    return [dict(guid=k,**v) for k,v in records.items() if 'path' in v]

def main():
    p=json.loads((OUT/'package-03.json').read_text(encoding='utf8'))
    entries={e['guid']:e for e in p['entries']}
    dependencies={}; embedded=[]; verified=[]
    source=ROOT/'assets/imported'
    with tarfile.open(p['path'],'r|gz') as tar:
        for m in tar:
            guid,_,kind=m.name.partition('/')
            if kind!='asset' or guid not in entries: continue
            e=entries[guid]; path=e['path']; suffix=Path(path).suffix.lower()
            needed=suffix in {'.unity','.prefab','.mat','.unitypackage','.shader'} or 'Environment/' in path
            if not needed: continue
            raw=tar.extractfile(m).read()
            if suffix in {'.unity','.prefab','.mat'}:
                text=raw.decode('utf8','replace')
                refs=set(re.findall(r'guid: ([a-f0-9]{32})',text))
                dependencies[path]={'names':re.findall(r'^  m_Name: (.+)$',text,re.M)[:80], 'refs':{g:entries.get(g,{}).get('path') for g in refs}}
            if suffix=='.unitypackage':
                embedded.append({'path':path,'sha256':hashlib.sha256(raw).hexdigest(),'entries':read_index(io.BytesIO(raw))})
            local=source/path
            if local.is_file():
                actual=digest(local); expected=hashlib.sha256(raw).hexdigest()
                verified.append({'path':path,'local':str(local),'sha256':actual,'matchesOriginalPackage':actual==expected})
    scenes=[]
    for e in p['scenes']:
        seen=set(); unresolved=set(); queue=[e['path']]
        while queue:
            path=queue.pop()
            if path in seen:continue
            seen.add(path)
            for g, ref in dependencies.get(path,{}).get('refs',{}).items():
                if ref:queue.append(ref)
                else:unresolved.add(g)
        scenes.append({'scene':e['path'],'dependencies':sorted(seen),'types':dict(collections.Counter(Path(x).suffix.lower() for x in seen)), 'unresolvedGuids':sorted(unresolved)})
    save('package-dependencies.json',{'package':p['path'],'sha256':digest(Path(p['path'])),'sceneDependencies':scenes,'authoredReferences':dependencies,'verifiedOriginals':verified,'embeddedPackages':embedded})
    print(json.dumps({'scenes':[(x['scene'],x['types']) for x in scenes], 'verified':len(verified),'hashMismatches':sum(not x['matchesOriginalPackage'] for x in verified),'nestedPackages':len(embedded),'nestedScenes':[e['path'] for x in embedded for e in x['entries'] if e['path'].endswith('.unity')]},ensure_ascii=False))

if __name__=='__main__':main()
