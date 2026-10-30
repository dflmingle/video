"""A: overlap blue preparation only. B: reject invalid backshift before simulation."""
import hashlib,json,shutil
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
R=Path(__file__).resolve().parents[1];D=R/'docs/v22r-fast-charge';D.mkdir(exist_ok=True);V=R/'variants/V22R-fast-A';V.mkdir(exist_ok=True)
src=R/'variants/V22R-overlap';c=json.loads((src/'params.json').read_text());c.update(duration=3.5,parallelAssemblyFire=True)
assert not c.get('safeFrontEngagement') and 'redArmyTranslations' not in c
(V/'params.json').write_text(json.dumps(c,indent=2),encoding='utf8');(D/'A-requested-params.json').write_text(json.dumps(c,indent=2),encoding='utf8')
if (src/'asset-render-audit.json').exists():shutil.copyfile(src/'asset-render-audit.json',V/'asset-render-audit.json')
s=json.loads((src/'simulation.json').read_text(encoding='utf8'));nb=s['blueCount'];red=np.array([u['start'] for u in s['units'][nb:]]);blue=np.array([u['start'] for u in s['units'][:nb]])
wall=-29.7378;radius=c['bodyRadius'];required=2*c['weaponEnvelopeRadius']+c['minimumEnemyClearance'];minimumShift=wall+radius-float(red[:,1].min())
dx=red[:,None,0]-blue[None,:,0];valid=np.abs(dx)<required
longitudinal=blue[None,:,1]-red[:,None,1]-np.sqrt(np.maximum(0.,required**2-dx**2))
maximumShift=float(np.min(longitudinal[valid]))
backshift=8.;proposed=red-[0,backshift]
report=dict(baseline='V22R-overlap / V22 unchanged red core',A=dict(variant='V22R-fast-A',changes={'duration':[2.2,3.5],'parallelAssemblyFire':[False,True]},redMotionController='tools/motion_v22.py unchanged',blueAdvance=c['blueAdvance'],range=c['archerRange'],arrowSpeed=c['arrowSpeed'],attackParametersUnchanged=True,description='Blue starts independent preparation while existing assembly continues; range/facing/draw/recovery checks retained. No safety-front controller, translations or blue speed-reference override.'),B=dict(status='REJECTED_BEFORE_SIMULATION',requestedMethod='Rigid backward translation of entire existing red army, blue U and camera unchanged',testedBackwardDistance=backshift,originalRedBehindWall=int(np.sum(red[:,1]<wall)),proposedRedBehindWall=int(np.sum(proposed[:,1]<wall)),redZBounds=[float(red[:,1].min()),float(red[:,1].max())],proposedZBounds=[float(proposed[:,1].min()),float(proposed[:,1].max())],wallFrontZ=wall,minimumForwardTranslationForAllRedInFront=minimumShift,maximumForwardTranslationBeforeInitialEnemyClearanceViolation=maximumShift,allowedForwardTranslationIntervalEmpty=minimumShift>maximumShift,why='Existing full red column already starts behind the wall. A backward-only shift cannot satisfy same-side constraint. Even forward-only translation has incompatible wall/front-army safety bounds at original X positions.',videoGenerated=False,noUnapprovedRearrangement=True),sourceHashes={name:hashlib.sha256((R/name).read_bytes()).hexdigest() for name in ['src/castle-approved-v22r.js','src/environment-native-v22.js','public/native-scenes/CastleExterior-scene/manifest.json','tools/motion_v22.py','tools/motion_v17.py']})
(D/'proposal-and-B-geometry.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(report,ensure_ascii=True,indent=2))
