import json
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parents[1];results=[]
for name in ['CastleExterior-scene','ArenaScene-scene','NewScene','CogworkWastes']:
    d=R/'public/native-scenes'/name;m=json.loads((d/'manifest.json').read_text());meshes=[]
    for mesh in m['meshes']:
        raw=(d/mesh['file']).read_bytes();v=np.frombuffer(raw,dtype='<f4',count=mesh['vertexCount']*3,offset=mesh['positionOffset']).reshape(-1,3)
        assert np.isfinite(v).all()
        for s in mesh['submeshes']:
            ix=np.frombuffer(raw,dtype='<i4',count=s['count'],offset=s['offset']);assert ix.min()>=0 and ix.max()<len(v)
        meshes.append(v)
    errors=[]
    for o in m['objects']:
        v=meshes[o['mesh']];mat=np.array(o['matrix']).reshape(4,4,order='F');w=v@mat[:3,:3].T+mat[:3,3]
        center=(w.min(axis=0)+w.max(axis=0))/2;size=w.max(axis=0)-w.min(axis=0)
        # Unity Renderer.bounds encloses transformed local AABB, including rotated empty corners.
        lo=v.min(axis=0);hi=v.max(axis=0);corners=np.array([[x,y,z] for x in [lo[0],hi[0]] for y in [lo[1],hi[1]] for z in [lo[2],hi[2]]]);world=corners@mat[:3,:3].T+mat[:3,3]
        bc=np.array([o['boundsCenter'][x] for x in 'xyz']);bs=np.array([o['boundsSize'][x] for x in 'xyz']);expectedlo=bc-bs/2;expectedhi=bc+bs/2
        errors.append(max(np.abs(world.min(axis=0)-expectedlo).max(),np.abs(world.max(axis=0)-expectedhi).max()))
    result=dict(environment=name,source=m['source'],objects=len(m['objects']),meshes=len(meshes),materials=len(m['materials']),boundsMaxError=max(errors,default=0),finiteVertices=True,validIndices=True,warnings=m['warnings']);result['passed']=result['boundsMaxError']<1e-3 and not m['warnings'];results.append(result)
(R/'docs/v22r/native-geometry-check.json').write_text(json.dumps(results,indent=2),encoding='utf8');print(json.dumps(results,indent=2));assert all(x['passed'] for x in results)
