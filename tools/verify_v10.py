from pathlib import Path
import json,hashlib,cv2,numpy as np
P=Path(__file__).resolve().parents[1];D=P/'variants/FINAL';O=P/'output';h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for version in ['v6','v7','v8']:
 for path,digest in json.loads((P/f'baseline/protected-{version}.json').read_text()).items():assert h(Path(path))==digest,('Changed baseline',path)
c=json.loads((D/'params.json').read_text());N=round(c['duration']*c['fps']);captures={}
for name in ['render-checks.json','motion-render-checks.json']:
 r=json.loads((D/name).read_text());assert not r['errors'] and all(s['identical'] for s in r['seeks']);assert len(r['states'])==N
 for p,digest in r['inputs'].items():assert h(P/p)==digest,('Stale capture',p)
 for field in ['cameraPosition','cameraQuaternion','cameraProjection','cameraZoom']:assert all(s[field]==r['states'][0][field] for s in r['states']),('Camera changed',field)
 captures[name]={'frames':N,'fixedPositionOrientationLens':True,'deterministicSeeks':r['seeks']}
main=json.loads((O/'final-media-validation.json').read_text());assert main['frames']==N and main['sha256']==h(O/main['path']);media=[]
for p in O.glob('*.mp4'):
 cap=cv2.VideoCapture(str(p));n=0;black=0;repeat=0;prev=None
 while True:
  ok,im=cap.read()
  if not ok:break
  digest=hashlib.sha256(im.tobytes()).hexdigest();black+=int(im.mean()<1);repeat+=int(digest==prev);prev=digest;n+=1
 rate=cap.get(5);cap.release();assert n>0 and black==0
 media.append(dict(path=p.name,frames=n,fps=rate,sha256=h(p),blackFrames=black,adjacentRepeats=repeat))
for m in json.loads((O/'evidence-media.json').read_text()):assert h(O/m['path'])==m['sha256']
a=json.loads((D/'audit.json').read_text());assert all(x['continuousSurfaceLowerBound']>=c['minimumEnemyClearance'] for x in a['safety'].values())
x=json.loads((O/'member-motion-validation.json').read_text());assert x['initialMembersExactlyEqualV5'] and x['bodyOverlapSamples']==0 and x['trackedCount']>=12
manifest=json.loads((P/'assets/runtime/manifest.json').read_text())
for k,m in manifest.items():assert h(P/f'assets/runtime/{k}.fbx')==m['sourceSHA256'] and h(P/f'assets/runtime/{k}.png')==m['textureSHA256']
r=dict(engineeringStatus='PASS',visualAcceptance='Separate review; not inferred from metrics',captures=captures,media=media,inputs={str(p.relative_to(P)):h(p) for p in [*P.glob('src/*-v10.js'),*P.glob('tools/*v10*'),*D.glob('*.f32'),D/'simulation.json',D/'params.json'] if p.is_file()})
(O/'delivery-manifest.json').write_text(json.dumps(r,indent=2));print('V10 encoded media, fixed continuous camera, current captures, assets, 12 members and protected V6/V7/V8: PASS')
