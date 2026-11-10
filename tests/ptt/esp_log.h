#ifndef DC_PTT_ESP_LOG_H
#define DC_PTT_ESP_LOG_H

// 仍求值日志实参，保持生产代码变量的使用语义；无需真实 ESP 日志运行时。
template <typename... Args> inline void DCPttDiscardLog(const char *tag, const char *format, const Args &...args) {
    (void) tag;
    (void) format;
    ((void) args, ...);
}

#define ESP_LOGD(tag, ...) DCPttDiscardLog(tag, __VA_ARGS__)
#define ESP_LOGI(tag, ...) DCPttDiscardLog(tag, __VA_ARGS__)
#define ESP_LOGW(tag, ...) DCPttDiscardLog(tag, __VA_ARGS__)
#define ESP_LOGE(tag, ...) DCPttDiscardLog(tag, __VA_ARGS__)

#endif
