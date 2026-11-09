# DeepChat 实体桌宠

目标：让一个可爱的角色生活在 ESP32-S3 驱动的小屏幕里，具备待机动画、按键语音对话和情绪反馈。

当前已实现 P0 构建基线：固定版本的 ESP-IDF、主机工具、最小 ESP32-S3 启动程序、开发命令与 CI。
当前固件只输出启动信息；角色动画、音频、语音后端和最终板级适配按计划继续开发，尚未完成实机验收。

## 开始开发

需要 Git、Python 3.12（含 venv/pip）及主机 C/C++ 编译器。在仓库根目录执行：

```sh
python3 tools/dev.py setup --host-only
python3 tools/dev.py format --check
python3 tools/dev.py test --suite tools
python3 tools/dev.py build --target host
```

安装 SDK 并交叉编译最小固件：

```sh
python3 tools/dev.py --jobs 4 setup
python3 tools/dev.py --jobs 4 build --target esp32s3 --board bringup
```

`bringup` 不假定 XIAO Plus 引脚和 PSRAM 配置；它是编译验证目标，不能替代最终板级适配。

## 文档

- [构建与环境说明](docs/BUILDING.md)
- [P0 验证报告](docs/P0_VALIDATION.md)
- [实施与 AI 交接计划](Plan.md)
- [项目通用实现约束](Rules.md)
- [代码与 API 风格](STYLE_GUIDE.md)
- [AI 工作约定](AGENTS.md)
- [日志规范](docs/LOGGING.md)

沿用 thread-cascade-over-coap 的命名形式、格式及 API 文档风格，公共 C 符号采用 `DC` 前缀。
代码采用 [MIT 许可证](LICENSE)；第三方库及后续角色素材保留各自许可。
