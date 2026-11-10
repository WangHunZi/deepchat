# 角色、PTT 与原始小智组件的主机测试

此目录不实现新的状态机、LVGL 对象树或 GIF 播放器。它直接链接固定小智的 device_state_machine.cc、LvglGif/gifdec 和锁定 LVGL 9.5，平台 shim 仅替换 ESP 日志。
测试图像是原创 4×4 红蓝方块，未使用第三方角色图片。

CMake 必需参数：

- UPSTREAM_ROOT：已初始化且具有 managed_components/lvgl__lvgl 的小智目录；先完成参考构建以取得锁定业务依赖。
- OVERLAY_ROOT：src/xiaozhi 目录，包含生产实际使用的 DCPetPresentation.h 和 DCPetLayout.h。
- APPLICATION_ROOT：通过 tools/xiaozhi_overlay.py 准备并应用角色/手动录音补丁的生成源 main 目录；不要指向原上游 main。日常使用 `python3 tools/dev.py --offline xiaozhi test`，入口会自动准备并传入此参数。

在固定 Docker 镜像内运行的等价命令（将 `<本次指纹>` 替换为本次准备结果）：

```sh
cmake -S tests/pet -B build/container/pet-tests -G Ninja \
  -DUPSTREAM_ROOT=/workspace/third_party/xiaozhi-esp32 \
  -DOVERLAY_ROOT=/workspace/src/xiaozhi \
  '-DAPPLICATION_ROOT=/workspace/build/container/xiaozhi-pet/<本次指纹>/source/main' \
  -DCMAKE_BUILD_TYPE=Debug
cmake --build build/container/pet-tests --parallel 4
ctest --test-dir build/container/pet-tests --output-on-failure --no-tests=error
```

历史七项角色测试的首次构建为 538 步；新增测试后的实际步数见验证报告。自有测试调用方为 C++23，开启 Wall/Wextra/Wpedantic/Werror，未对第三方源码强加风格或错误诊断策略。

七项行为测试：

1. manual：使用真实上游状态转换走过 listening → idle 等待回复 → speaking → idle。句间 drain 不结束；服务端 stop 后仍有音频不结束；真实 drain 后只结束一次，先显示本轮反馈。
2. cancel：真实状态机的 Idle→Idle 不发状态通知，因此等待回复时取消会直接返回待机刷新动作；取消和下一次录音清理上一轮显示信息，旧 drain 不会结束新的一轮。
3. feedback：未知/空情绪保持原反馈，neutral 清除待展示反馈，空播放队列先于 stop 时也能正常完成；已完成播放并显示待机后晚到的反馈可以立即显示。
4. diagnostics：启动、配置、激活、升级、音频自测和致命错误返回诊断界面选择，而不是强行显示角色。
5. layout：在真实 LVGL 对象树隐藏三个父栏；子标签反复更新/解除隐藏也不重新遮挡；退出角色模式恢复字幕偏好，角色和低电量弹层不被隐藏。
6. gif-once：原 LvglGif 经 lv_tick_inc/lv_timer_handler 驱动，在一轮结束后 IsPlaying=false。
7. gif-loop：原循环 GIF 经同样时钟驱动仍保持播放，显式 Stop 后停止。

以上七项验证生产显示映射、真实上游状态规则、LVGL 可见性与 GIF 生命周期；新增 PTT 测试覆盖所选真实 Application 方法及主循环，但不包含设备 FreeRTOS 调度、音频 DMA、真实网络或实机。实际 Application 接线与 LCD 完整界面仍需参考固件编译和后续设备验证。


另有一项实际 240×240 测试图像素测试，以及 tests/ptt 的 Application 软件时序回归：直接包含真实生成 application.h，并从生成 Application 源码提取完整 Run 和所选完整方法，不改方法体；链接真实 DeviceStateMachine 与 DCPetPresentation。仅事件组、协议、音频和显示端口使用测试替身，平台初始化单独提供，不调用硬件/OTA 初始化。

PTT 用例观察录音使能、协议 start/stop、连接调用、最终状态与角色动作，不断言新增私有原子字段。测试包括同批 START/STOP、连接中松开、录音前松开、再次按下、取消和自动模式等；修复前两条失败证据与当前实际数量见 [PTT_VALIDATION.md](../../docs/PTT_VALIDATION.md)。这些是确定时序的软件回归，不代表实际 FreeRTOS、按键电平、音频或网络联调。
