// SPDX-License-Identifier: MIT
#include <esp_app_desc.h>
#include <esp_log.h>
#include <esp_system.h>

_Static_assert(__STDC_VERSION__ == 201112L, "DeepChat application requires C11");

/**
 * @brief 输出未定板级配置的启动信息，不初始化外接 GPIO、屏幕或音频。
 * @note 由 ESP-IDF 主任务调用；返回后 SDK 继续调度系统任务。
 */
void app_main(void) {
    const esp_app_desc_t *description = esp_app_get_description();
    ESP_LOGI(
        "DeepChat", "[App::Boot]: firmware=%s idf=%s profile=bringup", description->version, esp_get_idf_version());
    ESP_LOGI("DeepChat", "[App::Boot]: peripherals=unconfigured hardware-validation=pending");
}
