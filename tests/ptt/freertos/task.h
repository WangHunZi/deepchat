#ifndef DC_PTT_TASK_H
#define DC_PTT_TASK_H

#include "FreeRTOS.h"

inline void vTaskPrioritySet(TaskHandle_t, UBaseType_t) {}

inline UBaseType_t uxTaskPriorityGet(TaskHandle_t) { return 1; }

#endif
