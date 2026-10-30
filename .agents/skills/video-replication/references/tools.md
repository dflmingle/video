# 工具用法与实际能力

入口 `scripts/replicate.py`，Python 已有依赖：numpy、opencv-python、scipy；编码另需 imageio-ffmpeg。无自动下载/安装。文件采用 UTF-8；Windows 上使用 `python -X utf8` 可避免控制台或外部验证器默认 GBK 的问题。已有输出拒绝覆盖，重跑使用新目录。源视频/素材只读。先 `--help`，子命令也支持 `--help`。

PowerShell 示例（路径换为当前项目）：

```powershell
$replicaTool = 'C:/Users/89trillion/.codex/skills/video-replication/scripts/replicate.py'
python $replicaTool probe 'D:/project/reference.mp4' --decode --out 'D:/project/audit/metadata.json'
python $replicaTool sample 'D:/project/reference.mp4' --interval 0.25 --out 'D:/project/evidence-v1'
python $replicaTool analyze 'D:/project/reference.mp4' --config 'D:/project/analysis.json' --out 'D:/project/analysis-v1'
python $replicaTool check 'D:/project/analysis-v1/bundle.json' --max-speed 200 --max-gap 0.5 --out 'D:/project/check-v1.json'
python $replicaTool plan 'D:/project/analysis-v1/bundle.json' --video-type '2D overlapping figures' --engine 'existing Canvas renderer' --out 'D:/project/plan-v1.json'
```

速度单位是 analysis_px/s，上述阈值只是调用语法示例，必须按当前视频校准。分析默认每0.25秒取样；特效/快速阶段应更密，`--interval 0.001` 会取每帧。`--start/--end` 限定实验范围；无 end 时覆盖整段可访问视频。采样时每帧解码用于自适应变化候选，保存选中帧；不是可靠语义镜头检测。

分析配置示例（**演示结构，不提供适用于所有片子的颜色值**；OpenCV H=0–179）：

```json
{
  "analysis_width": 640,
  "camera": "UNCOMPENSATED_REQUIRES_REGISTRATION",
  "association_gate_px": 24,
  "max_gap_seconds": 0.5,
  "adaptive_change_threshold": 0.08,
  "shot_change_threshold": 0.3,
  "classes": [
    {"id":"reviewed-ink-candidate", "hsv":[[[0,0,0],[179,255,80]]],
     "min_area_px":12, "close_px":1, "exclude":[], "roi":[0,0,1,1]}
  ]
}
```

候选的 association 不执行跨镜头重置/相机补偿/语义重识别；切镜应分镜头运行并由审查身份表整合。取样轮廓只输出外轮廓；每个取样帧/类别另存由原始解码帧计算的无损 PNG 掩膜，观测 `mask_ref` 指向它，以保留孔洞/内部占据。不要从证据 JPEG 重算来冒充原始掩膜，也不能把 mask 拓扑直接称为真实人物拓扑。

两帧分析：

```powershell
python $replicaTool register 'D:/project/a.png' 'D:/project/b.png' --model affine --max-error 3 --out 'D:/project/registration.json'
python $replicaTool flow 'D:/project/a.png' 'D:/project/b.png' --max-error 1 --out 'D:/project/flow.json'
```

register 返回从 first 到 second 的矩阵，只有通过内部留出门禁才返回可用矩阵。纹理点独立留出不是语义地标真值，仍需检查空间覆盖和动态前景。flow 只给结构点，不给确认的人物 ID。

诊断素材表：

```json
{"background_bgr":[235,235,235], "max_gap_seconds":0.1,
 "bindings":[
   {"class_hint":"reviewed-ink-candidate","mode":"contour","color_bgr":[80,30,80],"thickness":1}
 ]}
```

同一 binding 可改 `mode:"sprite"`，指定相对素材表路径 `sprite:"actor.png"`、`size_px:[20,30]`、`anchor:[0.5,1]`。这是**每个区域候选一个诊断精灵**，不是已把群体映射成真实个体；正式群体应先建立成员映射。

```powershell
python $replicaTool render 'D:/project/analysis-v1/bundle.json' --assets 'D:/project/assets.json' --out 'D:/project/render-v1'
```

`render` 精确观测帧画轮廓，不在稀疏轮廓间胡乱连接顶点；因此连续轮廓演示需要逐帧观测。sprite 中心可在限定短 gap 插值，仍是诊断，不代表运动质量已验收。无音轨。

比较配置：

```json
{"canvas":[640,960],
 "alignment":{"candidate_time_scale":1,"candidate_time_offset":0,
              "candidate_to_source_matrix":null,"validation":"REVIEWED_EVENT_AND_LANDMARKS"},
 "regions":[{"id":"main","box":[0,0,1,1]}],
 "classes":[{"id":"ink","hsv":[[[0,0,0],[179,255,80]]]}]}
```

```powershell
python $replicaTool compare 'D:/project/reference.mp4' 'D:/project/render-v1/diagnostic.mp4' --start 0 --end 3 --config 'D:/project/comparison.json' --stride 3 --window 1 --video --out 'D:/project/compare-v1'
```

输出连续对照 MP4、采样 JPG、逐区域/窗口代理指标、实际时间配对及解码结果。不能自动证明已正确对齐；validation 是用户/操作者提供的声明。不同时间起点须配置 offset，例如输出从源第8秒起，则 candidate_t=source_t−8。

可导入 `reconstruction.py` 的稳定布局、占据分位、二维约束路径、连续最小距离与优先级解析；这些是可运行原语，不是完整自动求解器。运行 `python scripts/test_tools.py` 验证关键行为。完整骨骼渲染、烟语义识别、真实身份恢复、事件因果、声音同步与自动全片纠错需项目适配和实际视觉复核，没有以文档冒充实现。
