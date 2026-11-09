#ifndef DC_DISPLAY_TEST_PATTERN_H
#define DC_DISPLAY_TEST_PATTERN_H

#include <cstdint>

inline constexpr int kDCDisplayTestWidth  = 240;
inline constexpr int kDCDisplayTestHeight = 240;

/**
 * @brief 生成测试图中一个像素的 SPI 字节序 RGB565 值。
 * @param[in] x 已成立的画布横坐标，范围 0..239。
 * @param[in] y 已成立的画布纵坐标，范围 0..239。
 * @return 在 ESP32 小端内存中可直接提交给 LCD 的大端 RGB565 数据。
 * @note 纯函数，无状态、无阻塞；白框、四色角标用于核对裁切与方向。
 */
constexpr uint16_t DCDisplayTestPixel(int x, int y) {
    constexpr uint16_t colors[] = {0xf800, 0x07e0, 0x001f, 0xffff, 0x0000};
    uint16_t           color    = colors[x / 48];
    if (x == 0 || y == 0 || x == 239 || y == 239) {
        color = 0xffff;
    } else if (x < 17 && y < 17) {
        color = 0xf800;
    } else if (x > 222 && y < 17) {
        color = 0x07e0;
    } else if (x < 17 && y > 222) {
        color = 0x001f;
    } else if (x > 222 && y > 222) {
        color = 0xffe0;
    }
    return static_cast<uint16_t>((color << 8) | (color >> 8));
}

#endif
