"""Read original attachments. Keep extracted evidence separate from interpretation."""
import hashlib,json,os,re,zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
import pymupdf
import requests

R=Path(__file__).resolve().parents[1];O=R/'docs/scene-requirements-r2';O.mkdir(exist_ok=True)
H=Path('C:/Users/89trillion')
EXT={'.docx','.doc','.pdf','.md','.txt','.xlsx','.csv','.json','.yaml','.yml','.html'}
SKIP={'node_modules','Library','Temp','.git','.venv','site-packages','ThirdParty','h-corpus','metadata','windows','chatbot-main','64504-main','leetcode_101-master','sku-recommendation (1)'}
KEY=re.compile(r'场景|战场|城堡|城墙|城门|地面|棋盘格|树木|围栏|参考图|\b3D\b|\bUnity\b|\bScene\b|\bBattlefield\b|\bCastle\b|\bEnvironment\b|\bReference\b|\bMap\b',re.I)
DOMAIN=re.compile(r'pve|pvp|混剪|真实感|守关敌万军|跨河|场景|资源|需求|分镜|制作|参考',re.I)
W={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

def save(name,obj): (O/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf8')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def walk(root):
 for directory,dirs,names in os.walk(root,followlinks=False):
  dirs[:]=[x for x in dirs if x not in SKIP and not x.startswith('.')]
  for name in names:
   p=Path(directory)/name
   if p.suffix.lower() in EXT:yield p

def extract(p):
 ext=p.suffix.lower();units=[];extra={}
 if ext=='.pdf':
  doc=pymupdf.open(p);extra={'pages':len(doc),'attachments':list(doc.embfile_names())}
  for i,page in enumerate(doc):
   units.append({'location':f'page {i+1}','text':page.get_text(),'links':list({v['uri'] for v in page.get_links() if 'uri' in v}),'images':[dict(xref=x[0],width=x[2],height=x[3]) for x in page.get_images()]})
 elif ext=='.docx':
  with zipfile.ZipFile(p) as z:
   extra['embeddedFiles']=[x for x in z.namelist() if x.startswith(('word/media/','word/embeddings/'))]
   for part in [x for x in z.namelist() if x.startswith('word/') and x.endswith('.xml') and any(k in x for k in ['document','footnote','endnote','header','footer'])]:
    root=ET.fromstring(z.read(part))
    for i,para in enumerate(root.findall('.//w:p',W)):
     text=''.join(t.text or '' for t in para.findall('.//w:t',W))
     if text:units.append(dict(location=f'{part} paragraph {i+1}',text=text))
   rel='word/_rels/document.xml.rels'
   if rel in z.namelist():extra['relationships']=ET.fromstring(z.read(rel)).attrib;extra['externalTargets']=[x.attrib.get('Target') for x in ET.fromstring(z.read(rel)) if x.attrib.get('TargetMode')=='External']
 elif ext=='.xlsx':
  import openpyxl
  wb=openpyxl.load_workbook(p,read_only=True,data_only=True)
  for sheet in wb:
   for i,row in enumerate(sheet.iter_rows(values_only=True)):
    text=' | '.join(str(x) for x in row if x is not None)
    if text and KEY.search(text):units.append(dict(location=f'sheet {sheet.title} row {i+1}',text=text))
  wb.close()
 elif ext=='.doc':return [],{'status':'Legacy binary DOC requires converter; not silently accepted'}
 else:
  raw=p.read_bytes()
  for encoding in ['utf-8-sig','utf-16','gb18030']:
   try:text=raw.decode(encoding);break
   except UnicodeError:continue
  else:text=raw.decode('utf8','replace')
  units=[dict(location=f'line {i+1}',text=l) for i,l in enumerate(text.splitlines()) if KEY.search(l)]
 hits=[u for u in units if KEY.search(u['text'])]
 return hits,extra

def main():
 roots=[H/'Downloads',H/'Documents/WXWork',H/'Desktop',H/'My project/Assets',R/'assets/imported']
 files=[];records=[]
 for root in roots:
  for p in walk(root):
   # WFL is an original game source, indexed separately by GUID and scenes.
   if 'Desktop/WFL/' in p.as_posix():continue
   record=dict(path=str(p),bytes=p.stat().st_size,extension=p.suffix.lower());files.append(record)
   if p.stat().st_size>35_000_000 and p.suffix.lower()!='.docx':record['status']='SKIPPED_SIZE_BOUND';continue
   # Large unrelated model/research tables do not establish project requirements.
   if not DOMAIN.search(p.name) and p.stat().st_size>3_000_000 and p.suffix.lower()!='.docx':record['status']='SKIPPED_LARGE_UNRELATED_NAME';continue
   try:
    hits,extra=extract(p);record['status']='READ';record['hitUnits']=len(hits)
    if hits:
     relevant=bool(DOMAIN.search(p.name)) or (p.suffix.lower()=='.docx' and any(re.search(r'混剪|阵型|蓝方|红方|城墙|城堡',h['text']) for h in hits))
     if relevant:
      records.append(dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size,relevanceByName=bool(DOMAIN.search(p.name)),hits=hits,extra=extra))
   except Exception as e:record.update(status='ERROR',error=str(e)[:250])
 save('original-document-search.json',dict(roots=[str(p) for p in roots],skippedDirectories=sorted(SKIP),files=files,matchedDocuments=records))
 pdf=H/'Downloads/pve pvp真实感混剪.pdf';d=pymupdf.open(pdf)
 for i in [6,7,12,13,14,15]:
  (O/f'original-pdf-page{i+1:02}.txt').write_text(d[i].get_text(),encoding='utf8')
  if i in [6,13]:d[i].get_pixmap(matrix=pymupdf.Matrix(1.5,1.5)).save(O/f'original-pdf-page{i+1:02}.png')
 save('original-pdf-provenance.json',dict(path=str(pdf),bytes=pdf.stat().st_size,sha256=sha(pdf),metadata=d.metadata,pages=len(d),pagesEvidence=[dict(page=i+1,links=list({x['uri'] for x in d[i].get_links() if 'uri' in x}),images=[dict(xref=x[0],width=x[2],height=x[3]) for x in d[i].get_images()]) for i in range(len(d))]))
 scene='18LIFiPBiOMRrSB1jDWQ4YgHVNy7uKwo';url='https://drive.89trillion.com:5001/webapi/entry.cgi'
 try:
  response=requests.get(url,params=dict(api='SYNO.SynologyDrive.Shard',version=1,method='getjs',permanent_link=json.dumps(scene)),timeout=15)
  (O/'drive-link-metadata.js').write_text(response.text,encoding='utf8')
  save('drive-link-fetch.json',dict(url=response.url,status=response.status_code,bytes=len(response.content),contentType=response.headers.get('content-type')))
  print('DRIVE',response.status_code,response.text[:2200])
 except Exception as e:save('drive-link-fetch.json',dict(error=str(e)))
 print(json.dumps(dict(scanned=len(files),matched=len(records),relevant=[dict(path=x['path'],hits=len(x['hits'])) for x in records if x['relevanceByName']],failures=[x for x in files if x['status']=='ERROR']),ensure_ascii=False))

if __name__=='__main__':main()
