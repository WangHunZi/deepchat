# DeepChat 交接入口

开始任务前依次阅读 `Rules.md`、`STYLE_GUIDE.md` 和 `Plan.md`，再阅读当前阶段相关文档。

- 产品是 DeepSeek 娘实体桌宠。用户已选择允许 C++、基于小智二开；先读更新的 Plan.md 和 docs/XIAOZHI.md，不恢复旧的自研状态机与 HTTP/WAV 后端路线。
- 已有 P0 基线、素材来源收集、转换与 240×240 预览，说明见 docs/ASSETS.md；说话仍为待机占位；角色界面及事件联动见 docs/ROLE_UI.md。小智参考工程与最终 XIAO 适配分别验收。旧 bringup 仍只输出启动信息；参考构建不得作为目标板可烧录交付。
- 按 `Plan.md` 中的阶段依赖实现；每阶段交付实现、真实调用方、必要测试和文档，不提前创建无人调用的框架。
- 默认使用 Docker 开发入口，工具链与源码分离；首次 registry 发布和 digest 锁定按 docs/DOCKER_RELEASE.md 人工触发，不自动发布或 merge。
- 使用当前 checkout；云任务已经隔离，除非用户要求，不创建 Git worktree。
- 自有模块命名、中文 API 契约和格式遵循本地规范；小智及第三方库保留上游 C++ 实现、命名和契约，不为统一风格改写上游。
- 按 `STYLE_GUIDE.md`，编译与测试交给测试子代理；不支持子代理时明确记录限制并安排独立测试任务。
- 硬件未知项阻塞板级定版和实机结论，不阻塞核心、素材工具、后端和主机测试。
- 禁止猜测引脚并发布为已确认接线；禁止把 mock、交叉编译或桌面预览描述为实机通过。
- 阶段结束更新 `Plan.md` 的交接表；记录命令、测试数量、产物、失败、跳过及未运行原因。
- 实现过程中按逻辑步骤创建本地 commit，供用户逐项 review；PR 按完整功能或可独立验证的子功能组织，可包含多个 commit，一个较大功能也可分为多个依赖 PR。
- PR 提供功能目标、依赖、commit 阅读顺序与验证结果；用户决定是否 merge，AI 不自行 merge 或开启自动合并。
- 当前本地 commit 授权不等于任意 push 或发布授权；用户要求提交 PR 时可推送对应功能分支并创建 PR。不修改或发布云环境配置。

角色构建通过 --pet 显式选择，在 build 下准备隔离的上游补丁副本；自有叠加头文件位于 src/xiaozhi，禁止直接改子模块后声称已交付补丁。主机入口 xiaozhi test 复用真实 FSM/LVGL/GIF，不能替代 FreeRTOS/音频/网络或实机验收。

XIAO Plus / ST7789 240×240 已有独立 --display-test 与 --pet 两种目标板构建，接线/烧录见 docs/HARDWARE.md，独立验证见 docs/XIAO_BOARD_VALIDATION.md。测试图 CI artifact 不含角色素材。屏幕 BL 电路、音频功放负载、实机仍未确认；上游 Connecting 中松开 PTT 的边界已记录，后续音频交互阶段需修复并验收。不要将参考板或交叉编译当作实机通过。
