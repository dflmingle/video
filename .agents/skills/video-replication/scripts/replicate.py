"""Evidence-led video tools. Run --help. Outputs never overwrite existing files."""
import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import sys
import cv2
import numpy as np
from common import capture, evidence, frame, fresh_dir, imread, imwrite, panel, probe, read, sha, write, Encoder
from vision import associate, binary_metrics, components, flow, mask, register


def generator_hashes():
    folder=Path(__file__).resolve().parent
    return {name:sha(folder/name) for name in ('replicate.py','common.py','vision.py','reconstruction.py')}


def effect_proxy(im):
    hsv=cv2.cvtColor(im,cv2.COLOR_BGR2HSV)
    m=np.uint8((hsv[:,:,2]>=235)&(hsv[:,:,1]<=80))*255
    count,_,stats,_=cv2.connectedComponentsWithStats(m)
    return dict(bright_area_fraction=float(np.mean(m>0)),bright_component_count=int(sum(s[4]>=2 for s in stats[1:])),
                caveat='Visible bright components, NOT physical shots/impacts; thresholds require project calibration')


def checked_media(path):
    meta=probe(path,True)
    if meta['decode_status']!='PASS' or meta['time_basis']!='CFR_VERIFIED_OPENCV':
        raise ValueError('Decode/time base unverified; normalize an analysis copy with explicit PTS mapping first')
    return meta


def bounds(meta,start,end):
    end=meta['duration_cfr_estimate'] if end is None else end
    if not 0<=start<end<=meta['duration_cfr_estimate']+1e-6:raise ValueError('Invalid time range')
    return math.ceil(start*meta['fps']-1e-8), min(meta['frames_reported'],math.ceil(end*meta['fps']-1e-8))


def cmd_probe(a):
    result=probe(a.video,a.decode); write(a.out,result)
    print(json.dumps(result,ensure_ascii=True))


def cmd_sample(a):
    meta=checked_media(a.video); start,end=bounds(meta,a.start,a.end); out=fresh_dir(a.out)
    stride=max(1,round(a.interval*meta['fps'])); indices=sorted(set(range(start,end,stride))|{end-1})
    c=capture(a.video); rows=[]
    for n in indices:
        im=frame(c,n); name=f'f{n:07d}.jpg'; imwrite(out/name,im)
        rows.append(dict(frame=n,t=n/meta['fps'],path=name,sha256=sha(out/name)))
    c.release(); write(out/'samples.json',dict(source=meta,samples=rows))
    print(f'{len(rows)} evidence frames: {out}')


