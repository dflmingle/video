"""Record the actual tracked delivery payload without changing its sources."""
from pathlib import Path
import subprocess,json,hashlib
from datetime import datetime,timezone
root=Path(__file__).resolve().parent
paths=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode('utf8').split('\0')
files=[]
for name in sorted(x for x in paths if x and x!='DELIVERY-MANIFEST.json'):
 p=root/name
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 files.append(dict(path=name,bytes=p.stat().st_size,sha256=h.hexdigest()))
data=dict(createdUTC=datetime.now(timezone.utc).isoformat(),sourceHead='7c20b43a44f9c9dc6b8c2653646103e45fb72bbd',approvedBaseline='C1 0–2.65s',continuationStatus='WORKING_SNAPSHOT_NOT_VISUALLY_APPROVED',gitLFS=['source-materials/*.unitypackage','reference/*.zip'],normalGitFiles='Other files are stored directly in Git; hashes refer to checked-out content after git lfs pull.',checked=dict(build='PASS',copiedC1BrowserRuntime='PASS',continuationDataAudit='PASS',continuationVisualApproval='PENDING'),sourceChanges='reference/working-changes-from-C1.patch plus newly added tools and documentation; original history in reference/source-history.bundle',fileCount=len(files),totalCheckedOutBytes=sum(x['bytes'] for x in files),files=files)
(root/'DELIVERY-MANIFEST.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in data.items() if k!='files'},ensure_ascii=False,indent=2))
