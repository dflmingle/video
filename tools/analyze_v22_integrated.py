"""Read-only audit of actual V22 integrated arrays/events; never prospective replay.
Usage: python tools/analyze_v22_integrated.py --source-root ../PveMontageShot01V22
"""
from pathlib import Path
import argparse, collections, csv, hashlib, json, math, subprocess
import numpy as np
from scipy.spatial import cKDTree
NAMES=['WAITING','MOVING','ARRIVING','AIMING','DRAWING','RELEASING','RECOVERING','TURNING']
COLUMNS=['state','timer','target','lastRelease','walkPhase','turnPhase','actionPhase','moveSpeed','facingYaw','targetYaw','stateProgress','releaseEventId']
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def stat(a):
    a=np.asarray(a,dtype=float)
    return None if not a.size else dict(min=float(a.min()),p10=float(np.percentile(a,10)),median=float(np.median(a)),p90=float(np.percentile(a,90)),max=float(a.max()))
def first(mask,fps):
    frames=np.flatnonzero(np.any(mask,axis=1));return None if not len(frames) else float(frames[0]/fps)
def fire_diagnosis(root,s,p,bc):
    import sys,copy
    sys.path.insert(0,str(root/'tools'))
    from archers_v22 import Archers
    c=s['config'];fps=c['simulationFps'];nb=s['blueCount'];nr=s['redCount'];units=s['units'][:nb];events=s['events'];controller=Archers(copy.deepcopy(units),c);groups=collections.defaultdict(collections.Counter);replay_mismatch=0;replay_examples=[];examples=[]
    hp=np.full(nr,c['redHitPoints']);next_allowed=np.zeros(nr);pending=np.zeros(nr,int)
    by_release=collections.defaultdict(list);by_hit=collections.defaultdict(list)
    for e in events:by_release[e['releaseFrame']].append(e);by_hit[e['impactFrame']].append(e)
    for f in range(len(p)):
        t=f/fps
        for e in by_hit[f]:hp[e['target']-nb]-=e['plannedDamage'];pending[e['target']-nb]-=1
        if hasattr(controller,'memberShots'):
            controller.memberShots[:]=0
            for g in controller.groupShots:controller.groupShots[g]=0
            for old_event in events:
                if old_event['releaseFrame']<f:
                    j=old_event['shooter'];controller.memberShots[j]+=1;controller.groupShots[units[j]['group']]+=1
        prev=bc[max(0,f-1)];controller.state=prev[:,0].astype(np.uint8).copy();controller.timer=prev[:,1].copy();controller.target=prev[:,2].astype(int).copy();controller.facingYaw=bc[f,:,8].copy();controller.position=p[max(0,f-1),:nb].astype(float).copy();controller.redPositions=p[max(0,f-1),nb:]
        controller.targetYaw=np.array([controller._threat_yaw(j) for j in range(nb)])
        controller.position=p[f,:nb].astype(float).copy();controller.lastRelease=prev[:,3].copy();controller.releaseEventId=prev[:,11].astype(int).copy();controller._lastTime=t
        # Movement owns transition into AIMING and resets its timer.
        for j in range(nb):
            if controller.state[j] in [0,1,2,7]:
                controller.state[j]=round(bc[f,j,0]);controller.timer[j]=0. if controller.state[j]==3 else bc[f,j,1]
        reserved=(pending>0)|(t<next_allowed)|(hp<=0)
        claimed={int(v):j for j,v in enumerate(controller.target) if v>=0 and controller.state[j] in [3,4]}
        original_select=controller.select
        def select(j,red,health,excluded,now):
            dist=np.linalg.norm(red-controller.position[j],axis=1);geometry=(health>0)&(dist<=c['archerRange']);unreserved=geometry&~reserved;available=geometry&~excluded;g=units[j]['group'];groups[g]['selectCalls']+=1;groups[g]['geometryCandidatesTotal']+=int(geometry.sum());groups[g]['reservedCandidatesTotal']+=int((geometry&reserved).sum());groups[g]['claimedCandidatesTotal']+=int((unreserved&excluded).sum())
            if geometry.any():groups[g]['selectCallsInRange']+=1
            if geometry.any() and not unreserved.any():groups[g]['allReservedCalls']+=1
            if unreserved.any() and not available.any():groups[g]['allRemainingClaimedCalls']+=1
            if available.any():groups[g]['selectHasAvailableCalls']+=1
            return original_select(j,red,health,excluded,now)
        controller.select=select
        before=controller.state.copy();old_target=controller.target.copy()
        def spawn(j,target,now,draw):
            matches=[e for e in by_release[f] if e['shooter']==j]
            return matches[0] if matches else dict(id='A999999',release=now)
        controller.update_fire(t,1/fps,p[f,nb:],hp,reserved,spawn);controller.select=original_select
        bad=np.flatnonzero((controller.state!=np.rint(bc[f,:,0]))|(controller.target!=np.rint(bc[f,:,2])));replay_mismatch+=len(bad)
        replay_examples.extend(dict(t=t,id=units[j]['id'],group=units[j]['group'],state=int(controller.state[j]),expectedState=int(bc[f,j,0]),target=int(controller.target[j]),expectedTarget=int(bc[f,j,2])) for j in bad if len(replay_examples)<12)
        for j,u in enumerate(units):
            g=u['group'];st=int(before[j]);aft=int(controller.state[j]);target=int(controller.target[j]);dist=np.linalg.norm(p[f,nb:]-p[f,j],axis=1);geometry=(hp>0)&(dist<=c['archerRange'])
            if st in [3,4] and geometry.any():groups[g]['readyInRangeFrames']+=1
            if st==3 and target>=0:
                delta=(controller.targetYaw[j]-controller.facingYaw[j]+math.pi)%(2*math.pi)-math.pi
                if abs(delta)>=.16:groups[g]['aimTurnBlockedFrames']+=1
            if st==3 and aft==4:groups[g]['drawEntries']+=1
            if st==4 and aft==3:
                groups[g]['drawAborts']+=1;old=int(old_target[j]);why='unknown'
                if old>=0:
                    why='dead' if hp[old]<=0 else 'reserved' if reserved[old] else 'range' if dist[old]>c['archerRange'] else 'claimed' if claimed.get(old,j)!=j else 'unknown'
                groups[g]['drawAbort_'+why]+=1
                if g==3 and len(examples)<8:examples.append(dict(t=t,id=u['id'],target=old,cause=why,distance=float(dist[old]) if old>=0 else None))
        for e in by_release[f]:target=e['target']-nb;pending[target]+=1;next_allowed[target]=e['impact']+c['minHitInterval']
    return dict(replayStateOrTargetMismatches=replay_mismatch,replayMismatchExamples=replay_examples,bySquad={str(k):dict(v) for k,v in groups.items()},centralAbortExamples=examples,method='Replays only production update_fire from recorded pre/post movement rows; no movement re-simulation or source writes.')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source-root',type=Path,default=Path(__file__).resolve().parents[1]);ap.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[1]/'output/v22-integrated-review');args=ap.parse_args();root=args.source_root.resolve();out=args.output;out.mkdir(parents=True,exist_ok=True)
    result=dict(sourceRoot=str(root),variants={},checks=[],limitations=['Recorded-state audit, not normal-speed full-video visual acceptance.','State same-pair rate includes legitimate common idle/aim states; pose equality is reported separately.','V20 event endpoints can be nominal despite IMPACT_IN_SHOT: resolved damage count is reported separately.','Capture audit checks existing browser samples only, not all encoded MP4 frames.'])
    node_samples=[];sample_expected=[]
    def check(name,ok,variant,detail=None):result['checks'].append(dict(name=name,passed=bool(ok),variant=variant,detail=detail))
    for name in ['V20-B','V21','V22-B','V22-C']:
        folder=root/'variants'/name;s=json.loads((folder/'simulation.json').read_text(encoding='utf8'));c=s['config'];fps=c['simulationFps'];nb=s['blueCount'];nr=s['redCount'];n=nb+nr;frames=s['frames'];end=(frames-1)/fps
        trajectory_file=folder/('trajectories.npy' if (folder/'trajectories.npy').exists() else 'trajectories.f32');p=np.load(trajectory_file) if trajectory_file.suffix=='.npy' else np.fromfile(trajectory_file,dtype=np.float32).reshape(frames,n,2);raw=np.fromfile(folder/'blue-control.f32',dtype=np.float32).reshape(frames,nb,12);bc=np.load(folder/'blue-control.npy') if (folder/'blue-control.npy').exists() else raw.copy();state=np.rint(bc[:,:,0]).astype(int);units=s['units'][:nb];audit=json.loads((folder/'asset-render-audit.json').read_text(encoding='utf8'));clips=audit['models']['archer']['clips'];events=s['events'];hits=[e for e in events if e.get('resolution')=='IMPACT_IN_SHOT' and e['impact']<=end+1e-7];resolved=[e for e in hits if e.get('damage') is not None]
        if name=='V21':check('actual V21 baseline fingerprint',s.get('version')=='V21-INTEGRATED' and len(events)==98 and len(hits)==55,name)
        r=dict(sourceFiles={p.name:dict(sha256=digest(p),mtime=p.stat().st_mtime) for p in [folder/'simulation.json',trajectory_file,folder/'blue-control.f32']},frames=frames,blueCount=nb,redCount=nr,hold=float(c.get('redChargeStart',0)),preAim=bool(c.get('preAim',False)),configDuration=c['duration'],simulationEnd=end,lastRendererSample=end-1/c['fps'],actualEvents=len(events),nominalImpactsInShot=len(hits),resolvedDamagingImpacts=len(resolved),uniqueShooters=len(set(e['shooter'] for e in events)),unfiredArchers=nb-len(set(e['shooter'] for e in events)),timeline={},bins=[],squads={},abi={},browserCaptures=[])
        check('control columns match stable ABI',s.get('controlColumns')==COLUMNS,name);check('control f32 shape/values valid',np.array_equal(raw,bc) and np.isfinite(raw).all(),name,'Compared with NPY' if (folder/'blue-control.npy').exists() else 'Baseline has F32 only; no independent NPY copy');check('frame count',len(p)==frames and len(bc)==frames and abs(c['duration']-end)<1e-6,name)
        tl=r['timeline'];tl.update(firstMoving=first(state==1,fps),firstArriving=first(state==2,fps),firstTurning=first(state==7,fps),firstAiming=first(state==3,fps),firstTargetValidAiming=first((state==3)&(bc[:,:,2]>=0)&(bc[:,:,1]>0),fps),firstDrawing=first(state==4,fps),firstRelease=min((e['release'] for e in events),default=None),firstNominalHit=min((e['impact'] for e in hits),default=None),firstResolvedHit=min((e['impact'] for e in resolved),default=None),end=end)
        tl['firstRangeValidControlTarget']=first((bc[:,:,2]>=0)&np.isin(state,[3,4]),fps);tl['firstAimingTimerPositive']=first((state==3)&(bc[:,:,1]>0),fps)
        tl['postNominalHitWindow']=None if tl['firstNominalHit'] is None else end-tl['firstNominalHit'];tl['postResolvedHitWindow']=None if tl['firstResolvedHit'] is None else end-tl['firstResolvedHit']
        for lo in np.arange(0,end+1e-7,.25):
            hi=min(float(lo+.25),end+1e-7);r['bins'].append(dict(start=float(lo),end=hi,releases=sum(lo<=e['release']<hi for e in events),nominalHits=sum(lo<=e['impact']<hi for e in hits),resolvedHits=sum(lo<=e['impact']<hi for e in resolved)))
        with (out/(name+'-first20-events.csv')).open('w',newline='',encoding='utf8') as f:
            w=csv.writer(f);w.writerow(['seconds','memberID','group','fromState','toState','stateTimer','targetIndex','actionPhase','walkPhase','releaseEventId','x','z','slotOffsetX','slotOffsetZ','source'])
            for j,u in enumerate(units[:20]):
                changes=np.r_[0,np.flatnonzero(state[1:,j]!=state[:-1,j])+1]
                for k in changes:
                    q=p[k,j];target=np.asarray(u.get('target',[u['start'][0],u['start'][1]-c['blueAdvance']]))
                    w.writerow([k/fps,u['id'],u['group'],NAMES[state[k-1,j]] if k else '',NAMES[state[k,j]],float(bc[k,j,1]),int(bc[k,j,2]),float(bc[k,j,6]),float(bc[k,j,4]),int(bc[k,j,11]),*map(float,q),*map(float,q-target),'authoritative final control row'])
        with (out/(name+'-release-events.csv')).open('w',newline='',encoding='utf8') as f:
            w=csv.writer(f);w.writerow(['id','shooterID','release','drawStartRecorded','aimStartDerivedNotStateEntry','impact','resolution','damage','releaseDistance','releaseControlState','releaseControlPhase','releaseControlEventId'])
            for e in events:
                k=e['releaseFrame'];j=e['shooter'];w.writerow([e['id'],e['shooterID'],e['release'],e.get('drawStart'),e.get('aimStart'),e['impact'],e.get('resolution'),e.get('damage'),e['releaseDistance'],NAMES[state[k,j]],float(bc[k,j,6]),int(bc[k,j,11])])
        # Pairwise rates within actual squads; independent clip-frame equality is
        # evaluated only while both members are active in a locomotion/shot state.
        for group in sorted(set(u['group'] for u in units)):
            ix=np.array([j for j,u in enumerate(units) if u['group']==group]);pairs=np.array([(a,b) for k,a in enumerate(ix) for b in ix[k+1:]])
            a,b=pairs.T;same_state=state[:,a]==state[:,b];active=np.isin(state[:,a],[1,2,4,5,6])&np.isin(state[:,b],[1,2,4,5,6]);phase=np.where(np.isin(state,[1,2]),bc[:,:,4],bc[:,:,6]);quant=np.floor(phase*np.where(np.isin(state,[1,2]),clips['move']['phases'],clips['attack']['phases'])).astype(int);same_pose=same_state&(quant[:,a]==quant[:,b]);attack_pairs=np.isin(state[:,a],[4,5,6])&np.isin(state[:,b],[4,5,6]);moving_pairs=np.isin(state[:,a],[1,2])&np.isin(state[:,b],[1,2]);times=np.arange(frames)/fps;combat=times>=tl['firstRelease'] if tl['firstRelease'] is not None else np.zeros(frames,bool)
            occupied=np.isin(state[:,ix],[3,4,5,6,7]);targets=np.array([u.get('target',[u['start'][0],u['start'][1]-c['blueAdvance']]) for u in np.array(units,dtype=object)[ix]]);offset=p[:,ix]-targets[None,:,:];radius=np.linalg.norm(offset,axis=2)
            transitions={}
            for st in [1,2,7,3,4,5,6]:
                entries=[np.flatnonzero(state[:,j]==st)[0]/fps for j in ix if np.any(state[:,j]==st)]
                transitions[NAMES[st]]=dict(members=len(entries),firstEntryDistribution=stat(entries))
            r['squads'][str(group)]=dict(members=len(ix),stateSamePairRate=float(same_state.mean()),activeSameClipFramePairRate=float(same_pose[active].mean()) if active.any() else None,attackSameClipFramePairRate=float(same_pose[attack_pairs].mean()) if attack_pairs.any() else None,movingSameClipFramePairRate=float(same_pose[moving_pairs].mean()) if moving_pairs.any() else None,combatStateSamePairRate=float(same_state[combat].mean()) if combat.any() else None,stationarySlotRadius=stat(radius[occupied]),firstStateEntries=transitions)
        gaps=[];surface=[];previous=None;first_ready_range=np.full(nb,np.nan);ever_ready_in_range=np.zeros(nb,bool);ever_in_range=np.zeros(nb,bool)
        for k in range(frames):
            gap=float(cKDTree(p[k,:nb]).query(p[k,nb:])[0].min());gaps.append(gap);lower=gap-2*c['weaponEnvelopeRadius']
            alive=np.array([u.get('deathTime') is None or u['deathTime']>k/fps for u in s['units'][nb:]])
            distance_to_live=cKDTree(p[k,nb:][alive]).query(p[k,:nb])[0];within=distance_to_live<=c['archerRange'];ever_in_range|=within;ready_now=within&np.isin(state[k],[3,4,5,6]);first_ready_range[ready_now&~np.isfinite(first_ready_range)]=k/fps;ever_ready_in_range|=ready_now
            if k:
                step=np.linalg.norm(p[k]-p[k-1],axis=1);lower=min(gap,previous)-.5*(step[:nb].max()+step[nb:].max())-2*c['weaponEnvelopeRadius']
            surface.append(float(lower));previous=gap
        firing_members={e['shooter'] for e in events}
        r['firingCoverage']=dict(everInRange=int(ever_in_range.sum()),everReadyAndInRange=int(ever_ready_in_range.sum()),neverFiredDespiteReadyAndInRange=[units[j]['id'] for j in range(nb) if ever_ready_in_range[j] and j not in firing_members],neverInRange=int((~ever_in_range).sum()),bySquad={str(g):dict(shooters=sum(j in firing_members for j,u in enumerate(units) if u['group']==g),arrows=sum(units[e['shooter']]['group']==g for e in events),everReadyInRange=sum(ever_ready_in_range[j] for j,u in enumerate(units) if u['group']==g),readyInRangeSecondsBeforeEnd=stat([end-first_ready_range[j] for j,u in enumerate(units) if u['group']==g and np.isfinite(first_ready_range[j])])) for g in sorted(set(u['group'] for u in units))})
        sorted_releases=sorted(e['release'] for e in events);r['interReleaseGap']=stat(np.diff(sorted_releases))
        r['safety']=dict(minCenterGap=min(gaps),minConservativeSurfaceGap=min(surface),required=c['minimumEnemyClearance']);check('interframe no-contact envelope',min(surface)>=c['minimumEnemyClearance'],name)
        # Range-only optimistic ceiling on the recorded fixed paths. This is a
        # theoretical bound, not hypothetical new combat or promised duration.
        range_first=None;min_gap=math.inf
        for k in range(frames):
            if gaps[k]<=c['archerRange']:
                range_first=k/fps;min_gap=gaps[k];break
        redv=np.linalg.norm(np.diff(p[:,nb:],axis=0)*fps,axis=2);bluev=np.linalg.norm(np.diff(p[:,:nb],axis=0)*fps,axis=2);reach=max(c.get('arrowOriginForward',.38),np.linalg.norm(np.array(audit['models']['archer'].get('bowReleaseLocal',[0,0,0]))[[0,2]]));max_red=float(redv.max());max_blue=float(bluev.max());effective_arrow=max([c['arrowSpeed']]+[np.linalg.norm(np.array(e['destination'])[[0,2]]-np.array(e['origin'])[[0,2]])/(e['impact']-e['release']) for e in events]);early=range_first-1/fps if range_first is not None else None
        hit_lower=None if early is None else early+max(0,min_gap-reach-(max_red+max_blue)/fps)/(effective_arrow+max_red)
        r['encodedEventBoundary']=dict(renderLastSample=end-1/c['fps'],releaseCountThroughRenderSample=sum(e['release']<=end-1/c['fps']+1e-7 for e in events),resolvedHitCountThroughRenderSample=sum(e['impact']<=end-1/c['fps']+1e-7 for e in resolved),note='Current renderer clamps t to config duration minus one output frame; do not describe the last simulation state as visibly rendered.')
        r['theoreticalRangeBound']=dict(firstRecordedRangeEntry=range_first,maxObservedRedSpeed=max_red,maxObservedBlueSpeed=max_blue,optimisticBowReach=reach,configuredArrowSpeed=c['arrowSpeed'],arrowSpeedUpperUsed=effective_arrow,configuredSpeedExceededByRecordedPath=effective_arrow>c['arrowSpeed']+1e-5,optimisticEarliestHitLowerBound=hit_lower,postHitWindowUpperBound=None if hit_lower is None else end-hit_lower,rangeOnlyZeroFlightWindowCeiling=None if early is None else end-early,assumptions='Recorded paths/available range, no aim/draw/deployment delay, nearest target prepared instantly, horizontal interception only, observed maximum speed bounds, one-frame slack; not applied. Does not prove achievability or allow movement outside range.')
        # Actual production JS pose helper, with exactly the recorded row ABI.
        chosen={(k,j) for k in np.linspace(0,frames-1,12,dtype=int) for j in [0,1,6,12,19,36,108,216] if j<nb}
        chosen|={(e['releaseFrame'],e['shooter']) for e in events}
        for k,j in sorted(chosen):
            speed=float(np.linalg.norm(p[k,j]-p[max(0,k-2),j])*fps/max(1,min(k,2)));node_samples.append(dict(bc=bc[k,j].tolist(),speed=speed,unit=units[j],time=k/fps,attackDuration=clips['attack']['duration'],moveDuration=clips['move']['duration']));sample_expected.append((name,k,j,bc[k,j].copy()))
        if name.startswith('V22'):
            r['fireDiagnosis']=fire_diagnosis(root,s,p,bc)
            mismatches=[]
            for e in events:
                k=e['releaseFrame'];j=e['shooter'];expected=int(e['id'].lstrip('A'));row=bc[k,j]
                if state[k,j]!=5 or abs(row[6]-.64)>1e-5 or int(row[11])!=expected or abs(row[3]-e['release'])>1e-5:mismatches.append(e['id'])
            r['abi']['releaseRowMismatches']=mismatches;check('each actual release has state5 phase.64 eventID',not mismatches,name)
            native=np.array(audit['models']['archer']['bowReleaseLocal']);origin_errors=[];facing_errors=[];origin_rows=[]
            for e in events:
                k=e['releaseFrame'];j=e['shooter'];yaw=float(bc[k,j,8]);at=p[k,j];wanted=np.array([at[0]+native[0]*math.cos(yaw)+native[2]*math.sin(yaw),native[1]+.015,at[1]-native[0]*math.sin(yaw)+native[2]*math.cos(yaw)])
                target_yaw=math.atan2(e['destination'][0]-at[0],e['destination'][2]-at[1]);angle=(target_yaw-yaw+math.pi)%(2*math.pi)-math.pi;err=float(np.linalg.norm(np.array(e['origin'])-wanted));origin_errors.append(err);facing_errors.append(abs(angle));origin_rows.append(dict(event=e['id'],originError=err,facingVsDestinationRadians=angle,actualFacing=yaw,targetYaw=target_yaw))
            r['abi']['nativeBowOriginError']=stat(origin_errors);r['abi']['releaseFacingVsDestinationRadians']=stat(facing_errors);r['abi']['largestOriginErrors']=sorted(origin_rows,key=lambda q:q['originError'],reverse=True)[:10]
            check('arrow origin equals native hand rotated by actual release facing',max(origin_errors,default=0)<1e-5,name)

            check('range valid at every release',all(e['releaseDistance']<=c['archerRange']+1e-6 for e in events),name)
            check('every on-screen impact resolves individual damage',len(hits)==len(resolved),name)
        for cap in (root/'output/captures').glob(name+'-*/audit.json'):
            d=json.loads(cap.read_text(encoding='utf8'));record=dict(path=str(cap),detail=d.get('detail'),samples=len(d.get('states',[])),sourceDuration=d.get('sourceDuration'),stale=cap.stat().st_mtime<(folder/'simulation.json').stat().st_mtime or abs(d.get('sourceDuration',0)-end)>1e-6,mismatches=[])
            if not record['stale']:
                for sample in d.get('states',[]):
                    k=min(frames-1,round(min(sample['t'],end-1/c['fps'])*fps))
                    for row in sample['rows']:
                        j=row['index']
                        if j>=nb:continue
                        st=state[k,j];action='move' if st in [1,2] else 'attack' if st in [3,4,5,6] else 'idle';frac=bc[k,j,4]%1 if action=='move' else .64 if st==5 else np.clip(bc[k,j,6],0,.999999) if action=='attack' else units[j]['phase']%1;expected_phase=float(frac*clips[action]['phases'])
                        if row['state']!=NAMES[st] or row.get('release')!=int(bc[k,j,11]):record['mismatches'].append(dict(t=sample['t'],id=row['id'],field='state/release'))
                        if abs(row['phase']-expected_phase)>1e-4:record['mismatches'].append(dict(t=sample['t'],id=row['id'],field='native phase',expected=expected_phase,actual=row['phase']))
                check('browser capture authoritative state/event rows',not record['mismatches'],name,str(cap))
            r['browserCaptures'].append(record)
        result['variants'][name]=r
    helper=root/'src/archer-pose-v22.js';js="""import fs from 'node:fs';import {pathToFileURL} from 'node:url';const {resolveArcherPose}=await import(pathToFileURL(process.argv[1]));const rows=JSON.parse(fs.readFileSync(0,'utf8'));console.log(JSON.stringify(rows.map(x=>{const a=resolveArcherPose(x),b=resolveArcherPose({...x,time:x.time+37});return{a,timeInvariant:a.action===b.action&&a.phaseFraction===b.phaseFraction&&a.yaw===b.yaw};})));"""
    run=subprocess.run(['node','--input-type=module','-e',js,str(helper)],input=json.dumps(node_samples),text=True,capture_output=True,encoding='utf8');check('production JS helper executes',run.returncode==0,'shared',run.stderr[:1000])
    if run.returncode==0:
        poses=json.loads(run.stdout);issues=[]
        for (name,k,j,row),item in zip(sample_expected,poses):
            a=item['a'];st=round(row[0]);want_action='move' if st in [1,2] else 'attack' if st in [3,4,5,6] else 'idle';want_phase=float(row[4]%1) if st in [1,2] else .64 if st==5 else float(np.clip(row[6],0,.999999)) if st in [3,4,6] else None
            ok=item['timeInvariant'] and a['action']==want_action and abs(a['yaw']-row[8])<1e-5 and a['releaseEventId']==round(row[11])
            if st in [1,2,3,4,5,6]:ok=ok and abs(a['phaseFraction']-want_phase)<1e-5
            if not ok:issues.append(dict(variant=name,frame=k,member=j))
        result['poseHelper']=dict(samples=len(poses),mismatches=issues,sourceSHA256=digest(helper));check('recorded ABI reaches independent JS pose',not issues,'shared')
    main_src=(root/'src/main-v22.js').read_text(encoding='utf8');asset_src=(root/'src/assets-v22.js').read_text(encoding='utf8');result['rendererWiring']=dict(helperImport="import {resolveArcherPose}" in main_src,controlRead='blueControl[(frame*nb+i)*BLUE_CONTROL_STRIDE+k]' in main_src,helperApplied='action=bluePose.action;phaseFraction=bluePose.phaseFraction;yaw=bluePose.yaw' in main_src,perInstanceWeight='b.moveWeight.setX' in main_src,perInstancePhase='b.blend.setX' in main_src,shaderInstancePhase='mix(position,nextPosition,poseBlend)' in asset_src,shaderInstanceWeight='mix(restPosition,mix(position,nextPosition,poseBlend),moveWeight)' in asset_src,shaderAttributes="geo.setAttribute('poseBlend',blend)" in asset_src and "geo.setAttribute('moveWeight',moveWeight)" in asset_src,sha256=digest(root/'src/main-v22.js'));check('renderer source connects control helper and instance data',all(v for k,v in result['rendererWiring'].items() if k!='sha256'),'shared')
    result['passed']=all(x['passed'] for x in result['checks']);(out/'result.json').write_text(json.dumps(result,indent=2,default=lambda x:x.item() if isinstance(x,np.generic) else str(x)),encoding='utf8')
    with (out/'quarter-second-arrow-counts.csv').open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=['variant','start','end','releases','nominalHits','resolvedHits']);w.writeheader()
        for name,r in result['variants'].items():
            for row in r['bins']:w.writerow(dict(variant=name,**row))
    print(json.dumps(dict(passed=result['passed'],timelines={n:r['timeline'] for n,r in result['variants'].items()},checks=result['checks'],output=str(out)),indent=2));return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
