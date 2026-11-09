# 已发布开发镜像锁定验证

日期：2026-11-09。范围：从成功发布的真实 artifact 锁定公开 GHCR 镜像，验证默认入口使用发布镜像，不修改安装配方或业务代码。

## 发布来源

- 发布运行：[42576609562](https://github.com/WangHunZi/deepchat/actions/runs/42576609562)，结论 success。
- 来源提交：已合并的 `main`，`721967cc5f3da8661ffa0dff60075545856c7e45`。
- 来源产物：该运行的 `released-container-lock/container-lock.json`。
- 实际引用：`ghcr.io/wanghunzi/deepchat-dev@sha256:e5e714e2cc20857ed1808374d23fcc772ff9644f6b7aa2c8441aa6c1a4b74eae`。
- 配方指纹：`0845d15310edb1b445faf20fdd1610ac6a701d74e29b2b846d5f26ca4a2604cd`，与当前安装输入匹配。

锁文件仅把 `image` 从 `null` 改为真实 registry digest；基础镜像、SDK、工具和 Python 依赖锁保持不变。没有消费可变 tag，也没有重新发布镜像。

## 本地验证

由独立测试代理执行，保留下层真实退出状态。

| 操作 | 结果 / 验证范围 |
| --- | --- |
| 临时空 Docker client config，明确本地 daemon，匿名 `pull --platform linux/amd64` | exit 0，真实下载并校验发布镜像；无需登录，未读取或改变原 registry 认证配置 |
| `python3 tools/dev.py image pin <上述真实引用>` | exit 0，实际 recipe 标签匹配后写入 tracked lock 与本地选择 |
| `python3 tools/dev.py setup` | exit 0，日志仅拉取 GHCR，没有 buildx 构建或 SDK 安装 |
| `python3 tools/dev.py --offline format --check` | exit 0 |
| `python3 tools/dev.py --offline test --suite tools` | 15/15 通过 |
| `python3 tools/dev.py --offline build --target host` | exit 0，复用相同工具链的有效主机缓存；干净 CI runner 另行运行 C11 / C++17 编译探测 |
| `python3 tools/dev.py --offline --jobs 4 build --target esp32s3 --board bringup` | exit 0，真实镜像编译工具路径位于 `/opt/deepchat`，应用最终使用 C11 |

setup 后的普通检查均在禁用网络的容器中执行，依赖由已拉取镜像提供。原生宿主机工具或旧候选镜像没有作为回退路径。
应用 BIN 170,112 bytes、bootloader 21,120 bytes、分区表 3,072 bytes，ELF/map 同时生成，宿主机所有者均为 `1000:1000`。本轮复用有效增量产物，不声称清空缓存重建。
SDK 配置阶段输出 OpenThread 子模块的 Git ownership 诊断，bringup 构建仍返回 0；本轮未修改 SDK 或扩大 Git 信任范围。

## CI 与生效边界

本轮 PR CI 会直接拉取同一固定 digest，运行离线格式、15 个工具测试、主机编译探测和 ESP32-S3 构建；准确结论以 PR checks 为准。
该路径不再进入 `image: null` 的候选构建分支。

版本锁改动由人类 review 并决定 merge；合并前不宣称默认 main 已采用新锁。
实机烧录、角色功能、音频和其他平台不是本轮范围；下一阶段仍为 P1。
