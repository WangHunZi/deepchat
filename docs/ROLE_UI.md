# 角色常驻界面与小智状态联动

本功能把已合并的 DeepSeek 娘素材接到小智现有 Application、状态机、LVGL 和 GIF 播放器。它不增加业务状态、FreeRTOS 任务、事件队列、播放定时器或网络重试。
板级仍是 bread-compact-wifi-lcd 参考配置；真实 XIAO 引脚、屏幕参数和语音服务联调尚待确认。

## 构建与检查

先按 docs/ASSETS.md 生成 assets/generated/deepseek/assets.bin，并缓存完整参考依赖，再执行：

```sh
python3 tools/dev.py --offline xiaozhi test
python3 tools/dev.py --offline --jobs 4 xiaozhi build --profile reference-s3-lcd --pet --assets assets/generated/deepseek/assets.bin
```

`xiaozhi test` 构建并运行真实上游 FSM、LVGL 和 GIF 主机测试，首次需要已缓存的 LVGL 组件，不需要真实设备或服务端。
`--pet` 显式选择角色版本，并要求提供自定义资源包。没有该参数的普通/带素材参考构建保持原上游 Application 和界面。
角色版本只支持默认 LCD 消息布局；其他布局在编译时明确拒绝，避免将默认栏对象用于不同布局。
工具和 SDK 镜像、组件锁不变，没有镜像发布步骤。

## 实际事件与画面

| 小智现有事件 / 状态 | 画面 | 说明 |
| --- | --- | --- |
| Idle，没有当前回复 | neutral / 待机 | 循环基础动作 |
| Connecting | thinking / 思考 | 等待通道建立 |
| Listening | listening / 倾听 | 沿用原录音和输入引擎 |
| 手动松开并发送 stop-listening 后的 Idle | thinking / 思考 | 仅显示标记，不新增业务状态 |
| TTS start，进入 Speaking | speaking / 说话占位 | 仍复用待机图像，不声称口型同步 |
| 句间暂时播放排空，尚无 TTS stop | 继续说话 | 不将局部排空当成本轮结束 |
| 收到 TTS stop，但还有本地播放 | 继续说话 | 等待已有 MAIN_EVENT_PLAYBACK_DRAINED |
| stop 和 AudioService 排空均具备 | 手动模式回 Idle；自动模式回 Listening | 保留原手动/自动录音语义 |
| 本轮有 happy / confused，手动回复结束 | 单次情绪反馈 | 播完后由原每秒状态刷新恢复 neutral |
| 本地回复已结束后才到的受支持情绪 | 立即显示反馈 | Idle→Idle 不产生状态变更，也能显示 |
| 通道关闭、协议重置或断网取消等待 | 清理本轮信息 | 已经处于 Idle 时直接刷新，避免思考动画滞留 |
| 启动、配网、激活、升级、自测、致命错误 | 原诊断界面 | 不强制隐藏必要的操作和提示 |

LLM 情绪边界只接收已有的 happy、confused、neutral；neutral 清除待显示反馈，其他名字记录不支持且保留当前状态，不偷偷换回系统表情。
既有主任务错误事件的 cancel/cloud_off 在 Idle 下使用困惑动作；激活、升级等诊断 Alert 保留原状态和提示。没有从 Alert 工作线程写入显示映射实例。
自动录音模式会直接继续 Listening，不为了情绪动画延迟下一轮。当前首版交互仍以手动按住说话为目标，实际按钮与服务端配合需后续验证。

## 显示层行为

角色主场景隐藏现有图标栏、状态/通知栏和聊天文字栏的父层。文字仍可按原接口更新，但子标签解除隐藏也不会穿透隐藏的父层而遮挡人物。
切回诊断场景恢复顶栏/状态栏，底栏遵循原字幕偏好及是否有文字；没有覆盖用户 hideSubtitle 设置。独立低电量弹层保持原行为。

