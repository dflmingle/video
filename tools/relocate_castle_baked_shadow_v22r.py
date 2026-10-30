"""Candidate-only relocation of the castle's authored shadow in ground albedo.

Keep original native texture immutable. Isolate its connected castle shadow,
repair the underlying terrain in a derived copy, and transplant its sampled
multiplicative shadow ratio using the measured ground UV/world affine map.
"""
from pathlib import Path
import json,hashlib,cv2,numpy as np
from scipy import sparse
from scipy.sparse.linalg import factorized
from PIL import Image
P=Path(__file__).resolve().parents[1];D=P/'docs/v22r-topfield';O=P/'output/v22r-topfield'
source=P/'assets/imported/Assets/ArtOfWar-II_Art/Environment/Common/CastleExterior/Texture/CastleExterior_Land_C.png'
im=np.array(Image.open(source).convert('RGB'));h,w=im.shape[:2]
yy,xx=np.mgrid[:h,:w]
# The authored castle shadow is the dark connected pair of tower silhouettes
# joined by the thin wall shadow, in this original texture's UV atlas region.
roi=(xx>220)&(xx<415)&(yy>320)&(yy<950)
mask=(roi&(im[:,:,0]<215)&(im[:,:,1]<150)&(im[:,:,2]<90)).astype(np.uint8)
num,labels,stats,_=cv2.connectedComponentsWithStats(mask)
keep=[i for i in range(1,num) if stats[i,cv2.CC_STAT_AREA]>150]
mask=np.isin(labels,keep).astype(np.uint8)*255
repairMask=cv2.dilate(mask,np.ones((3,3),np.uint8))
soft=cv2.GaussianBlur((repairMask/255.).astype(np.float32),(0,0),1.0)
# The original has no unshadowed layer. Restore only the small shadow atlas
# strip by harmonic interpolation from its actual unshadowed boundary. A
# rectangular domain avoids retaining an inverse tower-shaped outline.
x0,x1,y0,y1=210,440,325,960;nw=x1-x0-1;nh=y1-y0-1
tx=sparse.diags([-np.ones(nw-1),2*np.ones(nw),-np.ones(nw-1)],[-1,0,1],format='csc')
ty=sparse.diags([-np.ones(nh-1),2*np.ones(nh),-np.ones(nh-1)],[-1,0,1],format='csc')
laplace=sparse.kronsum(tx,ty,format='csc');solve=factorized(laplace)
rhs=np.zeros((nh,nw,3));rhs[0]+=im[y0,x0+1:x1];rhs[-1]+=im[y1,x0+1:x1];rhs[:,0]+=im[y0+1:y1,x0];rhs[:,-1]+=im[y0+1:y1,x1]
clean=im.copy();clean[y0+1:y1,x0+1:x1]=np.clip(np.round(np.column_stack([solve(rhs[:,:,i].ravel()) for i in range(3)]).reshape(nh,nw,3)),0,255).astype(np.uint8)
ratio=1-soft[:,:,None]*(1-np.minimum(1.,(im.astype(np.float32)+1)/(clean.astype(np.float32)+1)))
setup=json.loads((D/'setup.json').read_text());c=setup['candidates'][0];delta=np.array(c['sceneLayout']['previewTranslation'])[[0,2]]
uvMatrix=np.array([[0.,.00539998556],[.00539998518,0.]])
uvDelta=delta@uvMatrix;pixelDelta=np.array([uvDelta[0]*w,-uvDelta[1]*h])
affine=np.array([[1.,0.,pixelDelta[0]],[0.,1.,pixelDelta[1]]],np.float32)
shifted=cv2.warpAffine(ratio,affine,(w,h),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT,borderValue=(1.,1.,1.))
final=np.clip(np.round(clean.astype(np.float32)*shifted),0,255).astype(np.uint8)
def centroid(a):
 total=a.sum();return [float((a*xx).sum()/total),float((a*yy).sum()/total)]
beforeAlpha=1-ratio.mean(2);afterAlpha=1-shifted.mean(2)
centroidDelta=np.array(centroid(afterAlpha))-centroid(beforeAlpha)
assert np.max(np.abs(centroidDelta-pixelDelta))<.04
public=P/'public/native-scenes/layout-derived/topfield';public.mkdir(parents=True,exist_ok=True)
dest=public/'CastleExterior_Land_C-shadow-moved.png';Image.fromarray(final).save(dest)
for name,array in [('castle-shadow-mask.png',repairMask),('land-shadow-removed.png',clean),('land-shadow-relocated.png',final)]:Image.fromarray(array).save(O/name)
report=dict(originalPath=str(source),originalSHA256=hashlib.sha256(source.read_bytes()).hexdigest(),derivedPath=str(dest),derivedSHA256=hashlib.sha256(dest.read_bytes()).hexdigest(),method='Original baked castle shadow connected components; harmonic terrain repair from original unshadowed boundary; relocate shadow ratio through native ground UV affine map',terrainRepairUVPixelBounds=[x0,y0,x1,y1],originalUnchanged=True,worldTranslation=c['sceneLayout']['previewTranslation'],uvTranslation=uvDelta.tolist(),pixelTranslation=pixelDelta.tolist(),shadowMaskPixels=int((repairMask>0).sum()),components=keep,limitation='Original texture has no unshadowed layer. Ground directly beneath the old baked castle shadow is locally approximated by harmonic interpolation; other source texture regions remain unchanged.')
report.update(measuredShadowCentroidPixelTranslation=centroidDelta.tolist(),maximumTranslationPixelError=float(np.max(np.abs(centroidDelta-pixelDelta))),shadowOpacityMassRatio=float(afterAlpha.sum()/beforeAlpha.sum()))
(D/'shadow-relocation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report,indent=2))
