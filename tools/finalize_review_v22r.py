import hashlib,json,shutil,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[1];D=R/'docs/v22r';O=R/'output'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
sources=[Path('C:/Users/89trillion/PveMontageShot01V23/output/V22-V23-INDIVIDUAL-same-time-normal-speed.mp4'),Path('C:/Users/89trillion/PveMontageShot01V22/output/V22-C-B-formal-native-recapture.mp4'),Path('C:/Users/89trillion/PveMontageShot01V22/output/V22-C-B-scene-image-final.mp4'),R/'variants/V22-C/trajectories.npy',R/'docs/v22r/user-reference.png']
records=[dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p)) for p in sources]
unchanged=subprocess.check_output(['git','diff','dfcb24c','--','src','baseline','public/native-scenes/NewScene'],cwd=R,text=True)
assert not unchanged
(D/'baseline-preservation.json').write_text(json.dumps(dict(baseline='dfcb24c',sources=records,productionRendererCameraAndBaselineUnchanged=True,oldVideosNotOverwritten=True,scope='V22-R audit and opt-in opening simulation experiment; no V23 backport or formal scene replacement'),indent=2),encoding='utf8')
for name in ['V22-C-camera.json','V22R-overlap-camera.json','fixed-camera.json','encode-check.json']:
    shutil.copy2(O/'v22r-opening'/name,D/name)
shutil.copy2(O/'v22r-scenes/checks.json',D/'same-camera-same-actors-check.json')
items=''.join(f'<h3>V22 scene / CastleExterior candidate / Reference — time {t}</h3><img src="v22r-scenes/ABC-{i}.jpg">' for i,t in enumerate(['0','1.3','2.4167','2.7333']))
html='''<!doctype html><meta charset="utf-8"><title>V22-R 阶段审阅</title><style>body{background:#16191d;color:#e8e8e8;max-width:1200px;margin:35px auto;font:18px/1.6 sans-serif}a{color:#9bd2ff}video{max-width:100%;max-height:750px;background:black}img{max-width:100%}.note{padding:15px;background:#503d20}</style><h1>V22-R 阶段审阅：未通过正式验收</h1><p class="note">场景未确认；开场实验安全截止 2.20 秒，未达到约 4 秒，切点前无真实命中。视频仅为 0–1.5 秒同时运动诊断，不能视为正式场景或近景视觉验收。</p><p><a href="../docs/v22r/REVIEW.md">完整审阅报告</a> · <a href="../docs/v22r/RESOURCE-REPORT.md">原生资源映射</a> · <a href="../docs/v22r/V22R-overlap-0.1s.csv">每 0.1 秒统计</a></p><h2>开场同时间原速对照：左 V22 / 右 V22-R 实验</h2><video controls preload="metadata" src="v22r-opening/V22-V22R-opening-same-time-60fps.mp4"></video><h2>修订开场 1440×2160 / 60fps</h2><video controls preload="metadata" src="v22r-opening/V22R-overlap-opening-1.5s.mp4"></video><h2>原生候选，没有使用截图背景</h2><img src="v22r-scenes/native-candidates.jpg"><p>NewScene 的战斗原坐标实际落在竞技场；CastleExterior 方位、树色与标志仍不匹配；CogworkWastes 是工厂，已排除。</p>'''+items+'''<h2>世界坐标运动曲线</h2><img src="../docs/v22r/V22R-overlap-curves.png"><p>相机逐帧恒定已记录，正常速度视觉完整观看未完成；解码或编码不替代视觉验收。</p>'''
(O/'v22r-review.html').write_text(html,encoding='utf8');print('baseline hashes and review page written')
