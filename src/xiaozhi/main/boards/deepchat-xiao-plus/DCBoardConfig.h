#ifndef DC_BOARD_CONFIG_H
#define DC_BOARD_CONFIG_H

#include <driver/gpio.h>

// 项目分配的接线；D 标号按 Seeed Plus 官方引脚表核对，详见 docs/HARDWARE.md。
inline constexpr gpio_num_t kDCLcdCs     = GPIO_NUM_1;   // D0
inline constexpr gpio_num_t kDCLcdDc     = GPIO_NUM_2;   // D1
inline constexpr gpio_num_t kDCLcdReset  = GPIO_NUM_4;   // D3
inline constexpr gpio_num_t kDCLcdClock  = GPIO_NUM_7;   // D8
inline constexpr gpio_num_t kDCLcdMosi   = GPIO_NUM_9;   // D10
inline constexpr gpio_num_t kDCPttButton = GPIO_NUM_8;   // D9，外接常开按键到 GND
inline constexpr gpio_num_t kDCMicWs     = GPIO_NUM_5;   // D4
inline constexpr gpio_num_t kDCMicClock  = GPIO_NUM_6;   // D5
inline constexpr gpio_num_t kDCMicData   = GPIO_NUM_44;  // D7，UART RX，避免 ROM TX 连接麦克风输出
inline constexpr gpio_num_t kDCSpkData   = GPIO_NUM_43;  // D6，UART ROM TX 连接功放输入
inline constexpr gpio_num_t kDCSpkClock  = GPIO_NUM_39;  // D12，背面焊盘
inline constexpr gpio_num_t kDCSpkWs     = GPIO_NUM_40;  // D13，背面焊盘

// 初始调屏参数，尚需实际模块验收；BL 未接入 GPIO。
inline constexpr int  kDCLcdClockHz = 20 * 1000 * 1000;
inline constexpr bool kDCLcdInvert  = true;
inline constexpr bool kDCLcdMirrorX = false;
inline constexpr bool kDCLcdMirrorY = false;
inline constexpr bool kDCLcdSwapXY  = false;
inline constexpr int  kDCLcdOffsetX = 0;
inline constexpr int  kDCLcdOffsetY = 0;

#endif
