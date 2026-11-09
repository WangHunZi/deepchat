# DeepChat 实体桌宠

目标：让蓝发鲸鱼女仆 DeepSeek 娘生活在 ESP32-S3 小屏幕里，通过语音互动和表情反馈陪伴用户。

项目基于 MIT 的 [小智 ESP32](https://github.com/78/xiaozhi-esp32) 二次开发，复用其 C++ 语音、显示、表情和通信能力。上游源码固定在 Git 子模块，开发工具固定在已发布的 Docker 镜像。
当前接入的是 ESP32-S3 LCD 参考工程；XIAO ESP32S3 Plus 的最终接线、角色素材替换与实机验收尚未完成。

## 开发入口

需要 Git、Docker（含 Buildx）及 Python 3.10+：

```sh
git submodule update --init --depth 1
python3 tools/dev.py setup
python3 tools/dev.py --offline format --check
python3 tools/dev.py --offline test --suite tools
python3 tools/dev.py --offline xiaozhi check
# 首次下载业务组件需要网络：
python3 tools/dev.py --jobs 4 xiaozhi build --profile reference-s3-lcd
```

reference-s3-lcd 使用上游参考板配置，不代表 XIAO 接线或可直接烧录固件。旧 build --target esp32s3 --board bringup 仍是历史最小启动应用。

## 查看角色素材

```sh
python3 tools/collect_assets.py
python3 tools/collect_assets.py --check
```

原始联系表及 GIF 位于 assets/local/，来源与动作选择见 [素材说明](assets/README.md)。240×240 成品预览是下一份功能交付，当前构建通过不能代表角色画面或实机通过。

## 文档

- [小智接入、构建与看效果的方法](docs/XIAOZHI.md)
- [小智参考工程验证报告](docs/XIAOZHI_VALIDATION.md)
- [当前实施与 AI 交接计划](Plan.md)
- [项目通用实现约束](Rules.md)
- [命名、格式与 API 风格](STYLE_GUIDE.md)
- [AI 工作约定](AGENTS.md)
- [DeepSeek 娘素材来源与本地收集](assets/README.md)
- [Docker 工具环境与历史基线](docs/BUILDING.md)
- [Docker 镜像发布与锁定](docs/DOCKER_RELEASE.md)
- [已发布镜像锁定验证](docs/IMAGE_PIN_VALIDATION.md)
- [日志规范](docs/LOGGING.md)

自有代码采用 [MIT](LICENSE)；保留小智及组件各自许可。第三方角色素材保留原来源和许可，不因代码开源自动变成 MIT。
