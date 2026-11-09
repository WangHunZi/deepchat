# 构建与开发入口

P0 提供可复现的 ESP32-S3 **构建基线**及主机检查。`bringup` 只输出启动信息，不驱动屏幕、麦克风、扬声器或按键，不代表已经适配 XIAO Plus。
角色、音频、联网、烧录与串口配置工具按 [Plan.md](../Plan.md) 后续阶段实现。

## 环境与固定版本

支持 Linux x86_64；macOS 使用相同入口但尚未验证，Windows 请使用 WSL2。预先安装 Git、Python 3.12（含 venv/pip）、主机 C/C++ 编译器。
Ubuntu 可安装 `git python3.12 python3.12-venv build-essential`；系统包由操作系统管理，不由项目脚本提权安装。
CI 使用 Ubuntu 24.04 和 Python 3.12.14。接受本机 Python 3.12 的其他补丁版，实际版本应记录在验证报告中。

| 工具 | 固定版本 / 来源 |
| --- | --- |
| ESP-IDF | `v6.1`，commit `fff9895c82d744c7237be8847347bdd1b07c6643` |
| Xtensa 编译器 | `esp-15.2.0_20251204`，GCC 15.2.0 |
| ROM ELF | `20241011` |
| CMake | `3.30.5`；满足 SDK 要求的 3.22 最低版本 |
| Ninja | `1.11.1.3` Python 包，实际 Ninja 1.11.1 |
| clang-format | `18.1.8` |
| Ruff | `0.11.13` |

版本记录在 [sdk-lock.json](../tools/sdk-lock.json)，主机工具在 [requirements-host.txt](../tools/requirements-host.txt)。
ESP-IDF Python 包及传递依赖完整固定在 [requirements-idf.txt](../tools/requirements-idf.txt)。
官方约束的本地快照见 [idf-constraints.txt](../tools/idf-constraints.txt)，仍由 SDK 的依赖检查器校验，不关闭 TLS、工具包校验或依赖约束。
SDK 的工具清单提供平台对应下载地址和 SHA-256；项目调用官方安装器，复用其校验结果。

SDK 与交叉工具分别安装到 `.sdk/esp-idf`、`.sdk/tools`，Python 工具安装到 `.venv`；均为本机生成且被忽略。
不需要 Docker、API Key、屏幕选型或实体设备即可完成 P0。不要提交本机环境、SDK、构建结果或凭据。

## 仅主机开发

在仓库根目录运行：

```sh
python3 tools/dev.py setup --host-only
python3 tools/dev.py format --check
python3 tools/dev.py test --suite tools
python3 tools/dev.py build --target host
```

`--host-only` 不下载 SDK；`build --target host` 通过 CMake 编译探测验证 C11 和 C++17 编译能力。
P0 尚无角色核心或公共 C API，因此没有 C11 业务单测或 C++17 API 调用套件；编译探测不算业务测试。
现在执行以下两条命令应因为没有相应用例而失败，不应以“0 tests passed”报告通过：

```sh
python3 tools/dev.py test --suite unit
python3 tools/dev.py test --suite c-api-compat
```

`tools` 套件验证开发工具的实际行为：下层失败退出码保留、零测试拒绝、格式化边界、未知板型拒绝、SDK 错误版本不被重置。
后续 P1 添加核心实现时，再接入真实 CTest 测试和 C++ 调用目标。

## 安装并编译固件

```sh
python3 tools/dev.py --jobs 4 setup
python3 tools/dev.py --jobs 4 build --target esp32s3 --board bringup
```

`--jobs` 是顶层参数，放在子命令之前；默认 4。工具脚本为每条命令设置环境，不需要手动 source 或改写全局 PATH。
`setup` 可重复执行，已安装的固定 Python 包和官方校验过的交叉工具可复用；不重置有本地改动的 SDK。
已有 `.sdk/esp-idf` 的提交不同或存在本地修改时，保留文件并报错，由开发者先处理该目录，不自动覆盖。
SDK 使用自身固定的 submodule revisions；安装失败后根据错误修复前置条件再重跑，不关闭签名、哈希或证书校验。

只安装当前实际使用的 Xtensa 与 ROM ELF 包，不提前安装 GDB、OpenOCD、ULP 或其他目标编译器。
P0 不启用 ULP；需要这些功能时按实际调用增加对应依赖。
SDK 的 Python 环境复用项目 `.venv`，官方 `check-python-dependencies` 仍使用本地约束快照运行。

产物在 `build/esp32s3-bringup/`：

- `deepchat.bin`、`deepchat.elf`、`deepchat.map`。
- `bootloader/bootloader.bin`、`partition_table/partition-table.bin`。
- `flasher_args.json`、`project_description.json`、`compile_commands.json`、`sdkconfig`。

Flash 大小、分区、UART 等使用 SDK 的保守默认值，不构成最终硬件配置。主应用显式使用 C11，SDK 自身保留上游编译约定。
不能将当前固件包作为已确认 XIAO Plus 引脚、Flash/PSRAM 的成品；`--board xiao-esp32s3-plus` 当前会明确拒绝。
P2 核对板级资料，P6 才提供统一烧录、完整交付包及实机验收。

## 格式与选中文件

```sh
python3 tools/dev.py format
python3 tools/dev.py format --check
python3 tools/dev.py format --check apps/esp32s3/main/Main.c tools/dev.py
```

默认检查 `apps/src/include/tests/tools` 下 Git 跟踪或未忽略的自有 C/C++/Python 源文件，不扫描 SDK、虚拟环境或生成目录。
显式文件参数也限制在这些自有目录；不要将依赖或生成物放进这些目录并要求批量格式化。
C/C++ 使用固定 clang-format；Python 使用 Ruff lint 和 format。lint 错误需要修改源码，不通过全局自动修复掩盖。
clang-format 不验证符号命名与中文 API 契约；这些内容依照 [STYLE_GUIDE.md](../STYLE_GUIDE.md) review。

## CI 与验证范围

[构建工作流](../.github/workflows/build.yml) 分别运行 host 与 firmware；两者调用相同的 `tools/dev.py`。
GitHub Actions 保留依赖安装/固件日志、版本清单及构建产物，尚未提供完整可烧录发布包。
CI 在没有实体板卡时不运行烧录、串口、屏幕或音频验收；通过 CI 只代表对应构建和开发工具检查完成。

本次实际验证结果和未运行项记录在 [P0 验证报告](P0_VALIDATION.md)。

## 更新依赖

正常 setup 只安装已提交的版本；不要在 CI 中自动更新。
更改 SDK 或工具版本需要独立 review，并重新构建验证。IDF Python 锁文件来自对应 SDK 的核心 requirements 与官方约束：

```sh
# 仅维护者显式更新时执行；uv 是锁文件生成工具，不是日常 setup 前置条件。
uv pip compile --python-version 3.12 --no-header --no-annotate \
  --constraint tools/idf-constraints.txt \
  .sdk/esp-idf/tools/requirements/requirements.core.txt \
  --output-file tools/requirements-idf.txt
```

参考：[官方 v6.1 发布](https://github.com/espressif/esp-idf/releases/tag/v6.1)、[ESP32-S3 入门](https://docs.espressif.com/projects/esp-idf/en/v6.1/esp32s3/get-started/index.html)、[约束文件来源](https://dl.espressif.com/dl/esp-idf/espidf.constraints.v6.1.txt)。
代码采用 [MIT](../LICENSE)，第三方依赖保留上游许可证，后续角色素材许可另行记录。
