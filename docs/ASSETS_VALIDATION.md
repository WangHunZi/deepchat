# 角色素材、同源预览及参考构建验证

本轮将透明 WebP 角色画面与原 GIF 时长转换为 240×240 GIF，复用固定小智的资源打包器及设备 GIF 解码器。独立测试子代理执行转换、编译、行为测试和浏览器 QA；根代理负责实现与修复。

## 最终输入与产物

- 小智 commit a73e9a7e266e3196d1368ba46c30bee0d81f0a64，未改 tracked 上游源码；依赖锁未变。
- 角色来源 commit 27843e4ba86cc439d29aa1c6b0591f206fa2514f；原 WebP 和五个时长参考 GIF 的哈希见 assets/sources.json。
- Docker 镜像与 SDK 沿用现有锁；新增业务依赖仅为哈希固定的 Pillow 13.0.0，安装到 build/container/asset-python。
- 最终 assets.bin：**1,443,207 B**，约 1.38 MiB，占参考 8 MiB 分区约 17.2%。
- SHA-256：`a6822c21a9409a21c2e762cfc4e45dd339c71ca3a38f4541ef50599244fb0378`。

| GIF | 帧数 | 一轮时长 ms | 字节 | 方式 |
| --- | ---: | ---: | ---: | --- |
| dc-idle.gif | 6 | 1100 | 110171 | 循环 |
| dc-listen.gif | 6 | 1100 | 109625 | 循环 |
| dc-think.gif | 6 | 900 | 109147 | 循环 |
| dc-happy.gif | 4 | 700 | 76981 | 单次 |
| dc-confused.gif | 8 | 1300 | 150559 | 单次 |

说话复用待机，同一文件不重复存储。字体和非表情资源来自已验证参考工程的默认资源包。产物位于 assets/generated/deepseek/，角色图片与包没有加入 Git 或公开 CI artifact。

## 工具与素材检查

| 实际命令 / 检查 | 结果 |
| --- | --- |
| `python3 tools/dev.py assets setup` | 固定 wheel 通过 pip 哈希校验并安装；未改 SDK/镜像 |
| `python3 tools/dev.py --offline format --check` | 通过，12 个 Python 文件及自有 C 测试适配格式正确 |
| `python3 tools/dev.py --offline test --suite tools` | 25/25，通过 |
| `python3 tools/dev.py --offline assets test` | 11/11，通过，使用原创几何 fixtures |
| `python3 tools/dev.py --offline assets build` | 从固定原图/时长、base 字体及上游 packer 生成最终包与自包含 HTML |
| `python3 tools/dev.py --offline assets check` | 文件哈希、包内尺寸/映射、像素/时长/循环及配置/来源/base/模板时效检查通过 |
| 原始设备 gifdec 全帧对照 | 5 段、共 30 帧 BGRA 完整字节、逐帧时长及循环与预览完全一致 |
| `git diff --check`、子模块源码检查 | 通过，上游 tracked clean |

11 项素材测试覆盖：包与预览同源且保留字体；原设备解码像素/时长；源文件损坏；路径越界；预算超限保留旧产物；无效动作引用；输出损坏；配置/base/模板过期；跨帧统一锚点；确定性生成；时长 GIF 绿边不污染 WebP 画面。
设备解码对照直接编译固定子模块的 gifdec.c，主机只适配文件/内存/日志。分支宏与参考配置一致（关闭 Helium 与 GIF cache）；自有适配程序 C11 严格警告编译，上游不强加本项目风格。
该工具只验证本工具生成的受控 GIF，不是任意不可信 GIF 的安全解析器。

## 发现与修复

首次浏览器截图发现旧上游 preview GIF 的发丝、服装、腿边有显眼绿色轮廓；原 idle GIF 首帧强绿像素 1166，透明 WebP 对应格为 0。
修复改为 WebP 提供画面、GIF 只提供时长，明确配置各行列映射，没有加入自动匹配/抠图机制。新增合成绿色 GIF 的回归测试，验证时长参考的颜色不会进入画面。
最终 30 帧在 `g > 1.25*r && g > 1.25*b && g > 90` 条件下计数均为 0；截图确认绿边消失。旧 1,486,890 B 包已经替换，不作为最终交付。
浏览器 favicon 404 通过内联空 favicon 修复；控制台最终无错误或警告。

## 带素材参考固件

实际命令：

```sh
python3 tools/dev.py --offline --jobs 4 xiaozhi build --profile reference-s3-lcd --assets assets/generated/deepseek/assets.bin
```

独立 custom 目录的首次参考构建完成 2238 步；WebP 修复后禁网增量构建完成 5 步，均 exit 0。上游组件管理器禁网时跳过联网检查并使用固定缓存，未更改依赖。
sdkconfig 已确认 FLASH_CUSTOM_ASSETS=y，CUSTOM_ASSETS_FILE 指向 custom 目录的 input-assets.bin。
上游构建生成的 configured_assets.bin 与最终转换包逐字节相同，五段 GIF/尺寸和六项 emotion 映射均保留；flasher 元数据引用该文件。仅核对元数据，没有烧录。

app 2,545,776 B、ELF 30,052,544 B、bootloader 16,736 B、分区表 3,072 B、OTA data 8,192 B；app 分区剩余 38%，所有者 agent:agent。
Prettier 仅格式化 HTML 模板后重新生成预览，素材二进制哈希保持不变，未重复编译无变化的固件。

## 浏览器 QA

Browser plugin 不可用，使用现有 Playwright 1.62.0 与 Chromium 156.0.8078.79；未安装新的浏览器运行依赖。
URL：http://127.0.0.1:8765/ 。视口：桌面 1280×960、手机 390×844。

| 检查 | 结果 |
| --- | --- |
| 页面标题/身份、非空、无错误覆盖层 | 通过 |
| 六动作切换、说话占位说明 | 通过 |
| 播放→暂停帧稳定、前后逐帧、拖动定位 | 通过 |
| 开心/困惑末帧停止与重新播放 | 通过 |
| 下载实际 GIF、1×/2× 尺寸 | 通过 |
| 手机无页面横溢出，2× 可完整横向查看画面 | 通过 |
| 已加载 HTTP 页面禁网后切换/暂停/逐帧 | 通过 |
| Console errors / warnings | 0 / 0 |

截图在当前会话 /tmp/deepchat-preview-desktop.png、/tmp/deepchat-preview-mobile.png、/tmp/deepchat-preview-mobile-2x.png；最终截图均来自格式化后的最终模板和无绿边素材。会话证据不作为 Git 中的角色图片发布。
file:// 直接打开被环境 Chromium 企业策略以 ERR_BLOCKED_BY_ADMINISTRATOR 阻止，未绕过，不能标为实测通过。工具本身生成自包含 HTML；推荐使用已验证的本机 HTTP 入口。

## 尚未验证

- XIAO Plus 真实引脚、Flash/PSRAM 和屏幕参数；未烧录或进行实屏显示。
- 完整 LVGL 顶栏/聊天文字叠层与角色画面组合；当前预览是素材检查画布。
- 自定义 listening/thinking/speaking 与小智真实状态事件自动映射、嘴型和音频同步；说话仍是明确占位。
- 实际 RAM 峰值、SPI 刷新、真实屏幕色彩和音频/联网并发；预估像素缓冲 288000 B 不含结构和其他缓冲。
- macOS/ARM 原生素材依赖安装，其他浏览器；干净远端 CI 结果以本 PR checks 为准。
