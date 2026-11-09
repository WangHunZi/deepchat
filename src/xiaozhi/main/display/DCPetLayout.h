#pragma once

#include <lvgl.h>

/**
 * @brief 调整默认 LCD 布局的三个现有父层，角色层与低电量警告不受影响。
 * @param[in] top 非空、已创建的图标栏，由 LcdDisplay 所有。
 * @param[in] status 非空、已创建的状态/通知栏，由 LcdDisplay 所有。
 * @param[in] bottom 非空、已创建的聊天文字栏，由 LcdDisplay 所有。
 * @param[in] petMode 是否处于角色主界面。
 * @param[in] hideSubtitle 原用户字幕偏好，不在此修改。
 * @param[in] hasText 当前底栏是否有文字。
 * @note 调用者已经持有 LVGL 显示锁；不分配对象、存储指针或修改用户设置。
 */
inline void
DCPetApplyLayout(lv_obj_t *top, lv_obj_t *status, lv_obj_t *bottom, bool petMode, bool hideSubtitle, bool hasText) {
    auto setHidden = [](lv_obj_t *object, bool hidden) {
        if (hidden) {
            lv_obj_add_flag(object, LV_OBJ_FLAG_HIDDEN);
        } else {
            lv_obj_remove_flag(object, LV_OBJ_FLAG_HIDDEN);
        }
    };
    setHidden(top, petMode);
    setHidden(status, petMode);
    setHidden(bottom, petMode || hideSubtitle || !hasText);
}
