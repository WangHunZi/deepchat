#include <driver/spi_common.h>
#include <esp_heap_caps.h>
#include <esp_lcd_panel_io.h>
#include <esp_lcd_panel_ops.h>
#include <esp_lcd_panel_vendor.h>
#include <esp_log.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

#include "DCBoardConfig.h"
#include "DCDisplayTestPattern.h"
#include "application.h"
#include "button.h"
#include "codecs/no_audio_codec.h"
#include "display/lcd_display.h"
#include "wifi_board.h"

/** @brief 复用小智 LCD、独立 I²S 和按键实现的 Plus 板级入口，生命周期为设备运行期。 */
class DCXiaoPlusBoard : public WifiBoard {
private:
    LcdDisplay *display = nullptr;

    void InitializeDisplay() {
        spi_bus_config_t bus = {};
        bus.mosi_io_num      = kDCLcdMosi;
        bus.miso_io_num      = GPIO_NUM_NC;
        bus.sclk_io_num      = kDCLcdClock;
        bus.quadwp_io_num    = GPIO_NUM_NC;
        bus.quadhd_io_num    = GPIO_NUM_NC;
        bus.max_transfer_sz  = kDCDisplayTestWidth * kDCDisplayTestHeight * sizeof(uint16_t);
        ESP_ERROR_CHECK(spi_bus_initialize(SPI3_HOST, &bus, SPI_DMA_CH_AUTO));

        esp_lcd_panel_io_spi_config_t ioConfig = {};
        ioConfig.cs_gpio_num                   = kDCLcdCs;
        ioConfig.dc_gpio_num                   = kDCLcdDc;
        ioConfig.spi_mode                      = 0;
        ioConfig.pclk_hz                       = kDCLcdClockHz;
        ioConfig.trans_queue_depth             = 10;
        ioConfig.lcd_cmd_bits                  = 8;
        ioConfig.lcd_param_bits                = 8;
        esp_lcd_panel_io_handle_t io           = nullptr;
        ESP_ERROR_CHECK(esp_lcd_new_panel_io_spi(SPI3_HOST, &ioConfig, &io));

        esp_lcd_panel_dev_config_t config = {};
        config.reset_gpio_num             = kDCLcdReset;
        config.rgb_ele_order              = LCD_RGB_ELEMENT_ORDER_RGB;
        config.bits_per_pixel             = 16;
        esp_lcd_panel_handle_t panel      = nullptr;
        ESP_ERROR_CHECK(esp_lcd_new_panel_st7789(io, &config, &panel));
        ESP_ERROR_CHECK(esp_lcd_panel_reset(panel));
        ESP_ERROR_CHECK(esp_lcd_panel_init(panel));
        ESP_ERROR_CHECK(esp_lcd_panel_invert_color(panel, kDCLcdInvert));
        ESP_ERROR_CHECK(esp_lcd_panel_swap_xy(panel, kDCLcdSwapXY));
        ESP_ERROR_CHECK(esp_lcd_panel_mirror(panel, kDCLcdMirrorX, kDCLcdMirrorY));
#if CONFIG_DC_DISPLAY_TEST
        ESP_ERROR_CHECK(esp_lcd_panel_set_gap(panel, kDCLcdOffsetX, kDCLcdOffsetY));
        ESP_ERROR_CHECK(esp_lcd_panel_disp_on_off(panel, true));
        RunDisplayTest(panel);
#else
        display = new SpiLcdDisplay(io,
                                    panel,
                                    kDCDisplayTestWidth,
                                    kDCDisplayTestHeight,
                                    kDCLcdOffsetX,
                                    kDCLcdOffsetY,
                                    kDCLcdMirrorX,
                                    kDCLcdMirrorY,
                                    kDCLcdSwapXY);
#endif
    }

#if CONFIG_DC_DISPLAY_TEST
    [[noreturn]] void RunDisplayTest(esp_lcd_panel_handle_t panel) {
        auto pixels = static_cast<uint16_t *>(heap_caps_malloc(
            kDCDisplayTestWidth * kDCDisplayTestHeight * sizeof(uint16_t), MALLOC_CAP_DMA | MALLOC_CAP_INTERNAL));
        ESP_ERROR_CHECK(pixels == nullptr ? ESP_ERR_NO_MEM : ESP_OK);
        for (int y = 0; y < kDCDisplayTestHeight; ++y) {
            for (int x = 0; x < kDCDisplayTestWidth; ++x) {
                pixels[y * kDCDisplayTestWidth + x] = DCDisplayTestPixel(x, y);
            }
        }
        ESP_ERROR_CHECK(esp_lcd_panel_draw_bitmap(panel, 0, 0, kDCDisplayTestWidth, kDCDisplayTestHeight, pixels));
        ESP_LOGI("DCXiaoPlus", "[Board::DisplayTest]: 测试图已提交；检查红绿蓝白黑竖条、白边及四色角标");
        // SPI 异步读取缓冲；测试模式终身保留且不再改写，不引入额外同步队列。
        // 停在板级初始化中，Application 尚未启动音频、配网或服务端连接。
        for (;;) {
            vTaskDelay(pdMS_TO_TICKS(1000));
        }
    }
#endif

public:
    /** @brief 在应用初始化任务中初始化显示；测试模式停留于测试图，不初始化音频和按键。 */
    DCXiaoPlusBoard() {
        InitializeDisplay();
#if !CONFIG_DC_DISPLAY_TEST
        static Button pttButton(kDCPttButton);
        pttButton.OnPressDown([]() { Application::GetInstance().StartListening(); });
        pttButton.OnPressUp([]() { Application::GetInstance().StopListening(); });
#endif
    }

    /**
     * @brief 返回全生命周期 I²S 实例；由上游应用在板级初始化完成后首次调用。
     * @return 由板级持有的共享音频实例，调用方不得释放。
     */
    AudioCodec *GetAudioCodec() override {
        static NoAudioCodecSimplex codec(16000,
                                         24000,
                                         kDCSpkClock,
                                         kDCSpkWs,
                                         kDCSpkData,
                                         I2S_STD_SLOT_LEFT,
                                         kDCMicClock,
                                         kDCMicWs,
                                         kDCMicData,
                                         I2S_STD_SLOT_LEFT);
        return &codec;
    }

    /**
     * @brief 返回由板级持有的 LCD，应用仅借用；测试模式不返回应用主流程。
     * @return 已初始化的 LCD 实例，调用方不得释放。
     */
    Display *GetDisplay() override { return display; }
};

DECLARE_BOARD(DCXiaoPlusBoard);
