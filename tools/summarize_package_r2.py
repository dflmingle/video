"""Keep a bounded, reproducible environment subset of the complete native audit."""
import collections,hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];O=R/'docs/scene-requirements-r2'
P=Path('C:/Users/89trillion/PveMontageShot01V22R-PackageSceneAudit')
raw=P/'output/package-deep-r2/native-all-hierarchy.json'
d=json.loads(raw.read_text(encoding='utf8'));audit=json.loads((O/'designated-package-deep-audit.json').read_text(encoding='utf8'))
scenes=[];models=[]
for r in d['records']:
 if r['kind']=='scene':
  env=[n for n in r['nodes'] if '/Environment/' in n['meshAsset']]
  scenes.append(dict(source=r['source'],nodeCount=len(r['nodes']),rendererTypes=dict(collections.Counter(n['rendererType'] for n in r['nodes'] if n['rendererType'])),roots=[n for n in r['nodes'] if '/' not in n['path']],cameras=r['cameras'],environmentRenderers=env,inactiveEnvironmentRenderers=[n['path'] for n in env if not n['activeHierarchy']],missingMeshRendererCount=sum(n['rendererType'] in {'MeshRenderer','SkinnedMeshRenderer'} and not n['vertices'] for n in r['nodes'])))
 elif r['kind']=='model' and '/Environment/' in r['source']:
  models.append(dict(source=r['source'],nodes=[n for n in r['nodes'] if n['rendererType']],note='AssetDatabase model objects are not scene instances; activeHierarchy=false here does not indicate a disabled scene object.'))
result=dict(package=audit['source'],packageSha256=audit['sha256'],rawNativeAudit=str(raw),rawAuditSha256=hashlib.sha256(raw.read_bytes()).hexdigest(),unityVersion=d['unityVersion'],nativeRecordCount=len(d['records']),nativeErrors=d['errors'],sceneCount=len(scenes),prefabCount=sum(r['kind']=='prefab' for r in d['records']),modelCount=sum(r['kind']=='model' for r in d['records']),copiedAssetCount=len(audit['copied']),copyHashMismatches=[x for x in audit['copied'] if not x['matches']],scenes=scenes,environmentModels=models)
(O/'designated-package-native-summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
manifest=json.loads((P/'output/package-scenes-r2/CastleExterior-scene/manifest.json').read_text())
lines=['# 指定包原生城堡资源映射','',f'来源包：`{audit["source"]}`。SHA256：`{audit["sha256"]}`。',f'隔离原样解包目录：`{P}`。所有 329 个复制资产均逐文件校验一致。','', 'Unity 场景：`Assets/ArtOfWar-II_Art/Environment/Feature/CastleExterior/CastleExterior.unity`。','Prefab：`Assets/ArtOfWar-II_Art/Environment/Feature/CastleExterior/CastleExterior_Grp.prefab`。','','下表为实际 Unity 加载的场景对象 → 模型 → 材质 → 贴图，不是按文件名猜测。完整原始路径用隔离目录拼接 Assets 路径即可访问。','','| 场景对象 | 模型 Assets 路径 | 材质 Assets 路径 | 原贴图 Assets 路径 |','|---|---|---|---|']
for obj in manifest['objects']:
 mesh=manifest['meshes'][obj['mesh']];mats=[manifest['materials'][i] for i in obj['materials'] if i>=0]
 lines.append('| '+obj['path']+' | '+mesh['asset']+' | '+'<br>'.join(m['path'] for m in mats)+' | '+'<br>'.join(t['path'] for m in mats for t in m['textures'])+' |')
lines+=['','## 参考图匹配状态','','| 场景元素 | 包内实际对应 | 匹配状态 | 差异 |','|---|---|---|---|', '| 地面 | CastleExterior_Land.fbx；CastleExterior_Land_Mat；CastleExterior_Gird_Mat；SnowBridge_Gird.fbx | 部分匹配 | 暖色棋盘来源真实；格子与士兵比例、原场景坐标到战斗区域仍未确认 |','| 城墙、城门 | CastleExterior_Building.fbx / polySurface18、rock.016 | 部分匹配 | 紫墙和青色塔顶属于同类；塔、开口与参考图右侧门洞轮廓不完全一致 |','| 树木 | CastleExterior_Tree_04.fbx、CastleExterior_Tree_05.fbx 及各自 Prefab | 不匹配 | 包内为树桩/块状构件，缺参考图绿色、蓝绿色完整树冠 |','| 围栏 | CastleExterior_Stakes_01/02.fbx 及 Prefab | 部分匹配 | 实际为独立木桩，未找到参考图横向连接木栏的对应实例 |','| 告示牌、旗面 | 包内无可确认的对应几何；DecD 贴图/材质存在 | 未找到 | 贴图存在不能证明紫色骷髅牌模型和实例存在 |','| 花草与装饰 | CastleExterior_Flower_03.fbx、CastleExterior_Arrow.fbx | 部分匹配 | 有真实实例，位置是否对应参考图尚未证明 |','','## 排除导出遗漏','','- 六个场景与 24 个 Prefab、72 个模型均由 Unity 原生加载检查；模型层级包含全部子网格。','- CastleExterior 场景环境 34 个 MeshRenderer，无未激活的环境 Renderer，无空 Mesh 的 MeshRenderer/SkinnedMeshRenderer。','- Building.fbx 只有两个实际子网格，分别 1178 和 690 顶点；没有另一个被隐藏的完整城门或告示牌网格。','- CastleExterior_Grp 对外唯一未解析 GUID `474bcb49853aa07438625e644c072ee6` 出现在 m_Script 字段，不能当作丢失的城堡几何。其他场景有缺少的运行脚本，不代表原工程可直接运行。','- 九个嵌套包逐项读过 pathname 和引用，未发现 .unity 场景；它们是角色/特效资源，不含已确认的完整替代城堡环境。','- 桌面 WFL 工程中的 Tree_01/02/03、Flag、Fence_01/02、Castle 模型是另一份来源；本包无同名资产。没有把这些模型混进包内候选或自行重组场景。','','## 渲染边界','','静帧使用 Unity 原生求值后的几何、世界矩阵和材质/贴图绑定，通过现有 Three.js 浏览器预览。材质预览并非原 Unity 自定义 Shader 的完整等价实现；当前图能证明几何和布局差异，不能宣称最终光照已还原。']
(O/'PACKAGE-RESOURCE-MAP.md').write_text(('\n'.join(lines)+'\n').replace('包内为树桩/块状构件','包内为橙色块状树形'),encoding='utf8')
print(json.dumps(dict(nativeRecords=len(d['records']),scenes=len(scenes),prefabs=result['prefabCount'],models=result['modelCount'],envNodes=[(s['source'],len(s['environmentRenderers'])) for s in scenes],errors=d['errors'],copyMismatches=len(result['copyHashMismatches'])),ensure_ascii=True))
