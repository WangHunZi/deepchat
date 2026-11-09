#ifndef DC_PET_TEST_ESP_LOG_H
#define DC_PET_TEST_ESP_LOG_H

#include <stdio.h>

/* 仅替换平台日志输出，保留实际状态机、LVGL 和 GIF 实现。 */
#define ESP_LOGD(tag, ...)                                                                                             \
    do {                                                                                                               \
        (void) (tag);                                                                                                  \
    } while (0)
#define ESP_LOGI(tag, ...)                                                                                             \
    do {                                                                                                               \
        (void) (tag);                                                                                                  \
    } while (0)
#define ESP_LOGW(tag, ...)                                                                                             \
    do {                                                                                                               \
        fprintf(stderr, "[%s]: ", tag);                                                                                \
        fprintf(stderr, __VA_ARGS__);                                                                                  \
        fputc('\n', stderr);                                                                                           \
    } while (0)
#define ESP_LOGE(tag, ...) ESP_LOGW(tag, __VA_ARGS__)

#endif
