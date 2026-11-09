#include <cstdio>
#include <cstdlib>

#include "DCDisplayTestPattern.h"

#define CHECK(condition)                                                                                               \
    do {                                                                                                               \
        if (!(condition)) {                                                                                            \
            std::fprintf(stderr, "%s:%d: %s\n", __FILE__, __LINE__, #condition);                                       \
            std::exit(1);                                                                                              \
        }                                                                                                              \
    } while (0)

int main() {
    CHECK(kDCDisplayTestWidth == 240 && kDCDisplayTestHeight == 240);
    // 小端 DMA 缓冲的两个字节必须是 ST7789 需要的 RGB565 高字节、低字节。
    constexpr uint16_t expectedWire[] = {0x00f8, 0xe007, 0x1f00, 0xffff, 0x0000};
    for (int y = 17; y <= 222; ++y) {
        for (int x = 1; x < 239; ++x) {
            CHECK(DCDisplayTestPixel(x, y) == expectedWire[x / 48]);
        }
    }
    for (int position = 0; position < 240; ++position) {
        CHECK(DCDisplayTestPixel(position, 0) == 0xffff);
        CHECK(DCDisplayTestPixel(position, 239) == 0xffff);
        CHECK(DCDisplayTestPixel(0, position) == 0xffff);
        CHECK(DCDisplayTestPixel(239, position) == 0xffff);
    }
    CHECK(DCDisplayTestPixel(8, 8) == 0x00f8);
    CHECK(DCDisplayTestPixel(231, 8) == 0xe007);
    CHECK(DCDisplayTestPixel(8, 231) == 0x1f00);
    CHECK(DCDisplayTestPixel(231, 231) == 0xe0ff);
    return 0;
}
