from pathlib import Path
p=Path('tools/build_simulation_v17.py');s=p.read_text(encoding='utf8');
s=s.replace('from archers_v17 import Archers','from archers_v18 import Archers')
s=s.replace('blueControls=np.zeros((N,nb,4),np.float32)','blueControls=np.zeros((N,nb,8),np.float32)')
s=s.replace("dict(version='V17'", "dict(version='V18'")
s=s.replace("'controlColumns=['targetSpeed','forwardSpeed','acceleration','stride','cadenceCyclesPerSecond','posture','armSwing','turn','effort','reason']", "'controlColumns':['state','timer','target','lastRelease','walkPhase','turnPhase','actionPhase','moveSpeed']")
Path('tools/build_simulation_v18.py').write_text(s,encoding='utf8')
