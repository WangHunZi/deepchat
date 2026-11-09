# DeepSeek 娘 240×240 素材与预览

本功能将已收集的角色素材转为小智 LCD 已支持的 GIF，复用上游资源打包函数生成 assets.bin，并提供单文件浏览器预览。没有新增设备解码器、资源格式或播放任务。
当前验证的是角色素材；固件顶栏/聊天文字叠层、XIAO 接线、实屏和声音同步尚未适配。

## 如何查看与判断

如果当前工作区已生成素材，直接运行：

```sh
python3 tools/dev.py preview
```

在运行此命令的电脑浏览器打开 http://127.0.0.1:8765/ 。Ctrl-C 停止服务。该服务仅提供生成目录，默认监听本机，宿主机不需要 Pillow 或 SDK。
也可取得 assets/generated/deepseek/index.html，在允许 file:// 的本地浏览器离线打开；当前云 Chromium 的企业策略阻止 file://，因此该方式没有实测通过。已加载的 HTTP 页面禁网后继续操作已通过。

人工检查顺序：

1. 保持 1×，逐个选择待机、倾听、思考、说话、开心、困惑，检查角色大小及表情。
2. 暂停，点上一帧/下一帧或拖动时间轴，检查头发、服装、尾巴和脚部边缘及位置。
3. 恢复播放，观察循环接缝；开心/困惑单次播放后应停在末帧，点击重新播放从头开始。
4. 选择 2× 放大细节。手机上放大后可在画面区域横向滚动，页面本身不应横溢出。
5. 点击下载当前设备 GIF，取得与 assets.bin 内相同的动画。

1× 指 240 个 CSS 像素，不代表实际小屏的物理尺寸。浏览器显示不能代替 SPI 刷新率、色彩校准或音频并发的实机验收。

## 从干净 checkout 生成

需要 Docker、Git 和 Python；沿用已发布工具镜像，不要求重新发布镜像。

```sh
git submodule update --init --depth 1
python3 tools/dev.py setup
python3 tools/collect_assets.py --pack codex-pet
# 首次安装哈希锁定的素材依赖，使用网络：
python3 tools/dev.py assets setup
# 首次生成参考工程默认资源/字体并缓存组件，使用网络：
python3 tools/dev.py --jobs 4 xiaozhi build --profile reference-s3-lcd
python3 tools/dev.py --offline assets build
python3 tools/dev.py --offline assets check
python3 tools/dev.py preview
```

`assets setup` 只将 Pillow 13.0.0 安装到 build/container/asset-python，版本及 Linux amd64 CPython 3.12 wheel 哈希见 tools/requirements-assets.txt；不改镜像内 SDK Python 环境或镜像配方。
Native 维护模式使用 build/asset-python；素材依赖锁目前只验证固定 Linux amd64 容器，不声称支持 macOS/ARM 原生安装。

默认 base 为参考构建的 generated_assets.bin；可通过 assets build --base <仓库内路径> 选择另一份上游资源包。
生成器保留 base 中的字体和非表情资源，替换 emoji_collection 及旧表情文件；资源打包/读取均直接调用固定小智 scripts/build_default_assets.py 的 pack_assets_entries/read_assets_entries。
所有源文件逐个核对 sources.json 中的哈希后读取；输出在 assets/generated/deepseek/，由 Git 忽略。源图及生成的第三方角色图片不提交或自动发布。

## 画面、帧映射和时间

画面来自透明 spritesheet.webp；原上游预览 GIF 含明显绿边，只用作时长参考，不用其 RGB 像素。
assets/pet/deepseek.json 显式记录 8×11 网格及下表映射。通过透明区域交集对照确认对应关系，不在运行时新增自动匹配机制。

| 动作 | WebP 行 / 列（零起点） | 时长来源 | 上游 emotion 名称 |
| --- | --- | --- | --- |
| 待机 | row 0 / 0..5 | previews/idle.gif | neutral |
| 倾听 | row 6 / 0..5 | previews/waiting.gif | listening |
| 思考 | row 7 / 0..5 | previews/running.gif | thinking |
| 说话 | 复用待机 | 同待机 | speaking |
| 开心 | row 3 / 0..3 | previews/waving.gif | happy |
| 困惑 | row 5 / 0..7 | previews/failed.gif | confused |

idle 第七格没有对应预览时长，本版不用该格，不编造时序。说话只是明确的待机占位，没有嘴型或音频同步。
倾听/思考是现有 waiting/working 动作的复用，困惑实际来自 failed，仍需用户确认其表达是否合适。
素材包提供 emotion 名称，但小智当前 Application 不会自动把所有交互状态映射到这些自定义名称，留待板级/角色界面集成。

所有动作使用一个透明主体包围盒和锚点，不逐帧独立裁剪/居中。当前共同源范围 [23,5,168,203]，缩放到 158×216，放在 240×240 的 [41,12]，保留动作空间。
按 100 ms 时间格取样（10 fps 上限）；用实际 GIF duration 定位源帧，总时长向上取整至 100 ms，因此变化小于 100 ms。相同帧由 Pillow 合并为较长时长，实际独立帧率不是恒定 10 fps。
使用统一的 256 色调色板，并将其颜色预量化到 RGB565 可表示值；固定浅蓝背景合成半透明边缘。预览包含最终 GIF 的调色/缩放效果，不承诺真实屏幕色彩完全相同。
开心与困惑不写循环扩展，播放一次；其他动画循环。设备沿用上游 LvglGif/gifdec 的逐帧时长和循环处理。

## 生成物与资源预算

- assets.bin：上游 mmap 格式，可作为小智自定义素材输入。
- dc-*.gif：五段最终 GIF；说话与待机共用文件。
- index.html：包含最终 GIF 解出的 PNG 帧和时长的自包含预览，无 CDN 或外部脚本依赖。
- preview.json：来源/配置/base/模板哈希、帧时长与像素哈希、缩放范围、资源预算和动作说明。

assets check 检查生成文件哈希、上游包内 GIF/尺寸/动作映射、预览像素和时长、循环语义及源文件/配置/模板/base 是否变化；变化后重新生成。
参考 assets 分区为 8 MiB，预算来自已核对的上游参考分区，不是最终 XIAO 容量。超过预算时在写新产物前失败，保留旧产物。
一帧 RGB565 原始数据为 115200 B；上游 gifdec 的 ARGB 画布与索引帧合计约 288000 B，另需 gd_GIF 结构、LZW、LVGL 和 SPI/DMA 缓冲。此估算不是设备 RAM 峰值实测。

## 验证及参考固件入口

```sh
python3 tools/dev.py --offline test --suite tools
python3 tools/dev.py --offline assets test
# 需要先缓存完整参考依赖；初次使用不要加 --offline：
python3 tools/dev.py --offline --jobs 4 xiaozhi build --profile reference-s3-lcd --assets assets/generated/deepseek/assets.bin
```

带素材的构建使用独立 build/container/xiaozhi-reference-s3-lcd-custom/，不覆盖普通参考 sdkconfig。
构建入口复制资源到该目录并使用上游 FLASH_CUSTOM_ASSETS 路径；没有提供猜测 XIAO 引脚的烧录入口。
上游默认显示还包含顶栏/文字，240×240 预览展示的是素材画面，不是完整 LVGL 界面模拟。

CI 使用原创几何图形 fixtures 验证转换、打包、预算、输入错误、绿边回归及原设备解码器一致性，无需下载第三方角色或上传角色图像 artifact。
完整实际结果见 ASSETS_VALIDATION.md。素材来源与许可见 assets/README.md；代码 MIT 不替代角色素材许可。
