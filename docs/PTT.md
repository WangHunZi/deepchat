# 按住说话：连接期间松开与取消

此修复用于 `--pet` 角色固件，复用上游 Application、DeviceStateMachine、AudioService、Protocol 和 FreeRTOS 事件组。屏幕测试模式与未选择 `--pet` 的原上游参考构建不应用本补丁。

## 问题与行为

原 StartListening / StopListening 只设置事件位。事件位可以合并，并不保存每次按下/松开的顺序：

1. 按下与松开落在同一轮：主循环先进入 Connecting，再忽略 Connecting 中的 stop，随后排队的连接任务开始手动录音。
2. OpenAudioChannel 同步阻塞时松开：主循环暂时不能消费 stop；连接成功后，STATE_CHANGED 又先于 STOP 处理，可能在已松开后短暂启用录音。
3. 先松开再重新按下：同一轮仍可能保留旧 STOP 位，不能让它取消新的一次按下。

修复后按最新请求处理：

| 场景 | 结果 |
| --- | --- |
| 按住，通道已经可用 | 按原流程启动手动录音 |
| 按住，等待通道建立 | 保持 Connecting，建立成功后启动录音 |
| 开始连接前已松开 | 丢弃请求，返回待机，不发 start/stop，不进入等待回复 |
| 连接函数阻塞期间松开 | 函数返回后丢弃请求，不在放开后启动录音 |
| 已进入 Listening，但尚未启用录音时松开 | 在实际发送 start 之前取消，回待机 |
| 真正开始录音后松开 | 先关闭采集，再发送 stop，沿用角色等待回复与 TTS 流程 |
| 松开后再次按下，旧 STOP 位尚未消费 | 最新按下生效，旧 STOP 不取消本次按下 |
| 连接失败、网络错误、断开、协议重置 | 取消旧请求，不自动重试；取消处理完成后可重新按下 |
| ToggleChat / 唤醒词自动连接 | 记录本次真实模式，避免上一轮手动模式使旧 STOP 取消自动连接 |

没有强行中断 SDK 的同步连接函数。连接阻塞时画面/主循环仍可能等待；修复保证返回后不执行已释放的录音请求，不承诺即时取消底层网络操作。已经成功打开的通道与原手动停止一样保留，供后续交互复用。

## 一个新增值及其调用点

`Application::manual_listening_requested_` 是一个原子布尔值，表示当前仍有效的手动录音请求，不新增业务状态或第二套状态机。

- 按键任务调用 StartListening / StopListening 时先发布最新请求，再设置原事件位。原子值用于连接阻塞期间跨任务传递最新意图。
- 主循环遇到 START / STOP 任一事件位时，按最新请求选择原有处理器；不逐个重放已经被覆盖的按键边沿。
- ContinueOpenAudioChannel 在阻塞前后检查请求；StartListeningAudio 在真正发送 start 前检查，覆盖连接完成与状态事件之间的间隔。这些读取跨越了可发生外部按键变化的阶段，不是对库成功返回的重复确认。
- 错误/断连的异步入口及时取消阻塞中的请求，主事件处理也取消与故障同时排队的请求。ResetProtocol 在请求入口和实际释放资源时取消，并在销毁 protocol 前结束活动会话状态，防止排队中的旧连接任务解引用已释放资源。

不新增按键队列、代次计数、录音计时器、后台连接任务、网络重试或成功读回检查。按钮去抖继续使用上游 Button。

## 构建与检查

```sh
python3 tools/dev.py --offline test --suite tools
python3 tools/dev.py --offline xiaozhi test
python3 tools/dev.py --offline --jobs 4 xiaozhi build --profile xiao-esp32s3-plus-st7789 --pet --assets assets/generated/deepseek/assets.bin
```

`xiaozhi test` 通过现有隔离源码准备入口应用角色与手动录音补丁。新增测试编译生成源码中的真实 Application 入口、主循环和处理方法，链接真实 DeviceStateMachine 与角色映射；仅为平台事件组、协议、音频和显示端口提供测试替身。阻塞期间的按键通过确定的回调时序注入，不靠真实网络延迟碰运气。

实际命令、测试数量、修复前失败证据、产物与未运行项见 [PTT_VALIDATION.md](PTT_VALIDATION.md)。测试替身不等同于 ESP32 上的 FreeRTOS 调度、物理按键、I²S 或真实服务。

## 到货后的补充验收

1. 通道未建立时快速点按，观察松开后不开始录音，角色最终回待机。
2. 建立连接期间按住再松开；连接函数结束后不应继续倾听。
3. 正常按住讲话、松开后等待回复，声音与角色联动仍正常。
4. 快速松开再按下，第二次按住能继续倾听，不被旧 stop 取消。
5. 等待连接时断网/重置，再恢复并重新按下，不复活旧录音。

实机延迟、GPIO 电平、去抖、音频幅度和真实服务仍需分别记录。服务端选择、离线角色/音频自检和完整固件打包是后续功能 PR。
