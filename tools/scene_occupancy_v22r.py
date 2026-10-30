"""Original evaluated scene meshes -> conservative convex ground footprints."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial import ConvexHull

def load_obstacles():
 root=Path(__file__).resolve().parents[1]/'public/native-scenes/CastleExterior-scene'
 manifest=json.loads((root/'manifest.json').read_text());result=[]
 for obj in manifest['objects']:
  if not any(k in obj['path'] for k in ['Tree','Stakes','Building']):continue
  mesh=manifest['meshes'][obj['mesh']];data=(root/mesh['file']).read_bytes();v=np.frombuffer(data,dtype='<f4',count=mesh['vertexCount']*3,offset=mesh['positionOffset']).reshape(-1,3)
  matrix=np.array(obj['matrix']).reshape(4,4,order='F');world=np.column_stack([v,np.ones(len(v))])@matrix.T;world[:,2]*=-1
  # Actual model section overlapping a living soldier, rather than the full
  # treetop/castle roof bounding rectangle. Convex hull conservatively closes
  # concavities; no hand-placed scenery substitutes are used.
  # Split disconnected mesh islands first. A merged FBX may contain two
  # separated towers; one hull over both would invent a solid obstacle in
  # the empty ground between them.
  _,welded=np.unique(np.round(world[:,:3],5),axis=0,return_inverse=True);parent=np.arange(int(welded.max())+1)
  def find(a):
   while parent[a]!=a:parent[a]=parent[parent[a]];a=parent[a]
   return a
  for sub in mesh['submeshes']:
   indices=np.frombuffer(data,dtype='<i4',count=sub['count'],offset=sub['offset']).reshape(-1,3)
   for tri in welded[indices]:
    a=find(int(tri[0]))
    for b in tri[1:]:parent[find(int(b))]=a
  labels=np.array([find(int(k)) for k in welded])
  for component in np.unique(labels):
   section=world[(labels==component)&(world[:,1]>=-.2)&(world[:,1]<=1.6)][:,[0,2]]
   if len(section)<3 or np.linalg.matrix_rank(section-section[0])<2:continue
   hull=ConvexHull(section);result.append(dict(path=obj['path']+'#island'+str(component),equations=hull.equations,vertices=section[hull.vertices]))
 return result

def signed_clearance(points,obstacle):
 equations=obstacle['equations'];return np.max(points@equations[:,:2].T+equations[:,2],axis=1)
