# 构建与开发入口

当前产品已按用户决定改为基于小智二开，允许 C++；请先看 [小智接入](XIAOZHI.md)。本文中的 `build --target esp32s3 --board bringup` 是历史 P0 最小启动应用，不包含小智或角色图片。

默认使用 Docker 开发镜像。本地、云环境和 CI 共用镜像配方及同一个命令入口；宿主机需要 Docker（含 Buildx）、Git 和 Python 3.10+，不需要安装 SDK、C/C++ 编译器或项目 Python 包。
当前验证平台为 Linux amd64；Docker Desktop / ARM 模拟运行、串口烧录尚未验证。
`bringup` 固件只输出启动信息，不代表已经适配 XIAO Plus，角色、音频和最终板级配置仍按 [Plan.md](../Plan.md) 实现。

## 首次准备和日常开发

在仓库根目录执行：

```sh
python3 tools/dev.py setup
python3 tools/dev.py --offline format --check
python3 tools/dev.py --offline test --suite tools
python3 tools/dev.py --offline build --target host
python3 tools/dev.py --offline --jobs 4 build --target esp32s3 --board bringup
```

`setup` 直接拉取锁文件 `image` 固定的公开 GHCR 镜像，验证配方标签后选择同一个 registry digest；不在宿主机安装 SDK，也不重新构建工具镜像。CI 使用同一引用。
日常 format/test/build 直接复用已选镜像，不重新安装工具。重复 setup 由 Docker 复用已拉取的有效层。
维护者仍可显式 `image build` 构建候选，其本地内容 ID 与 registry digest 是不同标识；候选不自动替换 tracked 发布锁。

`--offline` 为容器禁用外部网络。历史基线所需工具都在镜像中；小智业务组件不在工具镜像里，首次 `xiaozhi build` 必须允许网络下载锁定依赖。缓存完整后是否可离线构建以小智验证报告为准；setup / image build 也需要网络。
`--jobs` 是顶层参数，放在子命令之前，默认 4。格式操作可选文件，例如：

```sh
python3 tools/dev.py format tools/dev.py tools/container.py
python3 tools/dev.py --offline format --check apps/esp32s3/main/Main.c
```

绝对路径限于当前 checkout，并在容器边界映射为 `/workspace/...`；仓库外文件被拒绝。
格式范围只包括 `apps/src/include/tests/tools` 中的自有 C/C++/Python，不处理依赖或生成目录。

## 镜像内容、版本与运行边界

- `docker/Dockerfile` 使用 [container-lock.json](../tools/container-lock.json) 中的具体 amd64 基础镜像 digest。
- 基础镜像为 Python 3.12.14 Bookworm，提供 Git 2.39.5、GCC/G++ 12.2.0 和 Make 4.3，不在构建时从系统仓库安装这些工具。
- ESP-IDF、交叉编译器、格式工具和 Python 依赖仍以 [sdk-lock.json](../tools/sdk-lock.json)、[host 锁](../tools/requirements-host.txt)、[IDF Python 锁](../tools/requirements-idf.txt) 为依据。
- 官方 IDF 约束快照见 [idf-constraints.txt](../tools/idf-constraints.txt)，官方包哈希、TLS 和 Python 约束检查均保留。
- 镜像只含安装入口及工具链，不含固件业务源码、宿主机 SDK、本地配置、GitHub 凭据或会话 CA。

工具安装在 `/opt/deepchat`；checkout 挂载到 `/workspace`，新产物写入 `build/container/`。
宿主机原有 `build/host`、`build/esp32s3-bringup`、`.sdk` 和 `.venv` 均不作为容器工具来源，也不复制或删除。
容器产物使用独立 CMake 缓存，避免复用宿主机编译器路径。

运行时使用调用者 UID/GID，不根据 daemon 的 rootless 标签推测挂载映射，也不 chown checkout。当前受管 rootless 环境的挂载保留宿主 UID；验收依据为实际产物所有者与可写性。其他 rootless 用户命名空间布局尚未验证，不自动改为容器 root 或放宽工作区 Git ownership 检查。
不使用 privileged、host network 或 Docker socket 挂载。只支持能够访问当前 checkout 的本地 daemon；远程 daemon 的文件挂载需自行提供相同目录，未验证。

