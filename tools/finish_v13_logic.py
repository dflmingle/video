from pathlib import Path
P=Path(__file__).resolve().parents[1]
p=P/'tools/build_simulation_v11.py';s=p.read_text(encoding='utf-8')
s=s.replace("   if hf>=N-2:continue", "   if t>C['duration']-1/C['fps']+1e-6:continue")
s=s.replace("events.append(e);scheduled.setdefault(hf,[]).append((target,e));fired[j].append(len(events)-1);nextFire[j]=t+u['cycle']", """events.append(e)
   if hf<N:e['resolution']='IMPACT_IN_SHOT';scheduled.setdefault(hf,[]).append((target,e))
   else:e.update(resolution='IN_FLIGHT_AT_CUT',remainingHP=None,killed=False,destinationEvidence='Extrapolated continuation beyond visible cut, no simulated damage')
   fired[j].append(len(events)-1);nextFire[j]=t+u['cycle']""")
s=s.replace(" e['destination']=[float(positions[e['impactFrame'],e['target'],0]),.85,float(positions[e['impactFrame'],e['target'],1])]", """ if e['resolution']=='IMPACT_IN_SHOT':end=positions[e['impactFrame'],e['target']]
 else:end=positions[-1,e['target']]+velocities[-1,e['target']]*(e['impact']-C['duration'])
 e['destination']=[float(end[0]),.85,float(end[1])]""")
s=s.replace(" e['resolution']='IMPACT_IN_SHOT'\n assert e['damage'] is not None", " if e['resolution']=='IMPACT_IN_SHOT':assert e['damage'] is not None")
a=s.index('# Preserve arrows that are still in flight');b=s.index("for j,u in enumerate(red):u['deathTime']",a)
s=s[:a]+s[b:]
p.write_text(s,encoding='utf-8')
p=P/'tools/capture_camera.mjs';s=p.read_text()
s=s.replace("const states=[],costs=[],screenTracks=[];", "const states=[],costs=[],screenTracks=[],behaviorTracks=[];const behaviorIds=await page.evaluate(()=>{const u=window.sceneRuntime.simulation.units,nb=window.sceneRuntime.simulation.blueCount;return [...Array.from({length:16},(_,i)=>i),...u.map((v,i)=>({v,i})).filter(o=>o.i>=nb&&o.v.army===2&&o.v.platoon===24).slice(0,16).map(o=>o.i)]});")
s=s.replace("states.push(state);screenTracks.push", "states.push(state);behaviorTracks.push(await page.evaluate(ids=>ids.map(i=>window.lastBehavior[i]),behaviorIds));screenTracks.push")
s=s.replace("fs.writeFileSync(`${dir}/${motion?'motion-':''}${shot==='A'?'A-':''}render-checks.json`", "fs.writeFileSync(`${dir}/behavior-tracks.json`,JSON.stringify({indices:behaviorIds,frames:behaviorTracks}));fs.writeFileSync(`${dir}/${motion?'motion-':''}${shot==='A'?'A-':''}render-checks.json`")
p.write_text(s)