单次情绪动画沿用 LvglGif 的完成状态。LcdDisplay 在已有每秒 UpdateStatusBar 中、同一显示锁内检查 IsPlaying=false 并恢复待机，最多在动画结束后约一秒刷新。
没有在 GIF 的正在执行回调内销毁其对象，也没有为此创建跨任务完成回调、代次计数或第二个播放定时器。
这不是精确到毫秒的硬实时动画结束通知；设备调度时序仍需实测。

## 新增信息的必要性与所有者

DCPetPresentation 是 Application 主任务持有的无分配显示映射实例，不调用状态转换、音频或网络。它的三个值都有现有调用点：

| 信息 | 当前问题 / 调用点 |
| --- | --- |
| awaitingReply | 手动松开后上游业务仍是 Idle，无法仅凭 DeviceState 区分待机和等待回复 |
| stopReceived | 协议 stop 与 AudioService decode/output in-flight 排空是不同事件；避免早退和句间误结束 |
| feedback | LLM 情绪可能在音频完成前到达，保留一项本轮反馈供真正完成后显示，不是积压队列 |

显示层的 pet_mode 选择主画面或诊断布局；pet_feedback_active 只标记需要播放结束后恢复待机的两个现有动作，避免影响普通循环动画。
Cancel 返回 Idle 下的待机刷新动作，因为上游同状态转换成功不会通知监听器；没有通过重复 TransitionTo 来“确认成功”。
音频结束依据所选 AudioService 的队列和 decode/output in-flight 排空合同，不增加 I²S 读回或物理扬声器确认。

## 如何管理上游修改

- patches/xiaozhi/pet-ui.patch：Application、Display/LcdDisplay 的小范围补丁，保留上游风格，不复制整个固件。
- src/xiaozhi/：两个自有 C++ 显示映射/布局头文件，编译时叠加到对应 main 目录；由现有格式入口覆盖。
- tools/xiaozhi_overlay.py：从固定上游 git archive 创建生成副本，复制头文件并 git apply；补丁失败不发布半成品源码目录。
- 生成位置：build/container/xiaozhi-pet/<输入指纹>/source，固件在同级 build。指纹包含上游 revision、补丁、叠加文件及业务依赖锁。
- 原子发布后的同输入副本可复用；补丁/头文件/锁更新会进入新目录，旧构建不被覆盖。生成目录是构建缓存，不作为编辑源。
- 复用原固定 managed_components 缓存；生成源有自己的依赖锁和生成头文件。固定子模块 tracked 工作树保持 clean。

CI 先构建上游参考工程、运行七项真实组件主机测试，再用默认参考资源编译 --pet 补丁。此步骤只验证固件代码可构建，不下载第三方角色，也不把默认参考资源宣称为 DeepSeek 娘素材；实际角色包的完整参考构建另有本地报告。
CI 角色构建日志和 CTest 日志保留为 artifact，不发布角色固件或镜像。

## 怎么确认行为正确

电脑上先运行 xiaozhi test，检查 manual、cancel、feedback、diagnostics、layout、gif-once、gif-loop 七项。源码中的测试使用真实状态转换与 LVGL，不检查私有计数值或伪造播放器。
原浏览器预览仍可用来检查素材画面，它没有模拟整个 FreeRTOS Application、网络或固件 UI；本轮没有把它改成第二套状态机。

拿到同型号硬件并确认接线后，按以下路径实测：

1. 配网/激活时能看到诊断信息，进入 Idle 后角色完整显示，无顶栏/聊天文字遮挡。
2. 按住时倾听；松开等待时思考；TTS 开始进入说话动作；协议停止发送但声音未结束时仍保持说话。
3. 本地播放完成后待机或单次情绪；单次结束后约一秒内恢复待机；下一轮按键不沿用上轮反馈。
4. 等待回复时断连/重置，不会因 Idle→Idle 没有事件而一直思考；关键错误/诊断仍可操作。
5. 检查低电量提示、字幕偏好恢复、真实屏幕方向/色序及声音。未跑这些步骤前不标记实机通过。

完整编译、测试数量、产物与未运行项见 ROLE_UI_VALIDATION.md。
