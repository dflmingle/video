"""Measure fixed-camera translation limits using actual native vertices."""
from pathlib import Path
import json,numpy as np
P=Path(__file__).resolve().parents[1]
root=P/'public/native-scenes/CastleExterior-scene';M=json.loads((root/'manifest.json').read_text())
normal=np.array(json.loads((P/'docs/v22r-distance/setup.json').read_text())['candidates'][0]['normal'])
forward=np.array([0.,-98.,-60.]);forward/=np.linalg.norm(forward);up=np.cross([1.,0.,0.],forward)
def project(x):
 r=x-[0.,98.,65.];z=r@forward;t=np.tan(np.deg2rad(21))
 return np.column_stack([360+360*r[:,0]/(z*t*2/3),540-540*(r@up)/(z*t)])
def vertices(o):
 m=M['meshes'][o['mesh']];b=(root/m['file']).read_bytes();v=np.frombuffer(b,dtype='<f4',count=m['vertexCount']*3,offset=m['positionOffset']).reshape(-1,3)
 w=np.column_stack([v,np.ones(len(v))])@np.array(o['matrix']).reshape(4,4,order='F').T;w[:,2]*=-1;return w[:,:3]
if __name__=='__main__':
 for o in M['objects']:
  if 'Building' not in o['path']:continue
  v=vertices(o)
  for shift in [0,3,5,7,10,15]:
   w=v.copy();w[:,[0,2]]-=normal*shift;pix=project(w);print(o['path'].split('/')[-1],shift,'y',pix[:,1].min(),pix[:,1].max(),'visible',np.mean((pix[:,0]>=0)&(pix[:,0]<=720)&(pix[:,1]>=0)&(pix[:,1]<=1080)))
