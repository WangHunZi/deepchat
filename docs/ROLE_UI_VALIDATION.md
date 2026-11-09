# 角色常驻界面与事件联动验证

独立测试子代理执行编译、行为测试和源码接线审查。最终代码使用真实小智 FSM、LVGL、GIF 播放器和 AudioService 排空事件；没有新建并行状态机或播放任务。

## 最终命令与结果

| 命令 / 检查 | 结果 |
| --- | --- |
| `python3 tools/dev.py --offline format --check` | 通过，14 个 Python 文件及自有 C/C++ 文件 |
| `python3 tools/dev.py --offline test --suite tools` | 30/30，通过 |
| `python3 tools/dev.py --offline xiaozhi test` | 7/7，通过，真实组件主机测试 |
| `python3 tools/dev.py --offline --jobs 4 xiaozhi build --profile reference-s3-lcd --pet --assets assets/generated/deepseek/assets.bin` | 2238 步完整角色参考构建通过，exit 0 |
| `git diff --check`、子模块源码状态 | 通过，固定上游 tracked clean |

上游 commit 为 a73e9a7e266e3196d1368ba46c30bee0d81f0a64；镜像、SDK 与组件锁未变。
最终生成树为 build/container/xiaozhi-pet/cfb9c4e59aa2dc504080/，source 是补丁源码，build 是参考固件。
compile_commands 已确认真实编译该目录的 patched application.cc，最终标准选项 GNU++23；主机自有测试为 C++23，开启 Wall/Wextra/Wpedantic/Werror，不强改第三方诊断策略。

## 行为证据

七项 CTest：manual、cancel、feedback、diagnostics、layout、gif-once、gif-loop。

- 使用真实 DeviceStateMachine 驱动录音、停止、等待、Speaking 和完成；等待仍使用 Idle，显示为 thinking。
- 句间 drain 不能结束整轮；stop 已到但未排空继续等待；排空先于 stop 时也能完成；同一完成条件只处理一次。
- 反馈保留至手动回复完成；未知/空情绪不改变已接收反馈；neutral 清除待反馈；本地结束后晚到 happy 仍可显示。
- 真实 FSM 的 Idle→Idle 不发通知；取消在已 Idle 时返回明确待机刷新动作，不滞留思考。新录音/取消清理上一轮信息，旧 drain 不结束新轮。
- 启动、配网、激活、升级、自测和致命错误保留诊断界面选择。
- 真实 LVGL 对象树隐藏父栏后，子标签更新/解除隐藏仍不可见；退出角色模式恢复字幕偏好；角色及低电量弹层不受影响。
- 原 LvglGif/gifdec 用 LVGL tick/timer 驱动：单次结束 IsPlaying=false，循环持续，显式 Stop 正常。没有测试专用播放器替代生产库。

新增五项工具测试验证隔离源码：原上游不被修改；同输入复用已完整准备的源码；补丁变更得到新源码；补丁失败不发布半成品；依赖锁变化不能复用旧锁；另有 --pet 缺少 --assets 的边界拒绝。工具总数从 25 增到 30，其中“原源码不改/同输入复用”在同一项测试内。

主机测试不等同于整个 Application 的 FreeRTOS 运行。真实接线由补丁源码审查和参考交叉编译补充验证；实机及完整协议联调另行进行。

## 审查发现与修复

1. 上游同状态转换成功不发送变更通知，关闭等待中的通道时 Idle→Idle 不能刷新。通过 CancelPetPresentation 在主任务直接更新已 Idle 的画面，加入回归。
2. Alert 也会从激活/升级任务调用，不能在该入口清理主任务持有的显示标记。已删除该处写入，只在既有所有者事件/取消路径更新。
3. 生成源复制依赖锁，因此锁是输入之一。已纳入源码指纹，并验证换锁后新副本使用新锁、旧副本保持不变。
4. LLM 情绪可能在本地播放结束后到达，Idle→Idle 同样无通知。已在主任务情绪回调中更新 Idle 画面；仍等待回复时保持 thinking，不消费反馈。
5. 首轮 Ruff import 分组检查失败，已按自有 src 布局修复并复验通过；最终没有失败或跳过的用例。

开发过程中旧 a54/cac2 生成树的编译只作中间证据，最终使用 cfb9c4e59aa2dc504080；没有把旧构建算作最终源码通过。

## 最终参考产物

| 文件 | 字节 |
| --- | ---: |
| xiaozhi.bin | 2546832 |
| xiaozhi.elf | 30121336 |
| bootloader/bootloader.bin | 16736 |
| partition_table/partition-table.bin | 3072 |
| ota_data_initial.bin | 8192 |
| configured_assets.bin | 1443207 |

默认 LCD 消息布局、自定义素材、240×240 和 ESP32-S3 配置已核对；应用分区剩余 38%。产物 owner 为 1000:1000。
configured_assets.bin 与输入 assets.bin 整个文件一致，SHA-256 为 a6822c21a9409a21c2e762cfc4e45dd339c71ca3a38f4541ef50599244fb0378。
生成源隔离、失败不发布半成品、目录复用及三份依赖锁一致已验证；没有更换 SDK/镜像、没有下载新依赖或修改上游 tracked 文件。

CI 运行同一组主机测试，并以默认参考资源编译角色补丁，不下载第三方角色图片；远端干净 CI 结果以 PR checks 为准。本地已用真实角色包完成上述构建，不将 CI 默认资源混同于角色包。

## 尚未运行

- XIAO Plus 实物引脚、供电、Flash/PSRAM、SPI 方向/色序；没有烧录或实屏验收。
- 完整 Application FreeRTOS 调度、真实 ASR/模型/TTS 服务、真实按键和网络异常联调。
- I²S/DMA 或物理扬声器精确播放结束；当前依赖 AudioService 队列及 decode/output in-flight 排空合同，不增加读回确认。
- 完整固件 UI 的屏幕截图和硬件内存/帧率实测。原浏览器仍是已验证素材检查工具，本轮不把它当成整个 SDK 模拟器。
- 精确毫秒级情绪结束回待机；采用已有每秒 UpdateStatusBar，动画完成后最多约一秒恢复。

操作与实机验收路径见 ROLE_UI.md，最终板级定版仍需用户提供具体器件资料。
