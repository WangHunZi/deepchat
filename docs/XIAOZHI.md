# 小智二开接入与验收入口

用户已选择接受 C++，以小智为基础开发 DeepSeek 娘实体桌宠。已接入上游参考工程和角色素材转换，支持带素材的参考构建；角色界面及事件联动已完成；XIAO Plus / ST7789 已增加板级配置和独立测试图构建，实机仍待验收。

## 固定输入与复用点

- 上游：[78/xiaozhi-esp32](https://github.com/78/xiaozhi-esp32/tree/a73e9a7e266e3196d1368ba46c30bee0d81f0a64)，MIT。源码位于 third_party/xiaozhi-esp32，Git 子模块与 tools/xiaozhi-lock.json 固定同一 commit。
- SDK 和开发工具仍由 tools/sdk-lock.json、tools/container-lock.json 固定；没有更换工具镜像或 SDK。
- ESP32-S3 业务组件锁来自真实 resolver：config/xiaozhi/dependencies.lock。首次下载需要网络，之后组件缓存由上游组件管理器维护。
- 自有新增代码使用 Python 接入工具；实际产品沿用上游 C++ Application、AudioService、Display、板级机制和传输协议，不把上游重写为 C。
- 参考 profile：上游 bread-compact-wifi-lcd，ST7789 240×240、16 MB Flash、Octal PSRAM；这些是参考编译参数，不是 XIAO 硬件结论。
- 禁用唤醒词和音频预处理做首轮参考构建；最终按键、半双工、超时及取消行为仍需结合上游真实流程和器件验证。

关键源码入口（均在子模块内）：

| 路径 | 复用目的 |
| --- | --- |
| main/application.cc、main/device_state_machine.cc | 交互编排和状态；按实际差异修改，不并行建立另一套状态机 |
| main/audio/README.md、audio_service.cc、codecs/ | 录音、播放、编码/解码、输入引擎和音频并发组织 |
| main/display/、main/assets.cc | 显示、表情和资源加载 |
| main/boards/bread-compact-wifi-lcd/ | 参考 LCD 和简单 I²S 结构，不能照抄其引脚到 XIAO |
| main/boards/seeed/xiao-esp32s3-respeaker-xvf3800/ | 仅供 XIAO 系列组织方式参考；ReSpeaker XVF3800 与本项目音频器件不同 |
| main/protocols/、docs/websocket_zh.md、docs/mqtt-udp_zh.md | 使用现有通信协议，替代原计划的自研 HTTP/WAV |

## 获取与构建

```sh
# 新 clone 可用 git clone --recurse-submodules；已有 checkout 用：
git submodule update --init --depth 1
python3 tools/dev.py setup
python3 tools/dev.py --offline xiaozhi check
python3 tools/dev.py --jobs 4 xiaozhi build --profile reference-s3-lcd
```

最后一条使用锁定工具镜像、SDK 与组件锁执行真实 idf.py build。首次不要加 --offline，否则组件下载会失败。
输出位于 build/container/xiaozhi-reference-s3-lcd/，上游 managed_components 和生成文件位于子模块忽略目录中。
参考应用不能作为 XIAO 可直接烧录交付。目标板使用单独的 `xiao-esp32s3-plus-st7789` profile，必须选择 `--display-test` 或 `--pet --assets ...`，接线与烧录见 [硬件说明](HARDWARE.md)。它沿用上游网络服务发现默认值，最终固件的服务端和设置需另行确认。

源码检查会拒绝不同 commit、已修改或未跟踪的源文件；不会 reset/覆盖源码。
构建前将跟踪的组件锁复制到上游忽略的 dependencies.lock；若现有锁内容不同会报告并保留，先自行备份再恢复需要的锁。
组件下载与完整性校验由 ESP-IDF 组件管理器负责，不再自研一套下载/成功确认机制。

## 怎么查看效果对不对

参考构建能验证固定源码版本、组件可解析、参考配置与编译产物。目标板新增独立测试图与角色构建，实际结果见 [板级验证记录](XIAO_BOARD_VALIDATION.md)。它不提供“文字状态模拟代替角色画面”的演示，也不能证明屏幕、麦克风或扬声器正常。

现在可以先看源素材：

```sh
python3 tools/collect_assets.py
python3 tools/collect_assets.py --check
```

打开 assets/local/codex-pet/previews/contact-sheet.png 查看全身动作，或 assets/local/emotes/previews/thinking.gif 比较大头表情。它们仍是原始素材，尚非 240×240 成品。

P2 已实现 240×240 预览，用同一套最终 GIF 和时长切换六动作，支持暂停/逐帧。生成与人工检查见 [素材说明](ASSETS.md)。说话尚为占位；预览只包含素材，不含固件顶栏/文字叠层。
之后硬件到货，再核对实屏色彩、方向、SPI 刷新、音频与网络并行情况。浏览器预览、交叉编译、真实服务和实机分别记录结果。

上游已有素材工具路线可复用：main/idf_component.yml 声明 image_player 和 esp_emote_expression；后者文档提供 [资源生成工具](https://gfx-gen-tool.pages.dev/) 及本地打包入口，image_player 已有 GIF 转换脚本。先做一段角色素材的最小验证，再固定适合的资源格式，避免重复编写播放器。
当前素材链已选用上游 LCD 现有 GIF 解码与 mmap 打包函数，不需要在线上传素材。image_player/emote 保留为可选能力，不同时引入第二个设备播放器。

## 许可与更新

保留子模块 LICENSE、上游命名和第三方组件许可；本项目自有 MIT 不替代各组件和角色素材的许可。
DeepSeek 娘来源锁、原作者及 EmoteLab 声明见 assets/README.md。
固定上游源码不是固定所有硬件和服务行为；更新上游/组件/素材时按功能 PR review，并回归目标板。
详细阶段见 Plan.md；实际编译与测试结果见 XIAOZHI_VALIDATION.md。
