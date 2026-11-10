# PTT 的真实 Application 主循环回归

此测试在主机上编译生成源中实际的 `application.h`、完整 `Application::Run()` 和所选完整方法，链接原小智 `DeviceStateMachine` 与本项目 `DCPetPresentation`。不复制业务状态机或事件分发顺序，不读取/断言新增请求标志的值。

`extract_application.py` 从当前已打补丁的 `application.cc` 提取方法的原始文本；单行/多行函数都按括号配对定位，跳过普通字符串、字符和注释。两个协议回调的注册语句也原文提取。若方法或回调不存在，配置立即失败。它只面向此固定上游和本项目补丁，不是通用 C++ 解析器。

平台替身的范围：

- FreeRTOS 事件组保留 OR 合并和取出后清位的语义；无事件时用测试标记退出真实无限主循环。
- 阻塞 `OpenAudioChannel` 可在返回前触发真实 `StopListening()`，其中一项从另一条主机线程调用。
- Protocol/AudioService/显示端口只记录调用和对外状态，不提供真实网络、编码器、DMA 或 LCD。
- 构造函数只完成测试平台接线；不运行设备、OTA、JSON 或服务初始化。两个协议回调原注册语句独立绑定，其余初始化流程由完整固件编译检查。
- 所有断言观察公开设备状态、协议 start/stop、采集使能和显示动作；normal 还核对发送 stop 的当时已经停止采集。

正常入口为 `python3 tools/dev.py --offline xiaozhi test`；此目录由 tests/pet 的 CMake 接入，`APPLICATION_ROOT` 必须指向准备好的生成源 main 目录。

17 个 PTT 场景覆盖合并短按、调度前松开、阻塞连接中松开、录音启动前松开、松开后再按、正常按住/松开、打开失败、网络错误、通道关闭、两种协议重置时序、网络断开，以及自动/唤醒/配置诊断/说话打断回归。原有 8 项角色和测试图检查保留，总计 25 项。

红绿对照使用同一 harness，只把 `APPLICATION_ROOT` 改成 PR #9 已生成且未包含 manual-listening.patch 的 main 目录。例如本次记录使用 `build/container/xiaozhi-pet/e3994d08706105fac81c/source/main`。配置后只构建 `DCPttApplicationTest`，分别运行：

```sh
ctest --test-dir BASELINE_BUILD --output-on-failure --no-tests=error -R '^ptt-coalesced-tap$'
ctest --test-dir BASELINE_BUILD --output-on-failure --no-tests=error -R '^ptt-release-during-connect$'
```

旧源码应因行为断言失败，当前源码应通过；编译错误不能冒充缺陷复现。完整命令、实际结果和硬件限制见 docs/PTT_VALIDATION.md。
