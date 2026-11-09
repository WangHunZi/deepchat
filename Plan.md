# DeepChat 实体桌宠实施计划

## 当前决策与交接起点

用户已选择：允许 C++，优先基于 MIT 的 [小智 ESP32](https://github.com/78/xiaozhi-esp32) 二开，减少从零实现。
本计划取代此前“独立 C11 状态机 + 自研 HTTP/WAV 后端”的实施路线；历史 P0 和素材收集结果保留。

产品仍是 DeepSeek 娘实体桌宠：240×240 ST7789 SPI 小屏常驻角色、按键语音交互、表情反馈。先实现单设备 USB 供电，沿用上游现成语音/显示/传输能力。
首次目标是可接线、可配置、可烧录并能看到角色的固件；参考构建通过不等于目标硬件适配完成。

已合并：PR #1 规范、#2 P0 基线、#3 Docker 开发镜像、#4 发布镜像 digest 锁定、#5 DeepSeek 娘素材来源与本地收集。
小智基础工程 PR #6 已合并；素材与预览 PR #7 已合并；PR #8 角色界面与真实事件联动已合并；本轮接入 XIAO Plus / ST7789 板级配置、独立测试图和角色构建，待本功能 PR review。实际结果见 docs/ROLE_UI_VALIDATION.md。
原自行实现的角色核心停留在本地 `feat/pet-state-animation`，未推送或提交 PR，不作为新路线的依赖。

## 1. 复用与自有代码的边界

- `third_party/xiaozhi-esp32` 使用 Git submodule 固定 commit，版本另见 `tools/xiaozhi-lock.json`；保留上游许可、命名和实现语言。
- 复用上游 Application、AudioService、Display、板级机制、设置、OTA/服务发现和通信协议。不再并行建设第二套通用状态机、音频流水线、设备动画播放器或 HTTP/WAV 后端。
- 自有改动集中在 XIAO 板级适配、DeepSeek 娘素材与角色界面、必要配置及验收工具。确有行为差异时在对应调用点做薄修改并测试，不另包一套框架。
- 上游更新需要独立 PR，说明版本、依赖和板级/素材回归结果；不自动跟随 main。
- 组件版本使用真实 resolver 生成的 `config/xiaozhi/dependencies.lock` 固定；沿用已发布 Docker 工具镜像及 `tools/sdk-lock.json`。
- Python 工具维持现有风格；新 C++ 可接受。上游不强行改为 DC 命名或 C11。自有接口与注释遵循 STYLE_GUIDE.md 的更新说明。
- 来源、许可和固件打包分开记录：自有代码 MIT 不自动授予第三方角色图像许可。

## 2. 已知硬件与尚未确认的部分

| 部件 | 用户提出的型号 / 计划 | 必须确认 |
| --- | --- | --- |
| 主控 | Seeed Studio XIAO ESP32S3 Plus | 已核对官方 Plus：16 MB Flash、8 MB Octal PSRAM；实物版本待验收 |
| 麦克风 | INMP441 | 引脚、供电、L/R 声道、I²S 位宽与实际录音幅度 |
| 功放 / 扬声器 | MAX98357A，扬声器未定 | 供电、增益、阻抗和功率、音量 |
| 屏幕 | 用户确认 ST7789、SPI、240×240；照片 TK013F0320 | 排针已确认；初始 SPI/方向/色序参数待实测，BL 电路待模块资料 |
| 操作 | 按键按住说话，USB 供电 | 独立按键 GPIO 与电平；不得直接沿用参考板 BOOT 接线 |

上游存在 `xiao-esp32s3-respeaker-xvf3800`，它使用 ReSpeaker XVF3800，不能等同于本项目的 INMP441 + MAX98357A。
保留 `bread-compact-wifi-lcd` 的 240×240 配置做参考编译；其 Flash/PSRAM 和 GPIO 仅属于上游参考板，不能照搬为 XIAO 接线。
硬件资料未齐不阻塞源码接入、素材处理、协议研究和主机预览；会阻塞最终引脚定版及实机结论。

## 3. 分阶段交付

每阶段是功能边界，不是固定 PR 或 commit 数；每份 PR 可含多个可读 commit，由用户 review 决定 merge。

### P0：历史构建基线（已合并）

- 保留根 CMake 的 C11/C++17 工具探测与 `apps/esp32s3` 无外设 bringup，作为历史环境基线。
- 工具环境使用固定公开 GHCR digest。小智业务依赖不预装在工具镜像，首次参考构建需要在线下载。
- 历史证据见 docs/P0_VALIDATION.md、docs/DOCKER_VALIDATION.md、docs/IMAGE_PIN_VALIDATION.md；不能拿这些结果声称小智或最终板级已验证。

### P1：固定上游与参考构建（PR #6 已合并）

- [x] 固定小智上游 commit，保留完整 MIT 来源。
- [x] 接入统一 dev.py 命令，检查源码版本及本地修改，不 reset 开发者修改。
- [x] 选上游 ESP32-S3 LCD 240×240 参考配置，明确不是 XIAO 可烧录交付。
- [x] 从真实解析结果记录业务组件版本与哈希锁，不凭空填写版本。
- [x] 独立测试子代理完成格式、25 项工具测试、参考配置检查、2238 步完整编译及缓存禁网重建，见 docs/XIAOZHI_VALIDATION.md。
- [x] CI 已配置从同一工具镜像和依赖锁构建参考工程；远端执行结果见 PR checks，不自动发布或 flash。

交付：可复现的小智源码和参考构建入口、验证报告。下一份 PR 以此为基础推进角色素材，不恢复旧的自研核心路径。

### P2：DeepSeek 娘素材与 240×240 预览

- [x] 来源与本地收集：两组固定来源、逐文件 SHA-256、许可记录，见 assets/README.md（PR #5）。
- [x] 复用上游 GIF 解码与 mmap 资源打包链，支持已有 FLASH_CUSTOM_ASSETS 构建路径，没有新建资源格式或设备播放器。
- [x] 选定 Codex Pet 同一画风，五段动画映射六动作；说话明确待机占位，没有嘴型。P3 当前实现已接入真实事件；实机待验证。
- [x] 用透明 WebP 消除原 GIF 绿边，统一全局锚点与 240×240 画布；保留原时长参考，10 fps 上限采样。
- [x] 提供单 HTML/本机 HTTP 预览，支持切换、暂停、逐帧、拖动和比例；最终 GIF 的 30 帧经上游原解码器逐像素/时长验证。
- [x] 记录转换、颜色及预算：最终包 1443207 B；11 个素材测试、25 个工具测试、带素材参考构建与浏览器桌面/手机验证通过。
- [x] 原图和生成角色包留在忽略目录；保留来源/许可，CI 使用原创几何 fixtures，不上传第三方角色图像。

验收：用户能直观看到 240×240 的角色大小、表情和动作，并能按场景切换。预览不等于实机刷新率、色彩或音频验证。

### P3：角色界面、XIAO 板级适配和本地硬件

- [x] 角色主界面隐藏遮挡父层，诊断场景恢复；复用原字幕偏好和低电量弹层。
- [x] 连接小智真实状态、手动停止、TTS stop 与 AudioService 排空事件；情绪播放后复用原每秒刷新恢复待机。
- [x] 补丁和自有头文件在隔离生成源构建，原子准备与依赖锁指纹有测试；不修改原上游子模块。
- [x] 主机验证复用真实状态机、LVGL、GIF 播放器，参考构建与限制见 docs/ROLE_UI_VALIDATION.md。

- [x] 编写 docs/HARDWARE.md，按官方 Plus 资料分配焊盘/GPIO、SPI 与独立 I²S；屏幕 BL、功放负载/供电仍待资料，未作实机确认。
- [x] 通过 Kconfig/CMake 板级扩展接入 Plus，复用 LCD、简单 I²S 和 Button；以隔离补丁/叠加文件管理，未修改上游 tracked 源码。
- [x] 按官方规格固定 16 MB Flash / Octal PSRAM；开放显式测试图或带素材角色 profile。产物仅代表目标板构建通过，实物待验收。
- [ ] 按顺序验证：测试图 → 角色待机 → 固定音频 → 录音回放 → 按键互动。
- [ ] 检查麦克风声道、16/32-bit 采样转换、扬声器音量和显示并行工作。复用 SDK 成功合同，正常处理错误，不逐层读回确认。

验收：同型号实物上角色和音频正常；无设备时只记录构建与资料核对结果。

### P4：服务端协议与 DeepSeek 对话

- [ ] 优先沿用小智现有协议及可自托管的兼容服务端，比较中文 ASR、DeepSeek 接入和 TTS 音色，选择一个清晰路径。
- [ ] 单独核对所选服务端的许可、依赖及部署方式，不把其源码自动纳入本项目 MIT。
- [ ] 固定真实供应商配置；用户在本地或环境配置中提供凭据，不入库、不打印。不为首版增加多供应商自动切换。
- [ ] 先运行兼容服务端的示例/集成测试，再用设备验证；mock、真实服务和实机分别报告。
- [ ] 按用户希望的按住说话交互核对上游实际行为。超时、录音限制、忙时按键和取消等差异有实际证据后再在对应模块修改，不另建平行状态机。
- [ ] 核对角色 happy/confused 等动作与真实服务事件映射；不存在准确口型时只展示说话动画。

电脑上的服务端需保持运行；脱离电脑需要用户另选常驻服务部署。本任务不擅自创建账号、连接付费服务、发布环境或部署服务器。

### P5：烧录交付与实机验收

- [ ] 固定目标板和完整素材，提供包生成与端口选择方式；地址从上游构建元数据获取，不硬写猜测偏移。
- [ ] 包含上游/本项目版本、依赖锁、板级配置、bootloader、分区、应用、所需素材、校验清单和已知限制。
- [ ] 提供首次烧录、配置、服务端启动、恢复与串口排错说明，不默认擦除整个 Flash。
- [ ] 实测 30 分钟待机、10 轮对话、断网和下一次操作恢复；记录延迟、内存、音频与画面表现。
- [ ] 用户或硬件测试者验收同型号器件，完成后才能标注“可以烧录使用”。

### P6：后续增强

真实 Token 用量/余额、触摸、唤醒词、打断播放、全双工、长期记忆、电池、OTA 等按实际需求独立推进。上游已存在能力可复用，但首版不要求全部启用。
模型用量和费用使用供应商真实字段，未知显示未知，不以进程内计数冒充账户账单。

## 4. 当前命令及看效果的方法

```sh
git submodule update --init --depth 1
python3 tools/dev.py setup
python3 tools/dev.py --offline format --check
python3 tools/dev.py --offline test --suite tools
python3 tools/dev.py --offline xiaozhi check
# 首次业务依赖下载需要网络；不是最终目标板固件：
python3 tools/dev.py --jobs 4 xiaozhi build --profile reference-s3-lcd
python3 tools/collect_assets.py --pack codex-pet
python3 tools/dev.py assets setup
python3 tools/dev.py --offline assets build
python3 tools/dev.py --offline assets check
python3 tools/dev.py preview
python3 tools/dev.py --offline xiaozhi test
python3 tools/dev.py --offline --jobs 4 xiaozhi build --profile reference-s3-lcd --pet --assets assets/generated/deepseek/assets.bin
# 目标板首次点屏，不启动音频或网络：
python3 tools/dev.py --jobs 4 xiaozhi build --profile xiao-esp32s3-plus-st7789 --display-test
# 测试图验收后，目标板角色固件（正常小智应用，需要配网/服务）：
python3 tools/dev.py --offline --jobs 4 xiaozhi build --profile xiao-esp32s3-plus-st7789 --pet --assets assets/generated/deepseek/assets.bin
```

接线、下载 CI 测试图固件、烧录和肉眼验收见 docs/HARDWARE.md；测试结果见 docs/XIAO_BOARD_VALIDATION.md。

旧 `build --target esp32s3 --board bringup` 仍是历史最小应用；它不构建小智。
根 CMake 尚无新路线的自有角色单元测试；unit/c-api-compat 的零测试仍应失败，不能伪称角色验证通过。
旧本地分支的 `pet-demo` 没有并入新路线，不是当前可用命令。

当前可生成 240×240 素材预览：assets setup → assets build → assets check → preview，详见 docs/ASSETS.md。素材画面验证不包含固件顶栏/聊天文字叠层、物理屏幕或音频。
详细命令、上游资源工具入口和人工验收路径见 docs/XIAOZHI.md。

## 5. 评审、提交与后续 AI

- 遵循 Rules.md 的四条约束：信任所选库成功契约、新机制有实际调用点、校验在明确边界、测试需求而非多余设计。
- commit 按可解释步骤组织，PR 按完整功能或可独立验证的子功能组织。一个功能可以多份 PR，一份 PR 可以多个 commit；不一 commit 一 PR。
- 编译与测试交给独立测试子代理，报告命令、数量、通过/失败/跳过/未运行原因；上游测试和自有工具测试分别说明。
- 每份 PR 说明基线、依赖、commit 阅读顺序、实际验证、未验证硬件与服务；用户决定 merge。未经新授权不自动 merge 或发布镜像/环境。
- 使用当前 checkout，除非用户要求不创建额外 worktree。上游修改以可审核文件/补丁管理，保持原作者与许可；不改写已审阅历史。
- 后续 AI 先核对本轮板级 PR 状态与 docs/XIAO_BOARD_VALIDATION.md，等待测试图实屏验收、确认 BL 和扬声器资料，再推进音频/服务联调。连接中松开按键会被上游忽略，完整 PTT 验收前应修复此已知边界。不要重新实现废弃的 HTTP/WAV 服务或 C11 角色核心。


## 6. 本轮板级交接

| 项目 | 本轮交付 / 下一步 |
| --- | --- |
| 目标硬件 | 用户确认 Plus + ST7789 240×240；按官方 Plus 资料分配 GPIO，详见 docs/HARDWARE.md |
| 构建入口 | 目标 profile 显式选择测试图或带素材角色；测试图停止于音频/网络初始化之前 |
| 固件获取 | CI 仅分发测试图烧录文件；角色素材仍在本地，使用本次构建 flash_args 烧录 |
| 独立验证 | 命令、数量、最终源码指纹、产物及失败/未运行项见 docs/XIAO_BOARD_VALIDATION.md |
| 硬件待办 | 确认 BL 电路、实物版本、扬声器/功放资料；用户先验收测试图，暂未实机通过 |
| 下一实现 | 音频独立验收、连接中松开按键边界修复，然后服务端选择与真实对话 |
| Review | 本功能按板级实现、行为验证与文档/CI 分组 commit；用户决定 merge，不自动合并 |
