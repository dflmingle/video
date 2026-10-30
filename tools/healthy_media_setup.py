from pathlib import Path
P=Path(__file__).resolve().parents[1]
s=(P/'tools/capture_v15.mjs').read_text().replace("local=variant==='LOCAL'","local=variant!=='FINAL'").replace("'tools/capture_v15.mjs'","'tools/capture_healthy_v15.mjs'")
(P/'tools/capture_healthy_v15.mjs').write_text(s)
s=(P/'tools/media_v15.py').read_text().replace("if variant=='LOCAL':","if variant!='FINAL':").replace("name='V15-50-members-5s-validation.mp4'","name='V15-50-members-5s-healthy-charge.mp4'").replace("Fixture: member 1 falls at 1.5s; member 7 wounded at 1.8s. No battle arrows.","All 50 unhit for 5 seconds. Motion and phase use the production controller.")
(P/'tools/media_healthy_v15.py').write_text(s)
