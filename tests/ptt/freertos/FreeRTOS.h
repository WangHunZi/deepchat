#ifndef DC_PTT_FREERTOS_H
#define DC_PTT_FREERTOS_H

#include <cstdint>

using BaseType_t                        = int;
using UBaseType_t                       = unsigned;
using TaskHandle_t                      = void *;
inline constexpr int      pdTRUE        = 1;
inline constexpr int      pdFALSE       = 0;
inline constexpr unsigned portMAX_DELAY = 0xffffffffU;

#endif
