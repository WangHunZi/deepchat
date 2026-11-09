# 小智参考工程接入验证

本轮根据用户确认改为基于小智二开，接受 C++。所有下列编译与测试由独立测试子代理执行；没有使用此前未合并的自研 C 核心测试来证明新路线通过。

## 固定输入

- 小智：a73e9a7e266e3196d1368ba46c30bee0d81f0a64，项目版本 2.5.3，子模块 tracked 工作树无修改。
- 工具镜像：沿用 tools/container-lock.json 的公开 GHCR digest，未重建/发布。
- SDK：沿用 tools/sdk-lock.json 的 ESP-IDF v6.1 固定 commit；组件管理器报告 IDF 6.1.0。
- 业务依赖：真实解析 74 项，config/xiaozhi/dependencies.lock 为 34345 字节；SHA-256 为 ba75d4d8ab6f8b34852d18d2ab0f8dec3d5faeeab6f3ac8b81f62520a3cd2d4c。
- 平台：Linux amd64，Docker 29.9.2 / vfs。上游 main 实际最终标准选项为 -std=gnu++23；不能描述为自有 C11 核心或仅 C++17 调用检查。

## 实际命令及结果

| 命令 | 结果 |
| --- | --- |
| `python3 tools/dev.py --offline format --check` | 通过，9 个 Python 文件格式/lint 正确；不重排第三方源码 |
| `python3 tools/dev.py --offline test --suite tools` | 25/25 通过：原 19，加 6 个小智源码/依赖边界行为测试 |
| `python3 tools/dev.py --offline xiaozhi check` | 固定版本和 clean 源码检查通过 |
| `python3 tools/dev.py --jobs 4 xiaozhi build --profile reference-s3-lcd` | 在线真实解析/下载业务依赖，完成 2238 步完整参考构建，exit 0 |
| `python3 tools/dev.py --offline --jobs 4 xiaozhi build --profile reference-s3-lcd` | 完整缓存及固定依赖锁下禁网重建通过，exit 0 |
| `git diff --check` | 通过 |

六项新增测试覆盖：正确版本/clean 源码可用、修改保留并拒绝构建、错误版本拒绝且不 reset、未确认 XIAO profile 在构建前拒绝、缺失生成锁按固定字节恢复、不同的本地依赖锁保留并报告。
首次在线构建验证解析流程；随后将真实依赖锁纳入仓库，再验证禁网缓存重建和新增两项锁边界测试。最终两份锁逐字节一致。
SDK 和镜像 Python 包足以构建，未额外安装包或修改 SDK。只有上游 Kconfig 默认值/配置重命名等非阻断通知，没有失败或跳过的工具用例。

## 参考配置与产物

实际 sdkconfig 已确认：

- BOARD_TYPE_BREAD_COMPACT_WIFI_LCD=y。
- LCD_ST7789_240X240=y。
- ESPTOOLPY_FLASHSIZE_16MB=y，SPIRAM_MODE_OCT=y。
- WAKE_WORD_DISABLED=y，USE_AUDIO_PROCESSOR 未启用。

产物位于 build/container/xiaozhi-reference-s3-lcd/，所有者均为 agent:agent：

| 文件 | 字节 |
| --- | ---: |
| xiaozhi.bin | 2545776 |
| xiaozhi.elf | 30052536 |
| bootloader/bootloader.bin | 16736 |
| partition_table/partition-table.bin | 3072 |
| ota_data_initial.bin | 8192 |
| generated_assets.bin | 923405 |

应用分区剩余 38%。构建后第三方源码保持 clean；managed_components、生成锁和派生文件由上游忽略规则排除，不作为自有源码提交。

## 不能据此得出的结论

这是上游 breadboard 16 MB / Octal PSRAM / ST7789 240×240 的参考交叉编译，没有确认 XIAO Plus 的引脚、Flash/PSRAM 或器件接线，没有烧录。
尚未替换为 DeepSeek 娘素材、提供 240×240 图片预览、连接真实语音服务或进行实机显示/录音/播放验收。
未重新运行废弃路线的 C11 角色单元测试、C++17 API 测试或 pet-demo；这些代码没有进入新路线。
远端干净 CI 的状态以本 PR checks 为准，不把本地缓存构建冒充远端首次依赖下载验证。
