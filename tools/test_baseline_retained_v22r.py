"""The optional prolonged-front behavior must not change V22 baseline dynamics."""
import copy,importlib.util,json,subprocess,tempfile,sys
from pathlib import Path
import numpy as np

R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'tools'))
def source_module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
before=subprocess.check_output(['git','show','b595e1a:tools/motion_v17.py'],cwd=R).decode('utf8')
s=json.loads((R/'baseline/V5-simulation.json').read_text());c=json.loads((R/'variants/V22-C/params.json').read_text());units=s['units'][s['blueCount']:s['blueCount']+72]
with tempfile.TemporaryDirectory(prefix='v22r-regression-') as tmp:
 path=Path(tmp)/'baseline_motion.py';path.write_text(before,encoding='utf8');old=source_module('baseline_motion',path).Crowd(copy.deepcopy(units),c);now=source_module('present_motion',R/'tools/motion_v17.py').Crowd(copy.deepcopy(units),c)
 for f in range(1,31):
  old.step(f/60);now.step(f/60);assert np.array_equal(old.position,now.position) and np.array_equal(old.velocity,now.velocity)
report=dict(status='PASS',baseline='b595e1a',members=72,steps=30,positionsBitIdentical=True,velocitiesBitIdentical=True,scope='Original red core when safeFrontEngagement is absent; blue baseline regression is independently tested.')
out=R/'docs/v22r-volley';out.mkdir(exist_ok=True);(out/'baseline-red-regression.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
