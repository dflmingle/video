from pathlib import Path
import json,sys
from PIL import Image,ImageDraw,ImageFont
p=Path(sys.argv[1] if len(sys.argv)>1 else 'output/v22r-frontfield/evidence')
s=json.loads((p/'evidence.json').read_text(encoding='utf8'));font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',13)
for kind in ['arrow','melee']:
 rows=[x for x in s['rows'] if x['event']['type']==kind]
 im=Image.new('RGB',(1280,216),'#222629');d=ImageDraw.Draw(im)
 for i,r in enumerate(rows):
  a=Image.open(r['file']);x,y=r['screen']
  crop=a.crop((round(x)-30,round(y)-36,round(x)+30,round(y)+24)).resize((160,160))
  im.paste(crop,(i*160,48));d.text((i*160+3,4),f"F{r['frameOffset']:+d} {r['time']:.3f}s",font=font,fill='white')
  d.text((i*160+3,24),f"flash={r['hitFlash']:.3f}",font=font,fill='white')
 im.save(p/f'{kind}-sequence.jpg',quality=95)
print(str(p))
