# 连接过程中松开 PTT 的验证记录

2026-11-10，由独立测试子代理执行。生产实现 commit 为 `1dbf497`、测试 commit 为 `e08f732`，基于 PR #9 的 `256a73c`；本报告记录当前实现的主机回归和 XIAO 角色固件编译，没有实机结果。

## 固定输入与测试边界

- 小智源码固定为 `a73e9a7e266e3196d1368ba46c30bee0d81f0a64`；在生成源依次应用 pet-ui.patch、manual-listening.patch 与目标板补丁，原子模块 tracked 工作树保持 clean。
- 工具镜像：`ghcr.io/wanghunzi/deepchat-dev@sha256:e5e714e2cc20857ed1808374d23fcc772ff9644f6b7aa2c8441aa6c1a4b74eae`。
- ESP-IDF v6.1，commit `fff9895c82d744c7237be8847347bdd1b07c6643`；业务组件锁不变，使用既有缓存离线构建。实际应用编译选项最后为 GNU++23。
- PTT 测试直接包含真实生成 application.h，编译从同一生成 application.cc 原文提取的完整 Run、Start/Stop、状态处理器、连接、录音启动、调度、重置、自动/唤醒调用等方法，链接真实 DeviceStateMachine 与 DCPetPresentation。
- 构造和硬件/网络端口由主机替身提供；两个协议回调的注册语句原文提取，其余 OTA/JSON 初始化不在主机测试内。没有复制业务状态机、改写方法体或断言新增原子请求字段。
- FreeRTOS 事件端口保留事件位 OR 合并和取出清位的语义；阻塞连接替身可以在返回前触发公开 StopListening，其中一项从另一条主机线程调用。它不是整个 ESP32/FreeRTOS 或真实服务器模拟器。

## 最终执行结果

| 命令 / 检查 | 实际结果 |
| --- | --- |
| `python3 tools/dev.py --offline format --check` | 通过；Ruff 与 15 个 Python 文件格式通过，自有 C/C++ 同入口通过 |
| `python3 tools/dev.py --offline test --suite tools` | 34/34 通过；更新原 source-preparation fixture 以应用新的真实补丁选择路径 |
| `python3 tools/dev.py --offline xiaozhi test` | 25/25 通过：原有 8 项角色/测试图检查，加 17 项 PTT 回归 |
| PR #9 同一 harness 的两项红色对照 | 原源码成功编译；两个行为断言均预期失败，各 CTest 返回码 8，详见下节 |
| `python3 tools/dev.py --offline --jobs 4 xiaozhi build --profile xiao-esp32s3-plus-st7789 --pet --assets assets/generated/deepseek/assets.bin` | 2238 步完整构建通过，返回码 0；使用本地真实角色包 |
| 子模块状态 / `git diff --check` | 原子模块无源文件修改，差异空白检查通过 |

17 项 PTT 场景：

- START/STOP 同轮合并、连接调度前松开、阻塞连接中松开、连接完成但启动采集前松开。
- 松开再按的最新请求、正常按住/松开、打开失败时取消陈旧重按，且下一次新按可继续。
- 真实协议错误/通道关闭回调、网络断开事件，以及阻塞连接中重置和重置排在连接任务之前的两种时序。
- 自动切换、上一轮手动模式后的自动/唤醒连接遇陈旧 STOP、配置诊断和说话打断。

断言观察公开状态、协议 start/stop、采集使能和角色动作。正常录音松开还检查发送 stop 的当时已停止采集；取消且未开始采集时不发送 start/stop，也不进入等待回复的 thinking。

## 红绿对照

同一套测试源不变，只将 CMake 的 APPLICATION_ROOT 指向 PR #9 已生成、未应用 manual-listening.patch 的真实旧源：

```sh
cmake -S tests/pet -B build/container/ptt-baseline/build -G Ninja \
  -DCMAKE_BUILD_TYPE=Debug \
  -DUPSTREAM_ROOT=/workspace/third_party/xiaozhi-esp32 \
  -DOVERLAY_ROOT=/workspace/src/xiaozhi \
  -DAPPLICATION_ROOT=/workspace/build/container/xiaozhi-pet/e3994d08706105fac81c/source/main
cmake --build build/container/ptt-baseline/build --target DCPttApplicationTest --parallel 4
ctest --test-dir build/container/ptt-baseline/build --output-on-failure --no-tests=error -R '^ptt-coalesced-tap$'
ctest --test-dir build/container/ptt-baseline/build --output-on-failure --no-tests=error -R '^ptt-release-during-connect$'
```

在同一锁定 Docker 镜像、禁网、仓库挂载 /workspace 下运行；使用镜像 native.host_environment() 选择工具。两个 CTest 分别运行并检查非零返回码，没有把预期失败伪装为正常退出。

| 旧源场景 | 预期失败证据 |
| --- | --- |
| ptt-coalesced-tap | `cancelled request must leave application idle`，CTest exit 8；同轮松开未阻止后续进入 Listening |
| ptt-release-during-connect | `cancelled request must send no listening start or stop`，CTest exit 8；放开后仍发送过 start/stop |

当前源主机目录为 `build/container/xiaozhi-pet/8ab8d72673969c25e409/source/main`，同样两项及其余 23 项全部通过。旧源两项失败是实际行为断言，不是抽取、缺符号或编译错误。

## 最终固件

生成源/构建目录：`build/container/xiaozhi-pet/0d178aa04b9ee214fe64/`，固件在其 build 子目录。Application 实际编译一次，生成源依赖锁与跟踪锁一致。

生成 application.h SHA-256：`94fbed7ccfe984ee0aa58667aefb3849e1dec01fa58c2a968580ac616941fe94`。

| 文件 | 大小（B） |
| --- | ---: |
| xiaozhi.bin | 2515216 |
| xiaozhi.elf | 29291472 |
| bootloader/bootloader.bin | 16784 |
| partition_table/partition-table.bin | 3072 |
| ota_data_initial.bin | 8192 |
| configured_assets.bin | 1443207 |

应用 SHA-256：`0f23dcb161eb90efd4a076a3167c5e43fd5273ebb4581b19cc601e9e49d44b64`。
角色包 SHA-256：`a6822c21a9409a21c2e762cfc4e45dd339c71ca3a38f4541ef50599244fb0378`，与本地输入逐字节一致。本次没有生成/上传新的第三方角色图片，也没有发布镜像或环境。

## 失败、跳过和未运行

测试端开发中曾出现方法提取器吞并单行函数、日志 shim 吞掉参数导致 unused-parameter、stop 时采集观察字段未声明的编译失败，均已修正并完成上述最终验证。这些编译失败不作为生产缺陷复现，也不混入两个预期红色对照结果。

最终当前实现没有测试失败。完整固件仍有上游 Kconfig 旧式默认值/弃用及组件依赖提示；离线组件管理器提示跳过 registry 变更检查，最终构建成功。

未重复构建独立测试图和无角色补丁的原参考模式：新补丁仅在 pet 构建中应用，独立显示模式没有 PTT 执行路径。未重跑素材浏览器：没有素材或网页变更。无新增 C API，不添加 C11/C++17 兼容占位检查。

没有设备和真实语音服务联调，未验证物理按键抖动、电平、FreeRTOS 实机抢占/延迟、麦克风 DMA、录音质量、扬声器或完整对话。主机测试中的端口状态不代表物理音频停止时刻。远端 CI 的执行结果以本功能 PR checks 为准；用户决定是否 merge。