def cmd_analyze(a):
    cfg=read(a.config); meta=checked_media(a.video); start,end=bounds(meta,a.start,a.end)
    if not cfg.get('classes'):raise ValueError('Configure visible candidate masks after inspecting frames')
    out=fresh_dir(a.out); c=capture(a.video); c.set(1,start)
    width=cfg.get('analysis_width',meta['width']); height=round(meta['height']*width/meta['width'])
    stride=max(1,round(a.interval*meta['fps'])); previous=None; active=defaultdict(dict); objects={}; counter=0
    samples=[]; changes=[]; fx=[]
    for n in range(start,end):
        ok,raw=c.read()
        if not ok:raise ValueError(f'Decode interrupted at {n}')
        im=cv2.resize(raw,(width,height)); gray=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)
        delta=0. if previous is None else float(cv2.absdiff(gray,previous).mean()/255)
        threshold=cfg.get('adaptive_change_threshold')
        take=(n-start)%stride==0 or n==end-1 or (threshold is not None and delta>threshold)
        if take:
            t=n/meta['fps']; name=f'evidence/f{n:07d}.jpg'; imwrite(out/name,im)
            refs=[dict(path=name,frame=n,t=t,sha256=sha(out/name))]
            samples.append(dict(frame=n,t=t,path=name))
            if delta>cfg.get('shot_change_threshold',1.):
                changes.append(dict(t=t,frame=n,kind='IMAGE_CHANGE_CANDIDATE',evidence=evidence('AUTOMATIC','INFERRED',refs)))
            for class_index,spec in enumerate(cfg['classes']):
                support=mask(im,spec)
                mask_path=f'masks/f{n:07d}-c{class_index:03d}.png'
                imwrite(out/mask_path,support)
                detections=components(support,spec.get('min_area_px',10))
                match=associate(active[spec['id']],detections,t,cfg['association_gate_px'],cfg['max_gap_seconds'])
                for j,d in enumerate(detections):
                    uid=match.get(j)
                    if uid is None:
                        counter+=1; uid=f'candidate-{counter:06d}'
                        objects[uid]=dict(id=uid,type='COLOR_REGION_CANDIDATE',class_hint=spec['id'],physical_identity='UNKNOWN',
                            group_id=None,source_count=None,render_count=None,observations=[],
                            evidence=evidence('AUTOMATIC','INFERRED',refs),states=[],layers=[])
                        active[spec['id']][uid]=objects[uid]['observations']
                    d.update(t=t,frame=n,coordinate_space='analysis_px',mask_ref=mask_path,
                        evidence=evidence('AUTOMATIC','OBSERVED',refs))
                    objects[uid]['observations'].append(d)
            hsv=cv2.cvtColor(im,cv2.COLOR_BGR2HSV)
            bright=(hsv[:,:,2]>=cfg.get('bright_value',235))&(hsv[:,:,1]<=cfg.get('bright_saturation_max',80))
            transient=bright if previous is None else bright&(cv2.absdiff(gray,previous)>cfg.get('transient_delta',20))
            fx.append(dict(frame=n,t=t,bright_area_fraction=float(bright.mean()),transient_area_fraction=float(transient.mean()),
                           proxy_not_event_count=True,evidence=evidence('AUTOMATIC','OBSERVED',refs)))
        previous=gray
    c.release()
    bundle=dict(schema_version='1.0',mode='FAITHFUL',source=meta,generator_hashes=generator_hashes(),
        analysis=dict(start=start/meta['fps'],end=end/meta['fps'],width=width,height=height,
            config=cfg,config_sha256=sha(a.config),camera=cfg.get('camera','UNKNOWN'),
            source_to_analysis=[[width/meta['width'],0,0],[0,height/meta['height'],0],[0,0,1]],
            coordinate_space='analysis_px',identity_validation='UNKNOWN'),
        objects=list(objects.values()),groups=[],memberships=[],events=[],effect_observations=fx,
        image_change_candidates=changes,samples=samples,asset_map=[],validation=[])
    write(out/'bundle.json',bundle)
    print(f'{len(samples)} sampled frames, {len(objects)} candidate tracks (physical identity UNKNOWN): {out}')


def cmd_pair(a):
    first,second=imread(a.first),imread(a.second)
    if first.shape!=second.shape:raise ValueError('Images must share an explicitly prepared analysis canvas')
    result=register(first,second,a.model,a.max_error) if a.command=='register' else flow(first,second,a.max_error)
    result.update(first_sha256=sha(a.first),second_sha256=sha(a.second),method='AUTOMATIC')
    write(a.out,result); print(json.dumps({k:v for k,v in result.items() if k!='points'}))


