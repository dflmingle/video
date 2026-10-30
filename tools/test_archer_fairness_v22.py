"""Isolated same-path firing replay. Does not write production variants."""
from pathlib import Path
import argparse,copy,json,math
import numpy as np
from archers_v22 import Archers,_angle

def replay(root,name):
    folder=root/'variants'/name;s=json.loads((folder/'simulation.json').read_text(encoding='utf8'));c=s['config'];p=np.load(folder/'trajectories.npy');bc=np.load(folder/'blue-control.npy');nb=s['blueCount'];nr=s['redCount'];fps=c['simulationFps'];dt=1/fps;a=Archers(copy.deepcopy(s['units'][:nb]),c);hp=np.full(nr,c['redHitPoints']);next_allowed=np.zeros(nr);pending=np.zeros(nr,int);scheduled={};shots=[];controls=[];draws=np.zeros(nb,int);locked_changes=[]
    # Movement is held to actual recorded paths. Readiness uses actual baseline
    # TURNING->AIMING times; attack yaw follows our independently selected target.
    ready=np.array([np.flatnonzero(np.isin(bc[:,j,0],[3,4,5,6]))[0] if np.any(np.isin(bc[:,j,0],[3,4,5,6])) else len(p)+1 for j in range(nb)])
    for f in range(len(p)):
        t=f*dt
        for target,damage in scheduled.pop(f,[]):
            assert hp[target]>0,'pending arrow reached already dead target'
            hp[target]-=damage;pending[target]-=1
        a.position=p[f,:nb].astype(float).copy();a.redPositions=p[f,nb:]
        for j,u in enumerate(a.units):
            if f<ready[j]:
                a.state[j]=round(bc[f,j,0]);a.timer[j]=float(bc[f,j,1]);a.facingYaw[j]=float(bc[f,j,8])
            elif f==ready[j]:a.enter(j,3,t);a.timer[j]=0.
            if f>=ready[j]:
                a.targetYaw[j]=a._threat_yaw(j);delta=_angle(a.targetYaw[j]-a.facingYaw[j]);a.facingYaw[j]+=np.clip(delta,-u['maxTurnRate']*dt,u['maxTurnRate']*dt)
        reserved=(pending>0)|(t<next_allowed)|(hp<=0);before=a.state.copy();prior_targets=a.target.copy()
        def spawn(j,target,now,draw):
            velocity=(p[min(f+1,len(p)-1),nb+target]-p[max(0,f-1),nb+target])/(dt*(1 if f==0 or f==len(p)-1 else 2));relative=p[f,nb+target]-a.position[j];qa=float(velocity@velocity-c['arrowSpeed']**2);qb=2*float(relative@velocity);qc=float(relative@relative);disc=max(0,qb*qb-4*qa*qc);roots=[(-qb+math.sqrt(disc))/(2*qa),(-qb-math.sqrt(disc))/(2*qa)];flight=max(.18,min(x for x in roots if x>0));impact=f+max(1,round(flight/dt));damage=3 if j%17==0 else 1;pending[target]+=1;next_allowed[target]=impact*dt+c['minHitInterval'];scheduled.setdefault(impact,[]).append((target,damage));event=dict(id=f'A{len(shots):05}',shooter=j,group=a.units[j]['group'],target=target,release=now,drawStart=draw,impact=impact*dt);shots.append(event);return event
        a.update_fire(t,dt,p[f,nb:],hp,reserved,spawn)
        draws+=(before==3)&(a.state==4)
        for j in np.flatnonzero(before==4):
            if a.state[j] in [4,5] and a.target[j]!=prior_targets[j]:locked_changes.append((f,int(j)))
        controls.append(a.control().copy())
    bygroup={str(g):dict(drawEntries=int(sum(draws[j] for j,u in enumerate(a.units) if u['group']==g)),releases=sum(e['group']==g for e in shots),uniqueShooters=len(set(e['shooter'] for e in shots if e['group']==g))) for g in sorted(a.groupShots)}
    original_first=min(e['release'] for e in s['events']);first=min(e['release'] for e in shots)
    assert first<=original_first+dt/2,(first,original_first)
    assert bygroup['3']['drawEntries']>0 and bygroup['3']['releases']>0,bygroup
    assert not locked_changes,locked_changes
    return dict(variant=name,firstRelease=first,originalFirstRelease=original_first,bySquad=bygroup,totalReleases=len(shots),committedTargetChanges=len(locked_changes),method='Isolated production scheduler on same recorded red/blue paths; actual baseline readiness, new bounded target-facing yaw. Not a full combat re-simulation or rendered acceptance.'),np.array(controls)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--source-root',type=Path,default=Path(__file__).resolve().parents[1]);ap.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[1]/'output/v22-fairness-tests');args=ap.parse_args();args.output.mkdir(parents=True,exist_ok=True);results=[]
    for name in ['V22-B','V22-C']:
        result,control=replay(args.source_root,name);again,other=replay(args.source_root,name);assert np.array_equal(control,other),'replay nondeterministic';result['deterministic']=True;results.append(result)
    out=dict(status='PASS',results=results);(args.output/'result.json').write_text(json.dumps(out,indent=2),encoding='utf8');print(json.dumps(out,indent=2))
