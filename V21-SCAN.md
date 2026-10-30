# V21 文件归属与资源扫描

| 责任 | 文件 | 状态 |
|---|---|---|
| 红方运动与局部响应 | `tools/motion_v21.py`, `tools/local_response_v21.py` | 已新增并接入 V21 构建 |
| 蓝方部署与射击 | `tools/archers_v21.py`, `tools/build_simulation_v21.py` | 已新增，保持 12 列 blue-control |
| 数据构建 | `tools/build_simulation_v21.py` | 已生成 `variants/V21` |
| 相机 | `src/main-camera.js`, `src/camera-v19.js` | 相机参数沿用 V19-B 基准 |
| 正式场景 | `src/environment-v21.js` | 已接入 UnityPackage 选择性转换 |
| 角色实例化渲染 | `src/assets-v17.js` | 保留 V18/V19 独立相位接口 |
| 验收 | `tools/validate_v21.py`, `tools/test_archers_v21.py`, `tools/test_local_response_v21.py` | 只读/单元测试通过 |

## UnityPackage 映射

来源包：`C:/Users/89trillion/Documents/WXWork/1688855976628529/Cache/File/2026-10/PVE混剪.unitypackage`

| 策划/Unity 资源 | Web 运行时资源 | 用途 |
|---|---|---|
| `New Scene.unity` | `assets/imported/Assets/New Scene.unity` | 场景布局参考 |
| `ArenaScene_Land.fbx` + `ArenaScene_Land_C.png` | 同路径 | 主棋盘地面 |
| `ArenaScene_HighWalls.fbx` + `ArenaScene_LowWall_C.png` | 同路径 | 远景边缘墙体 |
| `ArenaScene_Flag.fbx` + `ArenaScene_Castle_C.png` | 同路径 | 远景旗帜 |
| `CastleExterior_Building.fbx` + `CastleExterior_Castle_C.png` | 同路径 | 远景城墙/城门 |
| `CastleExterior_Tree_04.fbx` + `CastleExterior_Tree_C.png` | 同路径 | 非交战区装饰 |

Unity 专用场景不能直接由 Three.js 加载，因此 V21 使用 FBX/PNG 对的兼容转换，保留原始路径、颜色与比例约束；没有把截图当作地面贴图。
