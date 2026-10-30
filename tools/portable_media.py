"""Font lookup for English diagnostic video labels on Windows/macOS/Linux."""
import os
from PIL import ImageFont
def diagnostic_font(size):
 candidates=[os.environ.get('VIDEO_FONT',''),'C:/Windows/Fonts/msyh.ttc',
 '/System/Library/Fonts/Supplemental/Arial.ttf',
 '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','DejaVuSans.ttf']
 for path in candidates:
  if not path:continue
  try:return ImageFont.truetype(path,size)
  except OSError:pass
 return ImageFont.load_default()
