from pathlib import Path
p=Path('tools/build_simulation_v18.py'); s=p.read_text(encoding='utf8'); s=s.replace("archers=Archers(blue,C)", "shift=float(C.get('blueDistanceShiftZ',0.0))\nfor u in blue: u['start'][1]+=shift\narchers=Archers(blue,C)"); s=s.replace("dict(version='V18'", "dict(version='V19-DIST'"); Path('tools/build_simulation_v19_distance.py').write_text(s,encoding='utf8')
