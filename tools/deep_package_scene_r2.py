"""Read the user-designated archive, including nested archives, without changing sources."""
import collections,hashlib,io,json,re,tarfile
from pathlib import Path

R=Path(__file__).resolve().parents[1]
OUT=R/'docs/scene-requirements-r2'
PACKAGE=Path('C:/Users/89trillion/Documents/WXWork/1688855976628529/Cache/File/2026-10/PVE混剪.unitypackage')
TARGET=Path('C:/Users/89trillion/PveMontageShot01V22R-PackageSceneAudit')
GUID=re.compile(r'guid: ([a-f0-9]{32})')

def scan(handle,label,depth=0):
 records={};duplicates=[]
 with tarfile.open(fileobj=handle,mode='r:gz') as tar:
  for m in tar:
   guid,_,kind=m.name.partition('/')
   if kind not in {'pathname','asset','asset.meta'}:continue
   r=records.setdefault(guid,{})
   if kind in r:duplicates.append(m.name)
   r[kind]=tar.extractfile(m).read()
 entries=[];nested=[];copied=[];references={};sceneSummaries=[]
 index={g:r['pathname'].decode('utf8','replace').strip() for g,r in records.items() if 'pathname' in r}
 for g,r in records.items():
  if g not in index:continue
  path=index[g];ext=Path(path).suffix.lower();raw=r.get('asset',b'')
  e=dict(guid=g,path=path,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
  entries.append(e)
  if ext=='.unitypackage' and depth<3:
   nested.append(scan(io.BytesIO(raw),label+'!'+path,depth+1))
  if ext in {'.unity','.prefab','.mat','.asset'}:
   txt=raw.decode('utf8','replace');refs=set(GUID.findall(txt))
   refs.update(GUID.findall(r.get('asset.meta',b'').decode('utf8','replace')))
   references[path]={guid:index.get(guid) for guid in sorted(refs)}
   if ext in {'.unity','.prefab'}:
    sceneSummaries.append(dict(path=path,types=dict(collections.Counter(re.findall(r'^--- !u!(\d+)',txt,re.M))),names=re.findall(r'^  m_Name: (.*)$',txt,re.M),disabledGameObjects=len(re.findall(r'^  m_IsActive: 0$',txt,re.M)),disabledRenderers=len(re.findall(r'^  m_Enabled: 0$',txt,re.M))))
  if depth==0 and ext in {'.unity','.prefab','.mat','.fbx','.png','.jpg','.jpeg','.tga','.shader','.shadergraph','.shadersubgraph','.asset','.controller','.anim','.mask'} and raw:
   relative=Path(path)
   if relative.is_absolute() or '..' in relative.parts:raise ValueError(path)
   dst=TARGET/relative;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(raw)
   if 'asset.meta' in r:Path(str(dst)+'.meta').write_bytes(r['asset.meta'])
   copied.append(dict(path=path,sha256=e['sha256'],matches=hashlib.sha256(dst.read_bytes()).hexdigest()==e['sha256']))
 return dict(source=label,entries=entries,types=dict(collections.Counter(Path(e['path']).suffix.lower() for e in entries)),duplicates=duplicates,nested=nested,references=references,sceneSummaries=sceneSummaries,copied=copied)

def main():
 with PACKAGE.open('rb') as f:result=scan(f,str(PACKAGE))
 h=hashlib.sha256()
 with PACKAGE.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 result['sha256']=h.hexdigest();result['isolatedProject']=str(TARGET)
 (TARGET/'Packages').mkdir(exist_ok=True);(TARGET/'Packages/manifest.json').write_text('{"dependencies":{}}')
 (TARGET/'ProjectSettings').mkdir(exist_ok=True);(TARGET/'ProjectSettings/ProjectVersion.txt').write_text('m_EditorVersion: 6000.0.54f1\n')
 (OUT/'designated-package-deep-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
 print(json.dumps(dict(entries=len(result['entries']),copied=len(result['copied']),sha256=result['sha256'],types=result['types'],nested=[dict(source=x['source'],types=x['types']) for x in result['nested']],duplicates=result['duplicates']),ensure_ascii=False))

if __name__=='__main__':main()
