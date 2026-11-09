# P0 本地验证报告

日期：2026-11-09。执行者：独立测试代理；目标：开发工具与 ESP32-S3 `bringup` 构建基线。
环境：Linux x86_64，Python 3.12.14，主机 GCC/G++ 14.2.0。准确 SDK 与项目工具版本见 [版本锁](../tools/sdk-lock.json)。
本报告记录本地验证，GitHub Actions 运行状态以对应 PR 的 checks 为准。

## 已完成检查

所有命令均在仓库根目录执行；安装与测试保留底层进程退出状态，没有通过管道吞掉错误。

| 命令 / 检查 | 结果 | 说明 |
| --- | --- | --- |
| `python3 tools/dev.py setup` | exit 0 | 官方工具包 SHA-256 校验保留，SDK Python 依赖检查通过 |
| 同一 setup 再次执行 | exit 0 | 复用现有 SDK、固定包与交叉工具，没有重置 SDK |
| `.venv/bin/python -m pip check` | exit 0 | 无损坏或冲突的 Python requirements |
| `python3 tools/dev.py format` | exit 0 | 对自有 C/Python 应用格式，已修正导入排序 |
| `python3 tools/dev.py format --check` | exit 0 | clang-format 18.1.8 可解析配置，后续检查无格式差异，中文注释保留 |
| `python3 tools/dev.py test --suite tools` | 6/6 通过 | 开发命令行为测试，非硬件或角色功能测试 |
| `python3 tools/dev.py build --target host` | exit 0 | C11 和 C++17 分别编译探测成功，不计为公共 API 业务测试 |
| `python3 tools/dev.py --jobs 4 build --target esp32s3 --board bringup` | exit 0 | ESP-IDF v6.1、Xtensa GCC 15.2.0；实际命令 `ninja -j 4 all` |
| 上述固件构建的增量重跑 | exit 0 | 可以复用有效产物 |

应用的 `compile_commands.json` 已检查：SDK 添加 GNU23 选项后，应用最后一个标准选项为 `-std=c11`。
`Main.c` 的 `_Static_assert(__STDC_VERSION__ == 201112L)` 同时在实际编译中生效。
SDK 其他组件保留上游标准；不把主机 C++17 编译探测写成已有公共 C API 兼容套件通过。

6 个开发工具行为用例覆盖：下层退出码保留、零测试拒绝、目录与外部文件格式化拒绝、选中自有文件、未确认板型拒绝、错误 SDK revision 不被重置。

## 预期拒绝及未运行项

| 检查 | 结果 | 原因 |
| --- | --- | --- |
| `python3 tools/dev.py test --suite unit` | exit 8，No tests were found | P1 尚未添加 C11 业务单测，不算通过 |
| `python3 tools/dev.py test --suite c-api-compat` | exit 8，No tests were found | 尚无公共 API 与 C++17 调用套件，不算通过 |
| clang-tidy | 未运行 | 规范中为建议性检查，本次未安装 clang-tidy |
| GitHub Actions | 本报告未代替远端结果 | 工作流随 PR 提交，见 PR checks |
| 从第二台干净机器完整安装 | 未运行 | 当前实例安装及重复安装已验证，未声称新机器恢复验证完成 |
| 串口启动输出、屏幕、录音、播放、烧录 | 未运行 | 云环境没有实际板卡，P0 不包含外设实现 |

## 构建产物

本次本地生成的产物位于 `build/esp32s3-bringup/`，被 Git 忽略：

- `deepchat.bin`：170,112 bytes。
- `bootloader/bootloader.bin`：21,120 bytes。
- `partition_table/partition-table.bin`：3,072 bytes。
- 同时生成 ELF、map、`flasher_args.json`、`project_description.json`、编译数据库和 SDK 配置。

源码 revision 和开发状态会影响固件内版本信息；CI 将从 PR 的实际提交重新构建，最终以当次构建产物为准。
这些是构建产物，不是已完成板级确认、素材打包与实机验收的发布包。

## 实际发现与修复

- 首次格式检查指出 Python import 顺序问题，已按 Ruff 修正并通过检查。
- ESP-IDF 6.1 组件管理器需要 `ESP_IDF_VERSION`；入口补齐官方导出变量后构建恢复。
- SDK 直接调用 Ninja，需要 `IDF_PY_BUILD_JOBS` 才能让 `--jobs` 生效；已由实际 `ninja -j 4` 确认。
- 仅设置 CMake `C_STANDARD` 会被 SDK 的 GNU23 目录选项覆盖；应用组件追加 C11 选项并加编译期断言后通过。

下一阶段为 P1 角色状态、素材转换与预览；板级配置仍在 P2 等待具体器件资料。