def check_bundle(b,window,max_speed,max_gap):
    failures=[]; unknown=[]; ids=[o['id'] for o in b['objects']]
    if len(ids)!=len(set(ids)):failures.append('DUPLICATE_OBJECT_IDS')
    idset=set(ids); event_ids=set()
    def evcheck(e,location):
        if e.get('grade') not in ('OBSERVED','INFERRED','SYNTHETIC','UNKNOWN'):failures.append(location+':BAD_GRADE')
        if e.get('method') not in ('AUTOMATIC','CODEX_VISUAL','HUMAN_EDIT','RULE_GENERATED'):failures.append(location+':BAD_METHOD')
        if e.get('grade')!='UNKNOWN' and not e.get('refs'):failures.append(location+':MISSING_PROVENANCE')
    buckets=defaultdict(lambda:dict(object_ids=set(),sample_count=0,path_length_px=0.,jump_count=0,gap_count=0))
    for o in b['objects']:
        evcheck(o.get('evidence',{}),o['id'])
        rows=o.get('observations',[])
        if o.get('physical_identity')=='UNKNOWN':unknown.append(o['id']+':PHYSICAL_IDENTITY')
        if rows:
            times=np.array([r['t'] for r in rows]); points=np.array([r['center'] for r in rows])
            if np.any(np.diff(times)<=0):failures.append(o['id']+':NON_MONOTONIC_TIME'); continue
            for r in rows:
                evcheck(r.get('evidence',{}),o['id']+':OBS')
                q=buckets[int(r['t']//window)]; q['object_ids'].add(o['id']);q['sample_count']+=1
            for i in range(1,len(rows)):
                dt=times[i]-times[i-1]; length=float(np.linalg.norm(points[i]-points[i-1]))
                q=buckets[int(times[i]//window)];q['path_length_px']+=length
                q['gap_count']+=int(dt>max_gap);q['jump_count']+=int(length/dt>max_speed)
                if length/dt>max_speed:failures.append(o['id']+':SPEED_GATE')
        states=o.get('states',[]); hidden=False
        for s in sorted(states,key=lambda x:x['t']):
            if hidden and s['state']!='DEAD_HIDDEN':failures.append(o['id']+':RESURRECTION')
            hidden=hidden or s['state']=='DEAD_HIDDEN'
    for m in b.get('memberships',[]):
        if m['member_id'] not in idset:failures.append('UNRESOLVED_MEMBER:'+m['member_id'])
    for uid in idset:
        memberships=sorted([m for m in b.get('memberships',[]) if m['member_id']==uid],key=lambda x:x['start'])
        for m in memberships:
            if m['end']<=m['start']:failures.append('INVALID_MEMBERSHIP_INTERVAL:'+uid)
        for i in range(len(memberships)):
            for j in range(i+1,len(memberships)):
                x,y=memberships[i],memberships[j]
                if y['start']<x['end'] and y['group_id']!=x['group_id']:failures.append('OVERLAPPING_MEMBERSHIP:'+uid)
    for e in b.get('events',[]):
        if e['id'] in event_ids:failures.append('DUPLICATE_EVENT:'+e['id'])
        event_ids.add(e['id']); evcheck(e.get('evidence',{}),e['id'])
        if e['evidence']['grade']=='SYNTHETIC' and not e.get('authorization_ref'):failures.append('SYNTHETIC_EVENT_WITHOUT_AUTHORIZATION:'+e['id'])
        if e.get('actor_id') is not None:
            if e['actor_id'] not in idset:failures.append('UNKNOWN_ACTOR:'+e['id']); continue
            actor=b['objects'][ids.index(e['actor_id'])]
            disabled=[s['t'] for s in actor.get('states',[]) if s['state'] in ('HIT','FALLING','DEAD_VISIBLE','FADING','DEAD_HIDDEN')]
            if e['kind'] in ('FIRE','ATTACK','MOVE') and disabled and e['t']>=min(disabled):failures.append('DISABLED_ACTOR_EMISSION:'+e['id'])
    windows=[]
    start=b['analysis']['start'];end=b['analysis']['end']
    for k in range(int(start//window),math.ceil(end/window)):
        q=buckets[k]; windows.append(dict(start=max(start,k*window),end=min(end,(k+1)*window),
            tracked_candidate_count=len(q['object_ids']),stable_member_count=sum(o.get('type')=='DISPLAY_MEMBER' and o['id'] in q['object_ids'] for o in b['objects']),
            sample_count=q['sample_count'],path_length_px=q['path_length_px'],jump_count=q['jump_count'],gap_count=q['gap_count']))
    return dict(engineering_status='FAIL' if failures else 'PASS',identity_status='UNKNOWN' if unknown else 'UNREVIEWED',
        visual_status='UNKNOWN',failures=failures,unknown=unknown,windows=windows,
        limits=['Sampled image-space paths only; no claim of true member identities or continuous collision safety'])


def cmd_check(a):
    b=read(a.bundle); result=check_bundle(b,a.window,a.max_speed,a.max_gap)
    result['bundle_sha256']=sha(a.bundle);write(a.out,result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('windows','unknown','failures')}))
    if result['failures']:raise SystemExit(2)


def observation_at(rows,t,max_gap,mode):
    """Match exact frames on both sides of searchsorted (float time can differ)."""
    if not rows:return None
    times=np.array([r['t'] for r in rows]);j=int(np.searchsorted(times,t))
    near=[k for k in (j-1,j) if 0<=k<len(rows)]
    k=min(near,key=lambda k:abs(times[k]-t))
    if abs(times[k]-t)<1e-5:return rows[k]
    if mode!='sprite' or j==0 or j==len(rows) or times[j]-times[j-1]>max_gap:return None
    u=(t-times[j-1])/(times[j]-times[j-1])
    return dict(center=((1-u)*np.array(rows[j-1]['center'])+u*np.array(rows[j]['center'])).tolist())


def cmd_render(a):
    b=read(a.bundle); out=fresh_dir(a.out); assets=read(a.assets)
    w,h=b['analysis']['width'],b['analysis']['height']; w+=w%2; h+=h%2
    start,end=b['analysis']['start'],b['analysis']['end'];fps=b['source']['fps']
    count=round((end-start)*fps); background=assets.get('background_bgr',[230,230,230])
    bindings={x['class_hint']:x for x in assets['bindings']};sprites={}
    for key,v in bindings.items():
        if v.get('sprite'):
            path=Path(a.assets).resolve().parent/v['sprite'];spr=imread(path)
            if spr.ndim!=3 or spr.shape[2]!=4:raise ValueError('Sprites require RGBA')
            sprites[key]=spr
    enc=Encoder(out/'diagnostic.mp4',w,h,fps)
    for n in range(count):
        t=start+n/fps;im=np.full((h,w,3),background,np.uint8)
        for o in b['objects']:
            binding=bindings.get(o['class_hint']);rows=o['observations']
            if binding is None or not rows:continue
            r=observation_at(rows,t,assets['max_gap_seconds'],binding['mode'])
            if r is None:continue # Do not invent contour topology between sparse observations.
            if binding['mode']=='contour':
                if len(r['contour'])>=3:cv2.drawContours(im,[np.rint(r['contour']).astype(np.int32)],-1,binding['color_bgr'],binding.get('thickness',1),cv2.LINE_AA)
            else:
                spr=sprites[o['class_hint']];sw,sh=binding['size_px'];spr=cv2.resize(spr,(sw,sh))
                anchor=binding['anchor'];x=round(r['center'][0]-anchor[0]*sw);y=round(r['center'][1]-anchor[1]*sh)
                x0,y0=max(0,x),max(0,y);x1,y1=min(w,x+sw),min(h,y+sh)
                if x1>x0 and y1>y0:
                    cut=spr[y0-y:y1-y,x0-x:x1-x];alpha=cut[:,:,3:4]/255
                    im[y0:y1,x0:x1]=np.uint8(cut[:,:,:3]*alpha+im[y0:y1,x0:x1]*(1-alpha))
        enc.send(im)
        if n in (0,count//2,count-1):imwrite(out/f'preview-{n:05d}.png',im)
    enc.close()
    write(out/'render.json',dict(status='DIAGNOSTIC_ONLY',bundle_sha256=sha(a.bundle),asset_sha256=sha(a.assets),generator_hashes=generator_hashes(),
        source_start=start,source_end=end,frames=count,media=probe(out/'diagnostic.mp4',True),
        limits=['No audio','Image-space candidate regions, not confirmed individual actors','No pose/depth/semantic event reconstruction']))


def cmd_compare(a):
    cfg=read(a.config);out=fresh_dir(a.out);sm=checked_media(a.source);cm=checked_media(a.candidate)
    start,end=bounds(sm,a.start,a.end); sfps=sm['fps'];alignment=cfg['alignment']
    sc=capture(a.source);cc=capture(a.candidate); rows=[]; effects=[]; encoder=None
    for n in range(start,end):
        t=n/sfps;ct=alignment['candidate_time_scale']*t+alignment['candidate_time_offset']
        cn=round(ct*cm['fps'])
        if cn<0 or cn>=cm['frames_reported']:raise ValueError(f'Aligned candidate time outside media at source {t}')
        src=frame(sc,n);cand=frame(cc,cn)
        size=tuple(cfg['canvas']);src=cv2.resize(src,size);cand=cv2.resize(cand,size)
        if alignment.get('candidate_to_source_matrix') is not None:
            cand=cv2.warpPerspective(cand,np.array(alignment['candidate_to_source_matrix'],float),size)
        if (n-start)%a.stride==0 or n==end-1:
            for region in cfg['regions']:
                x0,y0,x1,y1=region['box'];w,h=size
                x0,x1=round(x0*w),round(x1*w);y0,y1=round(y0*h),round(y1*h)
                aa=src[y0:y1,x0:x1];bb=cand[y0:y1,x0:x1]
                effects.append(dict(t=t,candidate_t=cn/cm['fps'],region=region['id'],source=effect_proxy(aa),candidate=effect_proxy(bb)))
                for spec in cfg['classes']:
                    result=binary_metrics(mask(aa,spec),mask(bb,spec))
                    rows.append(dict(t=t,candidate_t=cn/cm['fps'],region=region['id'],class_hint=spec['id'],**result))
            imwrite(out/f'comparison-{n:07d}.jpg',panel(src,cand,f'SOURCE {t:.3f}s | CANDIDATE {cn/cm["fps"]:.3f}s'))
        if a.video:
            p=panel(src,cand,f'SOURCE {t:.3f}s | CANDIDATE {cn/cm["fps"]:.3f}s')
            # yuv420 requires even dimensions.
            p=p[:p.shape[0]//2*2,:p.shape[1]//2*2]
            if encoder is None:encoder=Encoder(out/'comparison.mp4',p.shape[1],p.shape[0],sfps)
            encoder.send(p)
    if encoder:encoder.close()
    sc.release();cc.release();windows=[]
    keys=sorted(set((int(r['t']//a.window),r['region'],r['class_hint']) for r in rows))
    for k,region,cl in keys:
        selected=[r for r in rows if int(r['t']//a.window)==k and r['region']==region and r['class_hint']==cl]
        mean=lambda key:float(np.mean([r[key] for r in selected if r.get(key) is not None])) if any(r.get(key) is not None for r in selected) else None
        windows.append(dict(start=k*a.window,end=(k+1)*a.window,region=region,class_hint=cl,samples=len(selected),
            mean_iou=mean('iou'),mean_chamfer_px=mean('symmetric_chamfer_px'),mean_density_mae=mean('density_mae')))
    write(out/'metrics.json',dict(source_sha256=sm['sha256'],candidate_sha256=cm['sha256'],alignment=alignment,generator_hashes=generator_hashes(),
        alignment_validation=alignment['validation'],rows=rows,windows=windows,effect_proxies=effects,visual_status='UNREVIEWED',
        media=probe(out/'comparison.mp4',True) if encoder else None,
        limits=['HSV metrics are appearance proxies','No automatic shot/death counts','No visual PASS inferred from metrics']))
    print(f'Aligned regional comparisons: {out}')


def cmd_plan(a):
    b=read(a.bundle)
    windows=[]
    for start in np.arange(b['analysis']['start'],b['analysis']['end'],a.window):
        end=min(float(start)+a.window,b['analysis']['end']); groups=defaultdict(list)
        for o in b['objects']:
            rows=[r for r in o['observations'] if start<=r['t']<end]
            if rows:groups[o['class_hint']].append(dict(id=o['id'],first_t=rows[0]['t'],last_t=rows[-1]['t'],samples=len(rows)))
        windows.append(dict(start=float(start),end=end,candidate_groups=dict(groups),boundary_status='PENDING_IDENTITY_AND_STATE_INTEGRATION'))
    plan=dict(status='DRAFT_REQUIRES_VISUAL_REVIEW',reference_sha256=b['source']['sha256'],
        video_type=a.video_type,engine=a.engine,methods=b['analysis']['config'],
        coordinate_space=b['analysis']['coordinate_space'],identity='CANDIDATE_ASSOCIATION_ONLY',windows=windows,
        commands=[['python',str(Path(__file__).resolve()),'check',str(Path(a.bundle).resolve()),'--max-speed','CALIBRATE_PX_PER_SECOND','--max-gap','CALIBRATE_SECONDS','--out','NEW_CHECK_PATH'],
                  ['python',str(Path(__file__).resolve()),'render',str(Path(a.bundle).resolve()),'--assets','REVIEWED_ASSET_MAP_PATH','--out','NEW_RENDER_DIR']],
        tasks=[dict(start=b['analysis']['start'],end=b['analysis']['end'],
            inputs=['bundle.json','raw evidence frames','asset map'],
            actions=['Review components and camera compensation','Resolve physical identities or preserve UNKNOWN',
                'Bind stable display IDs and fit spatial support','Rebuild continuous paths and evidence-backed events',
                'Adapt supplied assets without altering authoritative paths','Render continuous windows, compare, correct, protect regression'],
            gate='SPATIAL + TEMPORAL + EVENT + ENCODED_VISUAL_REVIEW')],
        unavailable=['Automatic semantic identity','Automatic causal event attribution','Universal renderer'])
    write(a.out,plan)


def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True)
    q=s.add_parser('probe');q.add_argument('video');q.add_argument('--out',required=True);q.add_argument('--decode',action='store_true');q.set_defaults(run=cmd_probe)
    for command in ('sample','analyze'):
        q=s.add_parser(command);q.add_argument('video');q.add_argument('--out',required=True);q.add_argument('--start',type=float,default=0);q.add_argument('--end',type=float);q.add_argument('--interval',type=float,default=.25)
        if command=='analyze':q.add_argument('--config',required=True)
        q.set_defaults(run=cmd_sample if command=='sample' else cmd_analyze)
    for command in ('register','flow'):
        q=s.add_parser(command);q.add_argument('first');q.add_argument('second');q.add_argument('--out',required=True);q.add_argument('--max-error',type=float,default=2.);q.add_argument('--model',choices=['affine','homography'],default='affine');q.set_defaults(run=cmd_pair)
    q=s.add_parser('check');q.add_argument('bundle');q.add_argument('--out',required=True);q.add_argument('--window',type=float,default=5);q.add_argument('--max-speed',type=float,required=True);q.add_argument('--max-gap',type=float,required=True);q.set_defaults(run=cmd_check)
    q=s.add_parser('render');q.add_argument('bundle');q.add_argument('--assets',required=True);q.add_argument('--out',required=True);q.set_defaults(run=cmd_render)
    q=s.add_parser('compare');q.add_argument('source');q.add_argument('candidate');q.add_argument('--config',required=True);q.add_argument('--out',required=True);q.add_argument('--start',type=float,default=0);q.add_argument('--end',type=float);q.add_argument('--stride',type=int,default=8);q.add_argument('--window',type=float,default=5);q.add_argument('--video',action='store_true');q.set_defaults(run=cmd_compare)
    q=s.add_parser('plan');q.add_argument('bundle');q.add_argument('--video-type',required=True);q.add_argument('--engine',required=True);q.add_argument('--window',type=float,default=5);q.add_argument('--out',required=True);q.set_defaults(run=cmd_plan)
    a=p.parse_args()
    for key in ('interval','window','stride','max_speed','max_gap','max_error'):
        if hasattr(a,key) and getattr(a,key)<=0:p.error(f'{key} must be positive')
    a.run(a)

if __name__=='__main__':
    try:main()
    except (ValueError,FileExistsError,FileNotFoundError,KeyError) as e:
        print(f'ERROR: {e}',file=sys.stderr);sys.exit(2)
