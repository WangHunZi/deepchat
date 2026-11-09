#ifndef DC_TEST_GIF_ESP_LOG_H
#define DC_TEST_GIF_ESP_LOG_H

/* 上游告警写入 stderr；不改动或抑制解码器错误路径。 */
#include <stdio.h>

#define ESP_LOGW(tag, ...)                                                                                             \
    do {                                                                                                               \
        fprintf(stderr, "[%s]: ", tag);                                                                                \
        fprintf(stderr, __VA_ARGS__);                                                                                  \
        fputc('\n', stderr);                                                                                           \
    } while (0)

#endif
