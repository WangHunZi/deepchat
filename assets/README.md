# DeepSeek 娘素材收集

本项目角色确定为蓝发鲸鱼女仆 DeepSeek 娘。这里记录两套不同画风的候选素材，不把它们当作同一套连续动画混用。
固定来源、版本及文件 SHA-256 见 [sources.json](sources.json)；原文件下载到被 Git 忽略的 `assets/local/`。
本目录提交来源和工具，不将第三方图像纳入本项目 MIT 许可，也不将其自动打包进公开固件。

## 下载与检查

在仓库根目录执行，工具仅使用 Python 标准库，无需 Pillow、SDK 或 Docker：

```sh
python3 tools/collect_assets.py
python3 tools/collect_assets.py --check
# 也可只收集一套：
python3 tools/collect_assets.py --pack codex-pet
python3 tools/collect_assets.py --pack emotes
```

默认收集十三个文件，约 14.6 MB（13.9 MiB），包含元数据、原始图片及各自 README 来源快照。
下载使用固定 commit URL，检查长度与 SHA-256 后才保存；不追随 main 或 latest。
已有文件通过检查即复用；本地文件不符时报告错误并保留文件，不自动覆盖修改。
需要重新下载时，先自行备份并删除对应文件，再运行收集。`--check` 完全离线，缺失或内容不符以非零状态退出。
工具不负责安装 Codex Pet，不向用户的 `~/.codex/` 写入文件。
这是原始素材收集入口。转换与预览已接入 `python3 tools/dev.py assets build`、`assets check`、`preview`，使用方式见 [240×240 素材说明](../docs/ASSETS.md)。

## 两套候选

| 本地目录 | 来源与固定版本 | 当前收集内容 | 用途 |
| --- | --- | --- | --- |
| `assets/local/codex-pet/` | [xpy12367/codex-pet-DeepSeek-girl](https://github.com/xpy12367/codex-pet-DeepSeek-girl/tree/27843e4ba86cc439d29aa1c6b0591f206fa2514f) | `pet.json`、透明 WebP 精灵图、动作联系表、五个时长参考 GIF、README | 优先用于全身桌宠 |
| `assets/local/emotes/` | [BrickAZ/deepseek-chan-emotes](https://github.com/BrickAZ/deepseek-chan-emotes/tree/0f970d9be7b33c6f7eae0f259062c8e3d40b7b3a) | 思考、点赞、打游戏三个 GIF 与 README | 比较大头表情的可读性 |

Codex Pet 精灵图实测 1536×2288、RGBA，按上游 8×11 网格得到每格 192×208。
原尺寸放进 240×240 画布时，左右各 24、上下各 16 像素；这只是网格尺寸，不代表角色主体占满每格。
后续检查透明留白，按整段动画统一裁剪范围与锚点，不能每帧独立裁剪后居中而导致抖动。
各行动画的网格位置、有效帧数和帧时长仍需在转换阶段核对，不能直接把 88 格等同于一个动画。

三个 GIF 实测均为 500×500：思考 32 帧、点赞 32 帧、打游戏 26 帧。
上游声明导出目标 30 fps；转换器必须读取实际逐帧 duration，不能假定每帧精确为 1/30 秒。
完整 161 个 GIF 在上游 [Releases](https://github.com/BrickAZ/deepseek-chan-emotes/releases) 的附件中，本次只收集三个候选，没有下载全量包。
后续若需更多动作，明确选择文件并更新版本、来源和校验值，不使用浮动 latest 下载作为可复现输入。

## 第一轮动作选择

当前素材已按下列方式提供预览和资源包；设备状态自动事件映射仍待板级集成：

| 产品动作 | 优先候选 | 尚需处理 |
| --- | --- | --- |
| 待机 | Codex Pet idle | 核对帧顺序、循环接缝及主体尺寸 |
| 倾听 | Codex Pet waiting / 环视 | 选择视线朝向；尚无专用倾听动画 |
| 思考 | Codex Pet working；GIF thinking 用于画风比较 | 选定主画风后再固定映射 |
| 说话 | 明确复用待机占位 | 没有嘴型帧，不宣称支持语音口型 |
| 开心 | Codex Pet waving / jumping | 区分单次动作与循环 |
| 困惑 | Codex Pet failed | 检查语义，避免把每次网络错误演成夸张失败 |

当前基于小智二开，复用其 GIF 播放和资源格式；不恢复原自研 C11 状态核心路线。当前转换与预览见 [docs/ASSETS.md](../docs/ASSETS.md)。
全身用于待机和大动作；表情特写优先使用合适的原图，不直接放大小尺寸全身图来承诺清晰度。
画面使用透明 WebP（原预览 GIF 存在绿边，仅取时长），输出 GIF 由小智现有解码器播放；预览从同一最终 GIF 解出。统一调色板预量化 RGB565，采样上限 10 fps。
带资源参考构建已验证，最终板型、显示 UI 叠层和实屏尚未验收。

## 来源与许可记录

- Codex Pet 作者/整理者：GitHub `xpy12367`；上游说明为非官方同人项目，与 DeepSeek 官方无隶属或背书关系。当前未找到明确素材再分发许可。
- GIF 整理者：GitHub `BrickAZ`。其 README 指向 Steam 创意工坊角色 [蓝色大肥鱼](https://steamcommunity.com/sharedfiles/filedetails/?id=3807575879)，工坊作者 [飞天豆之助](https://steamcommunity.com/profiles/76561199781918783)。
- GIF 使用 [EmoteLab](https://emotelab.app/) 导出；适用条件见上游声明及 [EmoteLab EULA](https://emotelab.app/eula/)。上游明确未额外授予第三方角色、模型、内置动画的许可。
- 保留下载目录中的上游 README。学习用途和代码 MIT 不会自动改变第三方素材的许可；公开打包时单独确认并记录适用授权。

## 生图与 GIF

当前会话可用的生图接口支持静态图片生成和编辑，没有直接输出 GIF、视频或带帧时序动画的接口。
因此本次没有生成 GIF，也没有用静态图冒充连续动画；其他 ChatGPT 产品界面的能力不能据此推定为本工具能力。

后续可用生图补充角色设定图、表情参考或关键帧，然后筛选、校准锚点并通过同一转换器制作帧动画。
生成多格图并不保证服装、脸型、鲸尾与动作连续；新增动画仍需逐帧检查透明边缘、角色一致性、循环接缝及 240×240 下的可读性。
生成或编辑第三方角色素材也要保留参考来源，不将处理后的素材自动标为 MIT。
