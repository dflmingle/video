from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json
R=Path(__file__).resolve().parents[1];O=R/'docs/scene-requirements-r2';P=R/'output/scene-requirements-r2'
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',17);small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',14)
def paste(canvas,filename,box):
 im=Image.open(filename).convert('RGB');im.thumbnail((box[2]-box[0],box[3]-box[1]));canvas.paste(im,(box[0]+(box[2]-box[0]-im.width)//2,box[1]))
im=Image.new('RGB',(1100,950),'#202529');draw=ImageDraw.Draw(im)
draw.text((12,10),'A 原需求 PDF 第14页完整图片',(255,255,255),font)
draw.text((430,10),'B 指定包 CastleExterior 原生场景',(255,255,255),font)
paste(im,O/'document-scene-reference.png',(10,42,405,937));paste(im,P/'exact-package-CastleExterior-inspection.png',(430,42,1090,778))
for i,line in enumerate(['参考图原相机未知；B 为场景检查视角，未声称视角完全相同。','差异：树冠 / 木栏横杆 / 骷髅牌 / 右侧城门轮廓。','B 保留原场景物体布局，仅做坐标手性转换。','真实 3D 资产已定位；与参考图完全一致尚未确认。']):draw.text((430,800+i*29),line,(240,230,206),small)
im.save(O/'PACKAGE-VS-DOCUMENT.jpg',quality=89)

im=Image.new('RGB',(1240,1050),'#202529');draw=ImageDraw.Draw(im)
labels=[('first','0.000s 开场'),('assembly','1.650s 蓝方集结中'),('release','2.417s 首次真实放箭'),('hit','2.733s 首次真实命中')]
for idx,(key,label) in enumerate(labels):
 x=(idx%2)*620;y=(idx//2)*510
 draw.text((x+10,y+8),label,(255,255,255),font)
 for j,env in enumerate(['NewScene','CastleExterior']):
  xx=x+10+j*302;draw.text((xx,y+37),'A 当前 NewScene' if j==0 else 'B 包内 CastleExterior',(240,230,206),small)
  paste(im,P/f'exact-package-{env}-V22-fixed-{key}.png',(xx,y+62,xx+295,y+505))
draw.text((10,1025),'全部使用同一固定开场机位、同一 V22 轨迹；场景原坐标不调整；本图不是固定近景验收通过。',(255,255,255),small)
im.save(O/'V22-FIXED-SCENE-FOUR-TIMES.jpg',quality=89)

im=Image.new('RGB',(1320,325),'#202529');draw=ImageDraw.Draw(im)
for i,(name,label) in enumerate([('Building','建筑：两块子网格'),('Tree_04','Tree_04：块状树形'),('Tree_05','Tree_05：块状树形'),('Stakes_01','Stakes_01：木桩'),('Stakes_02','Stakes_02：木桩')]):
 x=i*264;draw.text((x+5,8),label,(255,255,255),small);paste(im,P/f'exact-package-CastleExterior_{name}-asset.png',(x+4,35,x+260,291))
draw.text((5,301),'模型单独检查，各自适配观察机位；没有将散件拼装成新的正式场景。',(240,230,206),small)
im.save(O/'PACKAGE-ACTUAL-MODELS.jpg',quality=89)

checks=json.loads((P/'exact-package-fixed-browser-checks.json').read_text())
frames={(env,key):json.loads((P/f'exact-package-{env}-V22-fixed-{key}.json').read_text()) for env in ['NewScene','CastleExterior'] for key,_ in labels}
checks['sameSoldierWorldRowsAtEachTime']=all(frames[('NewScene',key)]['rows']==frames[('CastleExterior',key)]['rows'] for key,_ in labels)
checks['cameraSamples']=len(frames)
checks['cameraMode']='Candidate-only freeze of V22 B opening parameters. Original V22 camera is animated and is not claimed fixed.'
(O/'STATIC-COMPARISON-CHECKS.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf8')
assert checks['sameCamera'] and checks['noPageErrors'] and checks['sameSoldierWorldRowsAtEachTime']
print('Three review panels generated; same world rows and fixed camera confirmed in 8 static captures.')
