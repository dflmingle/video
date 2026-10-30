from pathlib import Path
p=Path('tools/build_simulation_v18.py')
s=p.read_text(encoding='utf8').replace('from archers_v18 import Archers','from archers_v21 import Archers').replace("version='V18'","version='V21'")
Path('tools/build_simulation_v21_archers.py').write_text(s,encoding='utf8')
