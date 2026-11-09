# Docker 开发环境验证

历史报告：对应 PR #3 的候选镜像构建阶段。首次发布现已完成，最新拉取与锁定结果见 [已发布镜像验证](IMAGE_PIN_VALIDATION.md)。

日期：2026-11-09。执行者：独立测试代理。目标：以实际 Docker 镜像替代宿主机工具链，验证相同源码的容器构建入口。
环境：受管 Linux x86_64，Docker 29.9.2，rootless daemon / VFS 存储。远端 CI 结果以本 PR checks 为准，不以本地结果代替。

## 镜像与工具

- 官方基础镜像：`python:3.12.14-bookworm@sha256:c90be507635af19768837aa7eeb2f4ce89a74d62962a335497b9df8edfb7f19d`，具体 Linux amd64 manifest。
- 镜像内 Python 3.12.14、Git 2.39.5、GCC/G++ 12.2.0、Make 4.3，未使用宿主机 GCC/G++ 14.2.0。
- ESP-IDF v6.1、Xtensa GCC 15.2.0、CMake、Ninja、clang-format、Ruff 及 Python 依赖沿用固定版本锁。
- 本轮候选内容 ID：`sha256:85b7330d6474069262ebe09df5edbd33801c0156a2d0e4152360456a0fe24889`。
- 本轮安装输入指纹：`0845d15310edb1b445faf20fdd1610ac6a701d74e29b2b846d5f26ca4a2604cd`。

本地内容 ID 不能当作可从 GHCR 拉取的 registry digest。首次自有镜像尚未发布，tracked lock 的 `image` 保持 `null`，不会填写虚构发布摘要。

## 真实执行结果

以下命令通过公共入口执行；日志保留下层进程的真实退出状态：

| 命令 | 结果 | 证据范围 |
| --- | --- | --- |
| `python3 tools/dev.py image build` | exit 0 | BuildKit 真实安装固定工具链，官方校验与 SDK Python 约束检查通过 |
| `python3 tools/dev.py --offline format --check` | exit 0 | 实际容器内运行格式 / lint，配置可解析 |
| `python3 tools/dev.py --offline test --suite tools` | 15/15 通过 | 原 native 行为、Docker 边界、digest/pin 和可见错误诊断 |
| `python3 tools/dev.py --offline build --target host` | exit 0 | 镜像 GCC/G++ 的 C11 / C++17 编译探测分别成功 |
| `python3 tools/dev.py --offline --jobs 4 build --target esp32s3 --board bringup` | exit 0 | 真实 Xtensa 编译，工具路径来自 `/opt/deepchat` |
| `python3 tools/dev.py --offline test --suite unit` | exit 8，预期无用例 | 不算 C11 业务测试通过 |
| `python3 tools/dev.py --offline test --suite c-api-compat` | exit 8，预期无用例 | 不算公共 API 调用测试通过 |

上述运行命令均以 `--network none` 进入容器；网络仅用于准备镜像时的真实下载，日常构建未临时下载依赖。
`build/container/host`、`build/container/esp32s3-bringup` 与原 native 缓存隔离；最终 `Main.c` 的标准选项为 `-std=c11`，且编译期断言参与编译。

产物：应用 BIN 170,112 bytes，bootloader 21,120 bytes，分区表 3,072 bytes，并生成 ELF/map、flash 配置及编译数据库。
实测宿主机所有者均为调用者 `1000:1000`，可以继续读取和修改。不同源码 revision 的版本字符串可能影响最终产物，以当次构建为准。

## 回归测试与实际修复

15 个工具测试包括原有 6 个行为用例及 9 个容器相关用例，验证：

- 缺少选择、移动 tag、无效 digest、安装配方变化均明确失败。
- 只挂载 checkout，不额外挂载 Docker socket、宿主机 SDK 或 venv；工具实际从镜像读取。
- 运行使用调用者 UID/GID，源路径只允许当前 checkout，绝对路径正确映射。
- Docker 失败退出码原样保留；Git 的被捕获 stderr 不再被静默丢弃。
- registry 镜像配方不匹配时，不覆盖旧选择；成功 pin 更新实际 digest 与 tracked lock。

曾尝试按 rootless 标签选择容器 UID 0，但该环境的挂载仍保留 owner 1000，Git 明确拒绝 ownership。已按实测删除该推断分支，保留调用者身份；没有放宽 workspace 的 Git 检查或 chown 文件。
镜像 SDK 的固定路径使用单独的 safe.directory 设置，因为 SDK 由镜像构建时的用户安装，运行时只读使用。

构建代理 CA 使用临时 BuildKit secret，镜像运行时有需要再只读挂载；不将会话证书或 credential 文件 COPY 到镜像。
`.dockerignore` 白名单只传入安装脚本和版本输入，不传入业务应用源码、宿主机 .sdk/.venv 或本地配置。

## 未执行与边界

- 自有 registry 镜像实际发布、GHCR package 可见性、首次发布 digest 锁定：未执行。工作流仅允许审核后的 main 手动触发，见 [发布流程](DOCKER_RELEASE.md)。
- registry pull / pin 的网络发布链路：用例验证了 Docker 边界与锁文件行为；尚无自有发布镜像可做端到端 registry 联调。
- macOS、Windows Docker Desktop、ARM64 / amd64 模拟、其他 rootless 映射方案：未验证。
- 设备烧录、串口启动、屏幕和音频：未运行，仍属后续板级和实机阶段。

首次发布和 pin 合并后，本地与 CI 将拉取完全相同的自有 registry digest；当前阶段提供可 review 的候选构建及完整发布路径。
