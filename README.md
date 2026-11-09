# DeepChat 实体桌宠

目标：让一个可爱的角色生活在 ESP32-S3 驱动的小屏幕里，具备待机动画、按键语音对话和情绪反馈。

当前状态：已完成实施计划与风格基线，尚未实现固件、语音服务和烧录工具。

- [实施与 AI 交接计划](Plan.md)
- [项目通用实现约束](Rules.md)
- [代码与 API 风格](STYLE_GUIDE.md)
- [AI 工作约定](AGENTS.md)
- [日志规范](docs/LOGGING.md)

计划沿用 thread-cascade-over-coap 的命名、格式及 API 文档风格；硬件平台采用 ESP32-S3，具体依赖在实施阶段锁定。
