# DeepSeek 娘素材收集验证

本轮仅交付原始素材的可复现本地收集，属于 P1 前置功能；不交付动画核心、RGB565 转换、浏览器预览或实机固件。
来源与使用方式见 [素材说明](../assets/README.md)。编译与测试按项目规范交给独立测试子代理执行。

## 实际结果

环境：Linux amd64，Docker 29.9.2 / vfs；沿用已发布的 `tools/container-lock.json` 镜像，无 SDK、依赖或镜像配方变更。

| 命令 / 检查 | 结果 |
| --- | --- |
| `python3 tools/dev.py --offline format --check` | 通过，7 个 Python 文件格式正确，lint 通过 |
| `python3 tools/dev.py --offline test --suite tools` | 19 个通过：原有 15 个，新增素材收集行为 4 个 |
| `python3 tools/collect_assets.py --check` | 8 个本地原始文件长度和 SHA-256 全部通过，离线检查 |
| `python3 tools/collect_assets.py` | 复用并核验已有 8 个文件 |
| `python3 tools/collect_assets.py --pack codex-pet --check` | 4 个文件通过 |
| `python3 tools/collect_assets.py --pack emotes --check` | 4 个文件通过 |
| 临时目录调用 `collect_pack` 下载 Codex Pet 的 `pet.json`、`README.md`，再以 `check=True` 检查 | 2 个真实固定 URL 下载及后续离线检查通过，未改动原始本地素材 |
| `git check-ignore assets/local/codex-pet/spritesheet.webp` | 原图目录被忽略 |
| `git diff --check` | 通过 |

新增测试验证：下载后字节不变；已有文件复用及离线检查不访问网络；长度或摘要不符的下载不落盘；离线缺文件报告失败；本地修改保留并报告。
其中长度和摘要两种损坏输入在同一个测试内分别运行，不另增测试数量。
Docker 检查首次启动约 45 秒，最终均以 0 退出；无失败或跳过用例。

本地已收集的 8 个文件共 14,175,687 字节；来源锁包含两组固定 commit、逐文件长度、SHA-256、来源与许可状态。
原始图片和上游 README 快照位于 `assets/local/`，不进入 Git；公开 CI 无需下载这些第三方素材即可执行 19 个工具测试。

## 未运行与后续

- 本轮未重跑主机 C11/C++17 编译和 ESP32-S3 交叉编译：没有修改 C 源码、公共头文件、构建系统或工具链；远端已有 CI 仍按完整基线执行。
- 未运行新图生成或 GIF 生成：当前生图工具没有直接 GIF 输出接口，本轮复用现有源素材。
- 未下载完整 161 个 GIF，未完成六类动作映射、嘴型、尺寸转换或帧时序适配。
- 未进行实机显示、Flash 空间或刷新率测试；原始 GIF/WebP 不代表 ESP32 可直接播放。
- 后续首先实现 P1 的 C11 状态与动画时序核心，再接本地素材转换和 240×240 预览；素材公开再分发许可与代码 MIT 分开记录。
