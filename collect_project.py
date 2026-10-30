"""Create an isolated, traceable delivery snapshot; never edit the source project."""
from pathlib import Path
import hashlib,json,shutil,subprocess,time,zipfile
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parent
SOURCE=Path('C:/Users/89trillion/PveMontageShot01V22R')
UNITY=Path('C:/Users/89trillion/PveMontageShot01V22R-PackageSceneAudit')
manifest=[];skipped=[]
def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def copy_file(src,dest):
 if not src.is_file():return
 before=src.stat();sha=digest(src);dest.parent.mkdir(parents=True,exist_ok=True)
 shutil.copy2(src,dest)
 after=src.stat()
 if before.st_size!=after.st_size or before.st_mtime_ns!=after.st_mtime_ns or sha!=digest(dest):
  raise RuntimeError('File changed during snapshot: '+str(src))
 manifest.append(dict(path=dest.relative_to(ROOT).as_posix(),source=str(src),bytes=dest.stat().st_size,sha256=sha))
def tree(src,dest,exclude=()):
 if not src.exists():return
 for path in sorted(src.rglob('*')):
  rel=path.relative_to(src)
  if path.is_file() and not any(part in {'__pycache__','node_modules','.git','Library','Temp','Logs','obj'} for part in rel.parts) and not path.name.endswith('.pyc') and not any(part in exclude for part in rel.parts):copy_file(path,dest/rel)

for folder in ['src','tools','docs','scenes','public','assets']:
 tree(SOURCE/folder,ROOT/folder,exclude=('native-scenes',) if folder=='assets' else ())
for path in SOURCE.iterdir():
 if path.is_file() and (path.suffix in {'.html','.md','.json','.js'}):copy_file(path,ROOT/path.name)
for path in (SOURCE/'baseline').iterdir():
 if path.is_file():copy_file(path,ROOT/'baseline'/path.name)

for variant in ['V22-C','V22R-C1','V22R-C2','V22R-fast-A']:
 tree(SOURCE/'variants'/variant,ROOT/'variants'/variant)
for name in ['params.json','continuation-checkpoint.pkl']:
 copy_file(SOURCE/'variants/V22R-C1-checkpoint'/name,ROOT/'variants/V22R-C1-checkpoint'/name)

# This directory is being produced in the main conversation. Copy a complete
# on-disk snapshot, exclude large resumable solver scratch, label it unapproved.
tree(SOURCE/'variants/V22R-C1-melee',ROOT/'variants/V22R-C1-melee',exclude=('progress-checkpoint.pkl',))
for folder in ['V22R-final','v22r-burst','v22r-fast-charge','v22r-approved-castle','v22r-melee']:
 src=SOURCE/'output'/folder
 if not src.exists():continue
 for path in sorted(src.rglob('*')):
  if not path.is_file():continue
  rel=path.relative_to(src)
  # Keep finished videos and small evidence, not per-frame temporary captures
  # or the explicitly failed arrow-order preview.
  if 'frames' in rel.parts or 'failed-arrow-order-preview' in rel.parts:continue
  if path.suffix.lower() in {'.mp4','.json','.csv','.md','.txt','.jpg','.png','.log'}:copy_file(path,ROOT/'output'/folder/rel)

# Prefix comparison tools require the actual approved C1 PNG sequence. Preserve
# it as an archive so the repository does not contain hundreds of loose frames.
for name,src in [('C1-approved-frames.zip',SOURCE/'output/v22r-burst/C1-preview/frames'),('C1-continued-prefix-frames.zip',SOURCE/'output/v22r-melee/prefix/frames')]:
 if src.exists():
  dest=ROOT/'reference'/name;dest.parent.mkdir(exist_ok=True)
  with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as z:
   for path in sorted(src.glob('*.png')):z.write(path,path.name)

for folder in ['Assets','Packages','ProjectSettings']:
 tree(UNITY/folder,ROOT/'unity-source'/folder)

pdf=json.loads((SOURCE/'docs/scene-requirements-r2/original-pdf-provenance.json').read_text(encoding='utf8'))['path']
copy_file(Path(pdf),ROOT/'source-materials/original-requirements.pdf')
copy_file(Path('C:/Users/89trillion/Documents/WXWork/1688855976628529/Cache/File/2026-10/PVE混剪.unitypackage'),ROOT/'source-materials/PVE混剪.unitypackage')

ref=ROOT/'reference';ref.mkdir(exist_ok=True)
status=subprocess.check_output(['git','status','--porcelain'],cwd=SOURCE).decode('utf8')
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=SOURCE).decode().strip()
patch=subprocess.check_output(['git','diff','--binary','HEAD'],cwd=SOURCE)
(ref/'working-changes-from-C1.patch').write_bytes(patch)
subprocess.run(['git','bundle','create',str(ref/'source-history.bundle'),'--all'],cwd=SOURCE,check=True)
snapshot=dict(createdUTC=datetime.now(timezone.utc).isoformat(),source=str(SOURCE),sourceHead=head,sourceBranch='v22-reference-revision',sourceWorkingTreeStatus=status,approvedBaseline='7c20b43',continuationStatus='WORKING_SNAPSHOT_NOT_VISUALLY_APPROVED',excluded=['node_modules','dist','Unity Library/Temp/Logs','loose capture frame sequences','failed-arrow-order-preview','solver progress-checkpoint.pkl'],files=manifest)
(ROOT/'SNAPSHOT-MANIFEST.json').write_text(json.dumps(snapshot,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(dict(files=len(manifest),bytes=sum(x['bytes'] for x in manifest),head=head,continuation=snapshot['continuationStatus']),indent=2))
