from pathlib import Path
P=Path(__file__).resolve().parents[1]
s=(P/'tools/prepare_v12.py').read_text(encoding='utf-8')
exec(s[s.index("p=P/'src/main-camera.js'"):],dict(P=P,hashes={}))
