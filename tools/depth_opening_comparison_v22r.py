from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json
P=Path(__file__).resolve().parents[1];O=P/'output/v22r-depth';S=json.loads((P/'docs/v22r-depth/setup.json').read_text());font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',22)
im=Image.new('RGB',(1440,2312),'#222629');d=ImageDraw.Draw(im)
entries=[('D2 / +20% / gap 5.909',P/'output/v22r-distance/D2-opening.jpg')]+[(f"{c['label']} / +{c['actualIncreaseRatio']*100:.2f}% / gap {c['actualFrontNetGap']:.3f}",O/('opening-'+c['label'])/'frames/F0000.png') for c in S['candidates']]
for j,(title,path) in enumerate(entries):
 x=j%2*720;y=j//2*1156;im.paste(Image.open(path),(x,y+60));d.text((x+10,y+20),title,font=font,fill='white')
im.save(O/'opening-D2-E1-E2-E3.jpg',quality=95)
