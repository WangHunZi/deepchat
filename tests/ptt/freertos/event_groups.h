#ifndef DC_PTT_EVENT_GROUPS_H
#define DC_PTT_EVENT_GROUPS_H

#include "FreeRTOS.h"

using EventBits_t = uint32_t;
struct DCEventGroup;
using EventGroupHandle_t = DCEventGroup *;

EventBits_t xEventGroupSetBits(EventGroupHandle_t group, EventBits_t bits);
EventBits_t xEventGroupGetBits(EventGroupHandle_t group);
EventBits_t
xEventGroupWaitBits(EventGroupHandle_t group, EventBits_t bits, BaseType_t clear, BaseType_t all, unsigned timeout);

#endif
