#include <array>
#include <cstdio>
#include <cstdlib>
#include <cstring>

#include "DCGifFixtures.h"
#include "DCPetLayout.h"
#include "DCPetPresentation.h"
#include "device_state_machine.h"
#include "lvgl_gif.h"

#define CHECK(condition)                                                                                               \
    do {                                                                                                               \
        if (!(condition)) {                                                                                            \
            std::fprintf(stderr, "%s:%d: %s\n", __FILE__, __LINE__, #condition);                                       \
            std::exit(1);                                                                                              \
        }                                                                                                              \
    } while (0)

static void CheckEmotion(const char *actual, const char *expected) {
    CHECK(actual != nullptr);
    CHECK(std::strcmp(actual, expected) == 0);
}

static void InitializeIdle(DeviceStateMachine &machine) {
    CHECK(machine.TransitionTo(kDeviceStateStarting));
    CHECK(machine.TransitionTo(kDeviceStateActivating));
    CHECK(machine.TransitionTo(kDeviceStateIdle));
}

static void AdvanceMs(uint32_t milliseconds) {
    for (uint32_t elapsed = 0; elapsed < milliseconds; elapsed += 10) {
        lv_tick_inc(10);
        lv_timer_handler();
    }
}

static void CheckLayout() {
    lv_init();
    lv_display_t                  *display = lv_display_create(240, 240);
    std::array<uint16_t, 240 * 20> pixels{};
    lv_display_set_buffers(display, pixels.data(), nullptr, sizeof(pixels), LV_DISPLAY_RENDER_MODE_PARTIAL);
    lv_display_set_flush_cb(display,
                            [](lv_display_t *output, const lv_area_t *, uint8_t *) { lv_display_flush_ready(output); });
    auto screen     = lv_screen_active();
    auto role       = lv_obj_create(screen);
    auto top        = lv_obj_create(screen);
    auto status     = lv_obj_create(screen);
    auto bottom     = lv_obj_create(screen);
    auto alert      = lv_obj_create(screen);
    auto statusText = lv_label_create(status);
    auto chat       = lv_label_create(bottom);
    lv_obj_update_layout(screen);
    DCPetApplyLayout(top, status, bottom, true, false, true);
    CHECK(!lv_obj_is_visible(top));
    CHECK(!lv_obj_is_visible(status));
    CHECK(!lv_obj_is_visible(bottom));
    CHECK(lv_obj_is_visible(role) && lv_obj_is_visible(alert));
    lv_obj_remove_flag(statusText, LV_OBJ_FLAG_HIDDEN);
    lv_obj_remove_flag(chat, LV_OBJ_FLAG_HIDDEN);
    lv_label_set_text(statusText, "changed status");
    lv_label_set_text(chat, "changed transcript");
    CHECK(!lv_obj_is_visible(statusText) && !lv_obj_is_visible(chat));
    DCPetApplyLayout(top, status, bottom, false, false, true);
    CHECK(lv_obj_is_visible(top) && lv_obj_is_visible(status) && lv_obj_is_visible(bottom));
    DCPetApplyLayout(top, status, bottom, false, true, true);
    CHECK(!lv_obj_is_visible(bottom));
    DCPetApplyLayout(top, status, bottom, false, false, false);
    CHECK(!lv_obj_is_visible(bottom));
    CHECK(lv_obj_is_visible(role) && lv_obj_is_visible(alert));
    lv_display_delete(display);
    lv_deinit();
}

static void CheckGif(bool loop) {
    lv_init();
    lv_img_dsc_t descriptor{};
    descriptor.data      = loop ? kDCPetLoopGif : kDCPetOnceGif;
    descriptor.data_size = loop ? sizeof(kDCPetLoopGif) : sizeof(kDCPetOnceGif);
    {
        LvglGif gif(&descriptor);
        CHECK(gif.IsLoaded());
        gif.Start();
        CHECK(gif.IsPlaying());
        AdvanceMs(90);
        CHECK(gif.IsPlaying());
        AdvanceMs(600);
        CHECK(gif.IsPlaying() == loop);
        if (loop) {
            gif.Stop();
            CHECK(!gif.IsPlaying());
        }
    }
    lv_deinit();
}

int main(int argc, char **argv) {
    CHECK(argc == 2);
    DCPetPresentation  presentation;
    DeviceStateMachine machine;
    InitializeIdle(machine);
    if (std::strcmp(argv[1], "manual") == 0) {
        CheckEmotion(presentation.OnState(machine.GetState()), "neutral");
        CHECK(machine.TransitionTo(kDeviceStateListening));
        CheckEmotion(presentation.OnState(machine.GetState()), "listening");
        presentation.OnRecordingStopped();
        CHECK(machine.TransitionTo(kDeviceStateIdle));
        CheckEmotion(presentation.OnState(machine.GetState()), "thinking");
        CHECK(presentation.SetFeedback("happy"));
        presentation.OnPlaybackStarted();
        CHECK(machine.TransitionTo(kDeviceStateSpeaking));
        CheckEmotion(presentation.OnState(machine.GetState()), "speaking");
        CHECK(!presentation.OnPlaybackDrained(true));
        CHECK(!presentation.OnPlaybackStopped(false));
        CHECK(!presentation.OnPlaybackDrained(false));
        CHECK(presentation.OnPlaybackDrained(true));
        CHECK(!presentation.OnPlaybackDrained(true));
        CHECK(machine.TransitionTo(kDeviceStateIdle));
        CheckEmotion(presentation.OnState(machine.GetState()), "happy");
        CheckEmotion(presentation.OnState(machine.GetState()), "neutral");
    } else if (std::strcmp(argv[1], "cancel") == 0) {
        CHECK(machine.TransitionTo(kDeviceStateListening));
        CheckEmotion(presentation.OnState(machine.GetState()), "listening");
        presentation.OnRecordingStopped();
        CHECK(machine.TransitionTo(kDeviceStateIdle));
        CheckEmotion(presentation.OnState(machine.GetState()), "thinking");
        bool notified = false;
        int  listener = machine.AddStateChangeListener([&notified](DeviceState, DeviceState) { notified = true; });
        CHECK(machine.TransitionTo(kDeviceStateIdle));
        CHECK(!notified);
        CheckEmotion(presentation.Cancel(machine.GetState()), "neutral");
        machine.RemoveStateChangeListener(listener);
        presentation.OnRecordingStopped();
        CHECK(presentation.SetFeedback("happy"));
        CHECK(!presentation.OnPlaybackStopped(false));
        presentation.Cancel();
        CHECK(!presentation.OnPlaybackDrained(true));
        CheckEmotion(presentation.OnState(kDeviceStateIdle), "neutral");
        presentation.OnRecordingStopped();
        CHECK(presentation.SetFeedback("confused"));
        CheckEmotion(presentation.OnState(kDeviceStateListening), "listening");
        CheckEmotion(presentation.OnState(kDeviceStateIdle), "neutral");
        CHECK(!presentation.OnPlaybackDrained(true));
    } else if (std::strcmp(argv[1], "feedback") == 0) {
        CHECK(presentation.SetFeedback("happy"));
        CHECK(!presentation.SetFeedback("unknown"));
        CHECK(!presentation.SetFeedback(nullptr));
        CheckEmotion(presentation.OnState(kDeviceStateIdle), "happy");
        CHECK(presentation.SetFeedback("confused"));
        CheckEmotion(presentation.OnState(kDeviceStateIdle), "confused");
        CHECK(presentation.SetFeedback("happy"));
        CHECK(presentation.SetFeedback("neutral"));
        CheckEmotion(presentation.OnState(kDeviceStateIdle), "neutral");
        presentation.OnPlaybackStarted();
        CHECK(presentation.OnPlaybackStopped(true));
        CHECK(!presentation.OnPlaybackDrained(true));
        CheckEmotion(presentation.OnState(kDeviceStateIdle), "neutral");
        CHECK(presentation.SetFeedback("happy"));
        CheckEmotion(presentation.OnState(kDeviceStateIdle), "happy");
    } else if (std::strcmp(argv[1], "diagnostics") == 0) {
        const DeviceState diagnostics[] = {kDeviceStateUnknown,
                                           kDeviceStateStarting,
                                           kDeviceStateWifiConfiguring,
                                           kDeviceStateActivating,
                                           kDeviceStateUpgrading,
                                           kDeviceStateAudioTesting,
                                           kDeviceStateFatalError};
        for (auto state : diagnostics) {
            presentation.OnRecordingStopped();
            CHECK(presentation.SetFeedback("happy"));
            CHECK(presentation.OnState(state) == nullptr);
            CheckEmotion(presentation.OnState(kDeviceStateIdle), "neutral");
        }
        CheckEmotion(presentation.OnState(kDeviceStateConnecting), "thinking");
        CheckEmotion(presentation.OnState(kDeviceStateNotifying), "speaking");
    } else if (std::strcmp(argv[1], "layout") == 0) {
        CheckLayout();
    } else if (std::strcmp(argv[1], "gif-once") == 0) {
        CheckGif(false);
    } else if (std::strcmp(argv[1], "gif-loop") == 0) {
        CheckGif(true);
    } else {
        return 2;
    }
    return 0;
}
