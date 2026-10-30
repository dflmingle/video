from pathlib import Path
import json
P=Path(__file__).resolve().parents[1];p=P/'tools/build_simulation_v16.py';s=p.read_text(encoding='utf-8')
s=s.replace("u['moveSeconds']=C['blueMoveSeconds']*(.88+.025*row+.080*r)","""# Wings deploy first, inner U completes a longer deployment. Each member
 # still walks its actual full path; no teleport or common arrival barrier.
 early=u['group'] in [0,6]
 u['moveSeconds']=(1.00 if early else 1.65)+.047*row+.035*r
""")
s=s.replace("u['drawSeconds']=.25+.10*q;u['aimSeconds']=.055+.045*r","u['drawSeconds']=.21+.075*q;u['aimSeconds']=.045+.035*r")
# Projectile time from moving-target intercept, not frozen target distance.
# Solve |relative + targetVelocity*tau| = projectileSpeed*tau. Endpoint is still
# bound to the actual target root when resolved; no fabricated off-screen damage.
s=s.replace("flight=float(max(.35,dist/C['arrowSpeed']));hf=f+round(flight/dt)","""relative=rp[target]-p;targetVelocity=motion.velocity[target]
   qa=float(np.dot(targetVelocity,targetVelocity)-C['arrowSpeed']**2);qb=2*float(np.dot(relative,targetVelocity));qc=float(np.dot(relative,relative))
   disc=max(0.,qb*qb-4*qa*qc);roots=[(-qb+math.sqrt(disc))/(2*qa),(-qb-math.sqrt(disc))/(2*qa)]
   flight=float(max(.18,min(tau for tau in roots if tau>0)));hf=f+round(flight/dt)""")
p.write_text(s,encoding='utf-8')
for name in ['BASE100','FAST125','FAST150']:
 p=P/f'variants/{name}/params.json';c=json.loads(p.read_text());c['duration']=6.;c['archerCycle']=.70;p.write_text(json.dumps(c,indent=2))
print('Archery revision: staggered arrivals, actual intercept flight time')
