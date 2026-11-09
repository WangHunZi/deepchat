# Docker 镜像发布与 digest 更新

本仓库使用 GHCR 作为开发镜像发布位置：`ghcr.io/wanghunzi/deepchat-dev`。
发布是明确的手动操作；PR 验证、push 或 merge 不自动公开镜像，不自动修改版本锁或 merge。
首次发布已完成：[run 42576609562](https://github.com/WangHunZi/deepchat/actions/runs/42576609562)，来源为已合并的 main 提交 `721967cc5f3da8661ffa0dff60075545856c7e45`。
本次真实 digest 来自该运行的 `released-container-lock` artifact，现已写入待 review 的 `tools/container-lock.json`；package 已由所有者设为 Public。合并该锁定 PR 后，默认 setup 和 CI 直接拉取该镜像。
本地匿名拉取与构建结果见 [已发布镜像验证](IMAGE_PIN_VALIDATION.md)。以下流程保留用于后续版本更新。

## 1. 审核并合并镜像配方

Dockerfile、基础镜像 digest、Python 依赖锁及安装脚本均进入功能 PR。
PR CI 构建候选后，在同一镜像中以 offline 模式跑格式、工具测试、主机 C11/C++17 编译探测和固件构建。
通过 PR 仅代表配方和开发能力已验证，不意味着发布镜像已存在。

## 2. 从已审核的 main 手动发布

在 GitHub Actions 中选择 [Publish development image](../.github/workflows/publish-dev-image.yml)，对 `main` 执行 Run workflow。
工作流只允许 main；它重新构建并测试候选，通过后才使用仓库内置 `GITHUB_TOKEN` 的 packages:write 权限推送 GHCR。
不要求个人令牌进入仓库或聊天。registry 登录只发生在一次性 runner 上。

标签为 `recipe-<安装输入指纹>`，用于定位发布；开发命令不会消费这个可变标签。
workflow summary 输出本次真实 registry `@sha256`，artifact `released-container-lock` 提供待审查的锁文件。
首次 GHCR package 默认可见性与组织策略有关。当前 PR CI 不执行 registry 登录，因此首次提交发布 digest 锁定前，需要所有者将开发镜像 package 设为 public，以便 CI 匿名拉取。
private package 可在本地使用 Docker 自身的登录配置，脚本不读取或复制 registry 密钥；私有镜像的 CI 登录不在本轮实现及验证范围。

## 3. 提交 digest 锁定 PR

从成功发布的 summary 复制实际引用，不填写虚构摘要：

```sh
python3 tools/dev.py image pin ghcr.io/wanghunzi/deepchat-dev@sha256:<实际64位摘要>
```

该命令拉取 digest、检查镜像配方标签，然后更新 `tools/container-lock.json` 的 `image`。
将此改动作为镜像版本锁定 PR；CI 会拉取该同一 digest 并运行全部检查，由人类决定 merge。
发布和 pin 分为两个明确边界，避免把尚未发布的镜像写成可拉取依赖。

仅本机试用某个已发布 digest，可用以下命令，不修改 tracked lock：

```sh
python3 tools/dev.py image pull ghcr.io/wanghunzi/deepchat-dev@sha256:<实际64位摘要>
```

配方不匹配时命令失败；本地 tag、`latest`、省略 digest 的引用均被拒绝。失败后不会自动回退到宿主机或其他镜像。

## 4. 以后升级工具链

1. 在功能分支修改安装输入；将 tracked `image` 显式置为 `null`，表示本轮验证候选配方。
2. 本地 `image build`，完成格式、测试和实际编译；提交配方 PR 并 review。
3. 合并后手动发布，得到真实 digest，再提交锁定 PR。
4. 新版本有问题时，选择兼容的旧配方及其 digest，通过正常 PR 回退，不修改已发布镜像摘要。

Docker 原生层缓存可复用本机未变化的安装步骤；同一 CI job 只构建一次候选。
本轮不引入独立缓存服务、自动更新机器人、重试计数或自动 merge。
