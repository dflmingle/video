"""Restore the approved frame references and compressed renderer logs."""
from pathlib import Path
import gzip,shutil,zipfile
root=Path(__file__).resolve().parent
for name,directory in [('C1-approved-frames.zip','output/v22r-burst/C1-preview/frames'),('C1-continued-prefix-frames.zip','output/v22r-melee/prefix/frames')]:
 archive=root/'reference'/name
 if archive.exists():
  dest=root/directory;dest.mkdir(parents=True,exist_ok=True)
  with zipfile.ZipFile(archive) as z:z.extractall(dest)
for path in (root/'output').rglob('*.json.gz'):
 with gzip.open(path,'rb') as src,path.with_suffix('').open('wb') as dst:shutil.copyfileobj(src,dst)
print('Evidence references restored.')
