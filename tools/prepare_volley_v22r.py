"""One bounded layout experiment: whole-army translations, unchanged scenery."""
import hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];O=R/'docs/v22r-volley';O.mkdir(exist_ok=True)
s=json.loads((R/'baseline/V5-simulation.json').read_text(encoding='utf8'))
c=json.loads((R/'variants/V22R-overlap/params.json').read_text(encoding='utf8'))
offsets={}
for color,x,front in [('red',0.,-11.4),('orange',9.,11.1),('yellow',-12.5,6.9)]:
 us=[u for u in s['units'] if u.get('color')==color]
 offsets[color]=[x,front-max(u['start'][1] for u in us)]
c.update(duration=4.,redArmyTranslations=offsets,blueArmyTranslation=[0.,4.3],blueAdvance=3.,blueWalkSpeedReferenceDistance=7.5,parallelAssemblyFire=True,safeFrontEngagement=True,safeFrontMargin=1.5,safeFrontBrake=42*c.get('chargeMultiplier',1.),autoCut=True)
variant=R/'variants/V22R-volley';variant.mkdir(exist_ok=True)
(variant/'params.json').write_text(json.dumps(c,indent=2),encoding='utf8')
for name in ['asset-render-audit.json']:
 source=R/'variants/V22-C'/name
 if source.exists():(variant/name).write_bytes(source.read_bytes())
proposal=dict(baseline='b595e1a / V22 battle core',requestedDurationCandidates=[3.,3.5,4.],redTranslations=offsets,blueTranslation=c['blueArmyTranslation'],preserve=['Scene, materials, geometry, lighting, fixed camera','Each army and squad internal start offsets','Red preferred world speeds, original wounds/deaths','Blue assembly path length and personal speed','Original per-shooter aim/draw/recover intervals, range and arrow speed'],changes=['Each colored army translates as a rigid formation; orange and red share the rear band, yellow leads.','Blue U translates as one formation; all its defense targets receive exactly the same offset.','Per-red-unit stopping-distance bound against actual future defensive occupation, followed by coupled local contact projection before the sole integral.','Blue locomotion uses independent deployment progress while attack uses individual seeded state and true range. Native sampled walk lower body blends with native attack upper body in renderer.'],noFinalRenderBeforeUserApproval=True,sourceHashes={p:hashlib.sha256((R/p).read_bytes()).hexdigest() for p in ['src/castle-approved-v22r.js','src/environment-native-v22.js','public/native-scenes/CastleExterior-scene/manifest.json']})
proposal['preserve'][3]='Blue original per-member world walking speed; assembly goal distance explicitly revised'
proposal['changes'][0]='Each colored army translates intact into available ground on the camera side of the wall; internal 3x3 squads remain unchanged.'
proposal['changes'][1]='Blue U translates intact; assembly goals advance 3 units while original per-ID walking speeds are preserved.'
proposal['blueAssemblyTargetAdjustment']=dict(previousDistance=7.5,candidateDistance=3.,worldWalkingSpeedUnchanged=True,reason='Keep the entire U in the frozen view, reserve safe firing space, avoid original scenery. No idle time added.')
(O/'proposal.json').write_text(json.dumps(proposal,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(dict(redTranslations=offsets,blueTranslation=c['blueArmyTranslation'],variant=str(variant)),ensure_ascii=True))