镜像内安装位置通过 `DC_TOOL_ROOT`、构建目录通过 `DC_BUILD_ROOT` 指定；由镜像设置，不要求用户手工配置。
Git 只对镜像内固定 SDK 路径设置 safe.directory，不使用 `safe.directory=*`。

## 配方变化和发布镜像

安装输入会计算内容指纹，包含 Dockerfile、构建上下文白名单、安装脚本和版本锁。当前已选镜像记录在被忽略的 `config/local/container-image.json`。
依赖变化后，旧选择明确报错，不自动换成未知镜像或使用宿主机工具。重新构建候选：

```sh
python3 tools/dev.py image build
```

镜像 ID 来自 Docker 的成功构建结果；发布镜像按 digest 拉取时检查其配方标签是否匹配当前 checkout。
安装输入相同并不意味着两次独立构建得到完全相同的镜像字节；需要不同机器使用完全相同的镜像时，使用已发布并固定的 registry digest。

当前发布来源与以后更新流程见 [Docker 镜像发布](DOCKER_RELEASE.md)。运行验证见 [已发布镜像锁定验证](IMAGE_PIN_VALIDATION.md)；是否已在 main 生效以锁定 PR 的 merge 状态为准。

## CI

[构建工作流](../.github/workflows/build.yml) 在一个 job 中只准备一次镜像，所有格式、测试及编译通过其不可变内容 ID / digest 运行。格式、工具测试及历史基线编译禁用网络；小智参考构建使用网络下载其锁定业务组件。
已固定发布 digest 时 CI 直接拉取；首次 bootstrap 或显式更新镜像配方时构建候选。此时 CI 仍需构建工具镜像，不能声称已省掉首次安装。
工作流上传镜像选择元数据、日志、业务组件锁、小智参考板 BIN/ELF/map/素材及历史 bringup 产物；参考板产物不能作为 XIAO 可烧录交付。
当前仍未提供完整的实机烧录发布包；板级确认在 P2，烧录与实机验收在 P6。

当前结果见 [已发布镜像验证](IMAGE_PIN_VALIDATION.md)；历史候选构建见 [Docker 报告](DOCKER_VALIDATION.md)，native 基线见 [P0 报告](P0_VALIDATION.md)。

## Native 维护入口

原有 P0 入口保留为显式维护模式：

```sh
python3 tools/dev.py --native setup --host-only
python3 tools/dev.py --native format --check
python3 tools/dev.py --native test --suite tools
python3 tools/dev.py --native build --target host
```

仅维护模式需要宿主机 Python 3.12、编译器与 venv/pip。镜像构建调用相同安装实现 `tools/native.py`，不维护第二套安装逻辑。
完整 native 安装为 `python3 tools/dev.py --native setup`。`setup --host-only` 不适用于默认容器模式，会明确拒绝，避免误以为只安装主机工具却触发完整下载。
容器内业务命令以 `--native` 执行，读取镜像的固定工具目录；不会递归启动 Docker。
P1 尚无角色核心或公共 C API 套件，因此 `test --suite unit` 与 `test --suite c-api-compat` 仍应因零测试失败，不能算业务测试通过。

## 企业或云代理 CA

镜像构建和容器运行不继承宿主机证书仓库。可以指定包含正常根证书和代理 CA 的联合 bundle：

```sh
python3 tools/dev.py --ca-bundle /path/to/combined-ca.pem image build
python3 tools/dev.py --ca-bundle /path/to/combined-ca.pem build --target host
```

受管云环境设置 `CODEX_PROXY_CERT` 时，自动使用其系统联合 bundle；保留 Docker 配置提供的代理与 registry 认证，不打印配置或凭据。
构建时使用 BuildKit secret 挂载，运行时只读挂载；不 COPY 会话证书进镜像，也不关闭 TLS 校验。
`--offline` 不影响 Docker daemon 首次拉取镜像所需网络；registry 下载由 daemon 自身代理和信任配置管理。

代码采用 [MIT](../LICENSE)；第三方依赖保留上游许可，角色素材许可另行记录。
