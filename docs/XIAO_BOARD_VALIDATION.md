# XIAO Plus / ST7789 板级验证记录

2026-11-09，独立测试子代理在实现 commit `47f6420`、测试 commit `86469fd` 上验证。代码基线为已合并的 PR #8；本记录只说明软件构建、主机测试与文件收集结果，没有实机验收。

## 固定输入

- 工具镜像：`ghcr.io/wanghunzi/deepchat-dev@sha256:e5e714e2cc20857ed1808374d23fcc772ff9644f6b7aa2c8441aa6c1a4b74eae`。
- ESP-IDF：v6.1，commit `fff9895c82d744c7237be8847347bdd1b07c6643`；上游小智 commit `a73e9a7e266e3196d1368ba46c30bee0d81f0a64`。
- 使用现有已解析组件缓存，两份最终固件均通过 `--offline` 构建；没有重新解析或修改组件锁。
- 镜像内实测 `python -m esptool version` 为 **5.6.0**，与硬件文档本机安装版本一致。
- GPIO 分配和硬件来源见 [HARDWARE.md](HARDWARE.md)。资料核对、编译通过和实际接线工作分别记录，不把软件配置当作模块出厂接线。

## 执行结果

| 命令 / 检查 | 实际结果 |
| --- | --- |
| 锁定工具容器内 `python3 tools/dev.py --native format --check` | 通过；Ruff 检查及 14 个 Python 文件格式通过，自有 C/C++ 同入口通过 |
| `python3 tools/dev.py --offline test --suite tools` | 34/34 通过；新增 4 项测试覆盖模式拒绝、板级/角色补丁选择、profile 与测试配置变更隔离 |
| `python3 tools/dev.py --offline xiaozhi test` | 8/8 通过：原有 7 项真实 FSM/LVGL/GIF 行为，加 1 项实际测试图生成函数测试 |
| `python3 tools/dev.py --offline --jobs 4 xiaozhi build --profile xiao-esp32s3-plus-st7789 --display-test` | 最终 `.cpp` 版本 2237 步完整构建通过，返回码 0 |
| `python3 tools/dev.py --offline --jobs 4 xiaozhi build --profile xiao-esp32s3-plus-st7789 --pet --assets assets/generated/deepseek/assets.bin` | 2238 步完整构建通过，返回码 0 |
| CI 收集段本机执行 | 提取 workflow 原 Python 段，在同时映射两份真实最终构建目录的临时 workspace 执行；仅复制测试图 7 个文件，逐字节一致，相对路径保持，角色目录被排除 |
| `git -C third_party/xiaozhi-esp32 status --porcelain` / `git diff --check` | 子模块无源文件修改；差异空白检查通过 |

测试图测试覆盖五等宽 RGB565 色条的内部像素、四边一像素白框、四色角标及 SPI 高低字节顺序。它验证最终固件调用的函数，不验证物理色彩、SPI 波形或屏幕背光。

两个构建的 `compile_commands.json` 均恰好包含一次 `DCXiaoPlusBoard.cpp` 编译；各生成源文件与仓库生产文件逐字节相同。早期 `.cc` 版本的预编译结果未作为最终交付产物。

## 最终配置和产物

测试图目录：`build/container/xiaozhi-pet/4da40de1e657b8748ebb/build/`。
角色目录：`build/container/xiaozhi-pet/2249da59c7d4f27c6ca2/build/`。
目录由内容指纹生成；后续修改配置或源码时应使用命令实际打印的新目录。

两份 sdkconfig 均选中目标板、16 MB Flash、QIO、Octal PSRAM 80 MHz、USB Serial/JTAG 和默认 LCD 消息布局；分区为上游 `partitions/v2/16m.csv`。PSRAM 容量仍需启动日志验证，不以交叉编译声称探测到实物 8 MB。

测试图 `CONFIG_DC_DISPLAY_TEST=y`、`CONFIG_FLASH_NONE_ASSETS=y`；角色模式关闭测试图并启用 `CONFIG_FLASH_CUSTOM_ASSETS=y`。ESP-IDF 在选择 QIO 的同时生成启动烧录参数 DIO / 80 MHz / 16 MB；保留其 `flash_args`，不手动替换。

| 文件 | 测试图大小（B） | 角色大小（B） |
| --- | ---: | ---: |
| xiaozhi.bin | 1997968 | 2514944 |
| xiaozhi.elf | 25114660 | 29280976 |
| bootloader/bootloader.bin | 16784 | 16784 |
| partition_table/partition-table.bin | 3072 | 3072 |
| ota_data_initial.bin | 8192 | 8192 |
| configured_assets.bin | 不使用 | 1443207 |

测试图应用 SHA-256：`93a32c170ffd97cf8ea545cc9068a1003ac09372f6bf13f04930a9d9ff17f4c1`。
角色应用 SHA-256：`bda8b0a938ffa4fd761d92a7f765ac9b65e8c885354d27910065ac00ccded453`。
角色素材 SHA-256：`a6822c21a9409a21c2e762cfc4e45dd339c71ca3a38f4541ef50599244fb0378`；`input-assets.bin`、`configured_assets.bin` 与原本地生成包逐字节相同。

从最终 `flasher_args.json` 读取，测试图包含 bootloader、分区表、OTA 初值和应用四个烧录文件，另附 `flash_args`、`flasher_args.json`、`sdkconfig`，共 7 个交付文件。角色构建另含 `configured_assets.bin`。地址由构建元数据提供；具体烧录方式见硬件文档。

CI 新增两个目标模式编译；角色集成使用参考资源，独立 artifact 只收集测试模式，无 DeepSeek 角色图片。此处验证了收集脚本与真实文件，远端 GitHub Actions 的实际结论以 PR checks 为准。

## 限制和下一步

没有本次新增测试失败。构建仍会出现上游组件 Kconfig 旧式默认值/弃用和组件 include 依赖提示；离线组件管理器提示跳过 registry 变更检查，最终构建均成功。

无设备连接，未执行烧录、USB 枚举、Flash/PSRAM 探测、屏幕颜色/偏移/方向/刷新率、背光、电源、录音、扬声器或联网对话。BL 电路及扬声器负载仍待确认，不能由 GPIO 直接驱动未知背光负载。

按键已连接上游 StartListening/StopListening 事件，尚未验证完整 PTT；上游 Connecting 状态松开可能被忽略的边界已在硬件文档记录，留待实际音频/服务集成修复与验证。本次未重跑未修改的素材浏览器、历史 P0 或其他旧基线测试；没有新增 C API，不另造 C11/C++17 兼容占位测试。

下一步由实物测试者先按硬件文档运行独立测试图并记录正面照片、启动日志，再进入配网/角色和后续音频阶段。
