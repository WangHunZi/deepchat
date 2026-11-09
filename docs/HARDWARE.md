# XIAO ESP32S3 Plus + ST7789 首次接线与验收

本页对应 `xiao-esp32s3-plus-st7789` profile。用户确认屏幕是 ST7789、SPI、240×240；实物照片 PCB 标记 TK013F0320，排针为 CS / SCK / MOSI / DC / RST / BL / 3V3 / GND。背面 RS 对应 DC、RESET 对应 RST。外形长宽不能代替有效显示区域尺寸。

本次已提供目标板配置和测试图入口，尚无实机烧录结果。下面 GPIO 是**本项目分配的接线方案**，不是屏幕厂家默认接线。请按 GPIO 和 Plus 焊盘双重核对。

## 资料与已确认边界

- [Seeed 官方入门页](https://wiki.seeedstudio.com/xiao_esp32s3_getting_started/) 的 XIAO ESP32-S3 Plus 小节：16 MB Flash、8 MB PSRAM，与普通 XIAO 的 8 MB Flash 区分。
- [Plus 正面引脚图](https://files.seeedstudio.com/wiki/SeeedStudio-XIAO-ESP32S3/img/XIAO_ESP32-S3_Plus_front_pinout.png)、[背面引脚图](https://files.seeedstudio.com/wiki/SeeedStudio-XIAO-ESP32S3/img/XIAO_ESP32-S3_Plus_back_pinout.png)。
- [Plus V1.1 官方原理图](https://files.seeedstudio.com/wiki/SeeedStudio-XIAO-ESP32S3/res/XIAO_ESP32S3_Plus_V1.1_SCH_260115.pdf)，图签日期 2026-01-15；核对模块及排针映射，实物版本仍需匹配。
- 当前使用 QIO Flash、80 MHz Octal PSRAM、原生 USB Serial/JTAG 控制台。GPIO43/44 已分配给音频，不能再接 UART 转串口。
- [ESP32-S3 Datasheet](https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf) §3.3 说明 ROM 默认向 UART0 与 USB 输出启动日志；[锁定 SDK 引脚表](https://github.com/espressif/esp-idf/blob/fff9895c82d744c7237be8847347bdd1b07c6643/components/soc/esp32s3/include/soc/uart_pins.h#L10-L11) 定义 GPIO43 为 UART TX、44 为 RX。USB 控制台切换在二级 bootloader 生效，因此麦克风 SD 选 GPIO44，功放 DIN 选 GPIO43，避免把 ROM 输出连接到麦克风输出。此为启动方向核对，并非实测争用结论。
- 屏幕照片可以确认接口文字，不能确认 BL 内部限流、驱动晶体管或有效电平。**BL 暂不接 MCU GPIO，也不把 BL 直接短接 3V3 作为通用接法。** 首次点亮前，按卖家的本型号原理图确认 BL 是逻辑输入还是 LED 电源，并按其限流/驱动要求接线；后续确认后再补 PWM。

## 先只接屏幕

断电接线，主板 USB 供电，屏幕使用主板 3V3 和公共 GND；不要把屏幕 3V3 接到 5V。SPI 为只写，无 MISO。

| 屏幕引脚 | XIAO Plus 焊盘 | ESP32-S3 GPIO | 说明 |
| --- | --- | --- | --- |
| CS | D0 | 1 | 片选 |
| SCK | D8 | 7 | SPI 时钟 |
| MOSI | D10 | 9 | SPI 数据 |
| DC / RS | D1 | 2 | 数据/命令 |
| RST / RESET | D3 | 4 | 复位 |
| 3V3 | 3V3 | — | 3.3 V 电源 |
| GND | GND | — | 公共地 |
| BL | 先按模块资料确认 | 未分配 | 不能凭照片认定为可直接驱动的逻辑输入 |

参数集中在 `src/xiaozhi/main/boards/deepchat-xiao-plus/DCBoardConfig.h`：20 MHz、SPI mode 0、RGB565、RGB 色序、反色开启、零偏移、不镜像、不交换 XY。这些是**初始调屏参数**，未冒充本型号实测值。测试图和角色模式共用同一初始化。

## 构建和烧录测试图

```sh
python3 tools/dev.py setup
# 首次业务组件下载需要联网；已有缓存可加 --offline。
python3 tools/dev.py --jobs 4 xiaozhi build --profile xiao-esp32s3-plus-st7789 --display-test
```

命令最后打印 `XIAO build complete: .../build`。日志中的 `/workspace/` 是容器内仓库根目录；宿主机对应当前仓库根目录。源树和构建隔离在 `build/container/xiaozhi-pet/<内容指纹>/`；该目录名是历史命名，测试图不会应用角色补丁。修改板级代码、profile 或测试模式会得到新目录，避免旧 sdkconfig 残留。原上游子模块不被修改。

测试模式不需要角色素材、麦克风、功放、按键、Wi-Fi 或服务器。它在板级构造期间显示静态测试图并阻塞后续应用初始化；没有音频、网络启动，也没有自动切入角色。

将打印目录内下列文件复制到**连接设备的电脑**，保持相对路径；或下载 PR CI 的 `xiao-display-test` artifact（保留内部相对路径）：

- `flash_args`、`flasher_args.json`、`sdkconfig`
- `bootloader/bootloader.bin`、`partition_table/partition-table.bin`
- `ota_data_initial.bin`、`xiaozhi.bin`

以真正包含 `flash_args` 的目录为工作目录，安装本机 esptool 后烧录。下面端口只是示例，Windows 改成实际 COM 号；先关闭占用端口的串口监视器：

```sh
python -m pip install esptool==5.6.0
python -m esptool --chip esp32s3 --port /dev/ttyACM0 write-flash @flash_args
```

偏移和写入参数来自 ESP-IDF 生成的 `flash_args`，不要手动猜地址。无需整片 erase-flash。首次写入会更新分区、应用和 OTA 初值，已有其他固件的数据布局不能视为兼容。无法连接时按住 BOOT、点按 RESET、释放 BOOT，再选择重新出现的端口；BOOT 仅用于 ROM 下载，不承担语音按键。

控制台通过 USB Serial/JTAG，串口监视器可用 115200。日志“测试图已提交”表示 SPI 提交被驱动接受；屏幕是只写接口，仍需肉眼验收。

## 肉眼检查什么

| 检查项 | 正确画面 | 异常时核对 |
| --- | --- | --- |
| 色序/字节序 | 从左到右红、绿、蓝、白、黑五等宽竖条 | 红蓝互换先核对 RGB/BGR；整体怪色再核对反色，避免同时改多项 |
| 裁切 | 240×240 四周均有一像素白边 | 偏移、有效尺寸、排线/初始化 |
| 方向 | 左上红、右上绿、左下蓝、右下黄的内侧小方块 | 镜像、XY 交换、实物安装方向 |
| 稳定性 | 静态保持，无闪烁、随机像素 | 接地、线长、接触、供电，再尝试降低 SPI 时钟 |
| 无画面 | 背光与 LCD 分开检查 | BL 接法、3V3、RST、CS、DC、时钟/数据，观察 USB 错误日志 |

黑屏不能仅凭 SPI API 成功认定屏幕坏了。请保留正对实屏照片和启动日志；一次只改一个显示参数，然后重新构建测试图。

## 角色固件及音频预留接线

测试图通过后，再使用已经完成的角色素材和 UI：

```sh
python3 tools/collect_assets.py --pack codex-pet
python3 tools/dev.py assets setup
python3 tools/dev.py --offline assets build
python3 tools/dev.py --offline --jobs 4 xiaozhi build --profile xiao-esp32s3-plus-st7789 --pet --assets assets/generated/deepseek/assets.bin
```

角色构建使用同一 LCD 配置、现有角色补丁，以及上游 `NoAudioCodecSimplex`、`Button`。它是正常小智应用，首次会进入配网/激活诊断界面；服务端尚未配置时不能承诺上电立即常驻角色或完成对话。角色素材仍为本地资源，不自动随 CI 分发。说话动画仍为待机占位。

角色固件烧录时除测试图文件外，还要保留其输出目录的 `configured_assets.bin`；使用**该次构建自己的** `flash_args`，不要混用测试模式或其他 profile 的文件。

下表是本次软件配置选用的音频/按键分配，尚未实测音量、增益、录音幅度或按键对话。屏幕测试不依赖它们；扬声器阻抗/功率及 MAX98357A 模块供电仍待确认，暂不连接扬声器进行大音量测试。

| 模块信号 | Plus 焊盘 | GPIO | 软件约定 |
| --- | --- | --- | --- |
| INMP441 SCK | D5 | 6 | 输入 I²S，16 kHz |
| INMP441 WS | D4 | 5 | 独立录音时钟 |
| INMP441 SD | D7 | 44 | 输入；L/R 接 GND 选择左声道 |
| INMP441 VDD / GND | 3V3 / GND | — | 3.3 V；按实际模块去耦 |
| MAX98357A DIN | D6 | 43 | 输出 I²S，24 kHz，左声道 |
| MAX98357A BCLK | D12（背面焊盘） | 39 | 与麦克风分离的输出时钟 |
| MAX98357A LRC | D13（背面焊盘） | 40 | 需要焊接背面焊盘，不与 D12 对调 |
| 外接常开按键 | D9 ↔ GND | 8 | 内部上拉，按下调用 StartListening，松开调用 StopListening |

MAX98357A 的 VIN、SD/MODE、GAIN 和扬声器接法应按具体模块/负载资料确认，所有模块共地。输出是桥接扬声器端，不能把某个扬声器输出端当 GND。不同输入/输出采样率需要独立 I²S 时钟，不能为省引脚直接并接。

未使用 D2/GPIO3（启动绑带）、D16/GPIO10（板载电池采样）、USB GPIO19/20；不启用板载 LED、相机、SD 卡或 PWM 背光。上游当前 `HandleStopListeningEvent` 不处理 Connecting：连接慢时短按并在连接中松开，后续可能仍进入手动停止录音。此处只交付按键事件接线，**完整 PTT 行为尚未验收**；后续音频/服务集成阶段需在实际调用点修复并验证该场景。

首次验收顺序仍为：测试图 → 配网/角色 → 固定音频 → 录音回放 → 按键对话；后面步骤需要下一阶段实现与实机记录。
