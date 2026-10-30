# 换电脑支持检查

记录日期：2026-10-30。只在独立仓库 `video` 中补充环境与接手支持，没有修改主制作工程或重算战斗。

已完成：

- `npm run setup`：建立独立 Python 3.12虚拟环境，固定六项核心依赖，恢复参考帧与压缩日志，不运行模拟。
- `npm run doctor`：10/10通过，包含 Git LFS、实际资源、C1检查点反序列化、Chrome与WebGL2。
- `npm run verify:runtime`：1,224名士兵和原生CastleExterior加载成功，没有页面异常或资源请求失败。已亲自查看实际2.3秒截图，蓝兵身体、U型布局与箭矢可见。
- `npm run battle:audit`：通过；前160状态数组一致，无死亡后放箭、非法近战命中、无效箭端命中或挥砍中换靶。
- `npm run build`：通过，仍有原有bundle体积提示。
- 编码使用的FFmpeg可执行文件和字体查找可用；本次没有启动完整视频重渲染。

验证环境：Windows，Node24.16.0，Python3.12.7，Chrome155.0.8059.80。macOS/Linux提供相应路径和启动支持，尚未在真实目标设备验证。

重要兼容发现：Playwright1.56配套Chromium141在这个项目中可加载页面，但蓝兵身体不显示；页面异常为空也无法证明画面正确。因此默认改为通过Playwright `chrome` channel自动查找当前稳定版Google Chrome，保留`VIDEO_CHROME`自定义入口。安装器不替换用户本机Chrome。旧Chromium141不作为本轮默认生产环境。

原生场景、灯光、固定镜头、军团布局、模拟参数和既有轨迹没有因换机支持改变。环境检查和单帧查看不代表续战完整视频已获视觉验收。
