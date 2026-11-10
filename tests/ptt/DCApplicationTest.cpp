#include <cstdio>
#include <cstdlib>
#include <thread>

#include "DCApplicationPlatform.h"
#include "application.h"

struct DCEventGroup {
    std::atomic<EventBits_t> bits{0};
};

struct DCMainLoopIdle {};

static DCEventGroup   sGroup;
DCTrace               sTrace;
std::function<void()> sDuringOpen;
std::function<void()> sBeforeWait;
bool                  sOpenSucceeds    = true;
bool                  sInitiallyOpened = false;
Protocol             *sProtocol        = nullptr;

static void DCRequire(bool condition, const char *message) {
    if (!condition) {
        std::fprintf(stderr, "%s\n", message);
        std::exit(1);
    }
}

EventBits_t xEventGroupSetBits(EventGroupHandle_t group, EventBits_t bits) { return group->bits.fetch_or(bits) | bits; }

EventBits_t xEventGroupGetBits(EventGroupHandle_t group) { return group->bits.load(); }

EventBits_t
xEventGroupWaitBits(EventGroupHandle_t group, EventBits_t bits, BaseType_t clear, BaseType_t all, unsigned timeout) {
    (void) all;
    (void) timeout;
    if (sBeforeWait) {
        sBeforeWait();
    }
    const EventBits_t result = clear ? group->bits.fetch_and(~bits) & bits : group->bits.load() & bits;
    if (result == 0) {
        throw DCMainLoopIdle{};
    }
    return result;
}

bool Protocol::OpenAudioChannel() {
    ++sTrace.opens;
    if (sDuringOpen) {
        sDuringOpen();
    }
    opened = sOpenSucceeds;
    return opened;
}

void Protocol::CloseAudioChannel() {
    ++sTrace.closes;
    opened = false;
    if (channelClosed) {
        channelClosed();
    }
}

// 平台初始化替身：提供真实 application.h 的实例、真实 FSM、协议端口及状态事件。
// 不调用真实硬件/OTA 初始化；业务方法与 Run 均由原生成 Application 源码直接编译。
Application::Application() : notify_player_(audio_service_) {
    event_group_ = &sGroup;
    protocol_    = std::make_unique<Protocol>();
    sProtocol    = protocol_.get();
    state_machine_.AddStateChangeListener(
        [this](DeviceState, DeviceState) { xEventGroupSetBits(event_group_, MAIN_EVENT_STATE_CHANGED); });
    SetDeviceState(kDeviceStateStarting);
    SetDeviceState(kDeviceStateActivating);
    SetDeviceState(kDeviceStateIdle);
    sGroup.bits.store(0);
    InitializeProtocol();
}

Application::~Application() = default;

// 非本次用例的初始化/诊断端口保持空实现；不改写 PTT 事件处理或其状态转换。
void Application::HandleNetworkConnectedEvent() {}

void Application::HandleActivationDoneEvent() {}

void Application::HandleWakeWordDetectedEvent() {}

void Application::ShowStartupWakeWordHint() {}

void Application::HideStartupWakeWordHint() {}

void Application::StopNotification() { SetDeviceState(kDeviceStateIdle); }

static void DCDrain(Application &app) {
    try {
        app.Run();
    }
    catch (const DCMainLoopIdle &) {
        return;
    }
    DCRequire(false, "Run unexpectedly returned");
}

static void DCExpectCancelled(Application &app) {
    DCRequire(app.GetDeviceState() == kDeviceStateIdle, "cancelled request must leave application idle");
    DCRequire(sTrace.starts == 0 && sTrace.stops == 0, "cancelled request must send no listening start or stop");
    DCRequire(sTrace.voiceEnables == 0 && !sTrace.voiceEnabled, "cancelled request must never enable recording");
    DCRequire(sTrace.emotion != "thinking", "cancelled request must not wait for a reply");
}

static void DCStartAndExpectRecording(Application &app) {
    app.StartListening();
    DCDrain(app);
    DCRequire(app.GetDeviceState() == kDeviceStateListening, "held press must enter listening");
    DCRequire(sTrace.voiceEnabled, "held press must enable recording");
    DCRequire(sTrace.lastMode == kListeningModeManualStop, "PTT must use manual-stop protocol mode");
}

int main(int argc, char **argv) {
    DCRequire(argc == 2, "provide a scenario");
    const std::string scenario = argv[1];
    auto             &app      = Application::GetInstance();

    if (scenario == "coalesced-tap") {
        app.StartListening();
        app.StopListening();
        DCDrain(app);
        DCExpectCancelled(app);
        DCRequire(sTrace.opens == 0, "tap released before dispatch must not open the channel");
    } else if (scenario == "release-before-connect") {
        bool released = false;
        sBeforeWait   = [&]() {
            if (!released && app.GetDeviceState() == kDeviceStateConnecting) {
                released = true;
                app.StopListening();
            }
        };
        app.StartListening();
        DCDrain(app);
        DCRequire(released, "scenario must reach pending connection");
        DCExpectCancelled(app);
        DCRequire(sTrace.opens == 0, "released scheduled request must not start connection");
    } else if (scenario == "release-during-connect") {
        sDuringOpen = [&]() {
            std::thread button([&]() { app.StopListening(); });
            button.join();
        };
        app.StartListening();
        DCDrain(app);
        DCExpectCancelled(app);
        DCRequire(sTrace.opens == 1, "scenario must release inside the blocking open");
        sDuringOpen = {};
        DCStartAndExpectRecording(app);
        DCRequire(sTrace.opens == 1, "successfully opened channel must remain reusable");
    } else if (scenario == "release-before-audio") {
        bool released = false;
        sBeforeWait   = [&]() {
            if (!released && app.GetDeviceState() == kDeviceStateListening) {
                released = true;
                app.StopListening();
            }
        };
        app.StartListening();
        DCDrain(app);
        DCRequire(released, "scenario must release after connection before state dispatch");
        DCExpectCancelled(app);
    } else if (scenario == "release-repress") {
        sDuringOpen = [&]() {
            app.StopListening();
            app.StartListening();
        };
        DCStartAndExpectRecording(app);
        DCRequire(sTrace.opens == 1 && sTrace.starts == 1, "latest press must start exactly one recording");
        DCRequire(sTrace.stops == 0, "stale stop bit must not cancel the latest press");
        app.StopListening();
        DCDrain(app);
        DCRequire(sTrace.stops == 1 && !sTrace.voiceEnabled, "fresh release must stop the latest recording");
    } else if (scenario == "normal") {
        DCStartAndExpectRecording(app);
        app.StopListening();
        DCDrain(app);
        DCRequire(sTrace.starts == 1 && sTrace.stops == 1, "normal hold/release must send one start and one stop");
        DCRequire(!sTrace.stopSawRecording, "recording must be disabled before stop is sent to the protocol");
        DCRequire(app.GetDeviceState() == kDeviceStateIdle && !sTrace.voiceEnabled, "release must disable recording");
        DCRequire(sTrace.emotion == "thinking", "completed recording must wait for a real reply");
        DCStartAndExpectRecording(app);
        DCRequire(sTrace.opens == 1, "next press should reuse the existing audio channel");
    } else if (scenario == "open-failure") {
        sOpenSucceeds = false;
        bool repeated = false;
        sDuringOpen   = [&]() {
            if (!repeated) {
                repeated = true;
                app.StopListening();
                app.StartListening();
            }
        };
        app.StartListening();
        DCDrain(app);
        DCExpectCancelled(app);
        DCRequire(sTrace.opens == 1, "failed open must not retry a stale queued request");
        sDuringOpen   = {};
        sOpenSucceeds = true;
        DCStartAndExpectRecording(app);
    } else if (scenario == "network-error") {
        sDuringOpen = [&]() {
            app.StopListening();
            app.StartListening();
            sProtocol->EmitNetworkError();
        };
        app.StartListening();
        DCDrain(app);
        DCExpectCancelled(app);
        DCRequire(sTrace.opens == 1, "network error must cancel a queued press without reopening");
    } else if (scenario == "channel-close") {
        sDuringOpen = [&]() {
            app.StopListening();
            app.StartListening();
            sProtocol->EmitChannelClosed();
        };
        app.StartListening();
        DCDrain(app);
        DCExpectCancelled(app);
        DCRequire(sTrace.opens == 1, "closed channel must not restart from a stale request");
    } else if (scenario == "reset-during-connect") {
        sDuringOpen = [&]() { app.ResetProtocol(); };
        app.StartListening();
        DCDrain(app);
        DCExpectCancelled(app);
        DCRequire(sTrace.closes == 1, "reset must close the successful connection before releasing the protocol");
        app.StartListening();
        DCDrain(app);
        DCRequire(sTrace.starts == 0 && !sTrace.voiceEnabled,
                  "reset protocol must remain inactive until reinitialized");
    } else if (scenario == "reset-before-scheduled-open") {
        // Reset 位于本次 Run 消费 START 时新排入的 Continue 之前。
        app.ResetProtocol();
        app.StartListening();
        DCDrain(app);
        DCExpectCancelled(app);
        DCRequire(sTrace.opens == 0, "reset queued before Continue must prevent access to a destroyed protocol");
    } else if (scenario == "disconnect") {
        sDuringOpen = [&]() { xEventGroupSetBits(&sGroup, MAIN_EVENT_NETWORK_DISCONNECTED); };
        app.StartListening();
        DCDrain(app);
        DCExpectCancelled(app);
        DCRequire(sTrace.closes == 1, "network-disconnect event must close the channel");
    } else if (scenario == "toggle-auto") {
        app.ToggleChatState();
        DCDrain(app);
        DCRequire(app.GetDeviceState() == kDeviceStateListening && sTrace.voiceEnabled,
                  "toggle must still start auto mode");
        DCRequire(sTrace.lastMode == kListeningModeAutoStop, "toggle must not inherit manual request gating");
        app.ToggleChatState();
        DCDrain(app);
        DCRequire(app.GetDeviceState() == kDeviceStateIdle && !sTrace.voiceEnabled,
                  "toggle must still close auto mode");
    } else if (scenario == "auto-after-manual" || scenario == "wake-after-manual") {
        DCStartAndExpectRecording(app);
        app.StopListening();
        DCDrain(app);
        sProtocol->EmitChannelClosed();
        DCDrain(app);
        bool released = false;
        sBeforeWait   = [&]() {
            if (!released && app.GetDeviceState() == kDeviceStateConnecting) {
                released = true;
                app.StopListening();
            }
        };
        if (scenario == "auto-after-manual") {
            app.ToggleChatState();
        } else {
            app.WakeWordInvoke("test wake word");
        }
        DCDrain(app);
        DCRequire(released, "regression must consume stale manual release while auto connection is pending");
        DCRequire(app.GetDeviceState() == kDeviceStateListening && sTrace.voiceEnabled,
                  "stale manual mode must not cancel the next automatic connection");
        DCRequire(sTrace.lastMode == kListeningModeAutoStop, "automatic request must use the current default mode");
        DCRequire(sTrace.starts == 2 && sTrace.stops == 1, "old release must not add an automatic stop");
    } else if (scenario == "diagnostic") {
        app.SetDeviceState(kDeviceStateWifiConfiguring);
        DCDrain(app);
        app.StartListening();
        DCDrain(app);
        DCRequire(app.GetDeviceState() == kDeviceStateAudioTesting,
                  "configuration press must retain upstream audio test");
        app.StopListening();
        DCDrain(app);
        DCRequire(app.GetDeviceState() == kDeviceStateWifiConfiguring, "configuration release must leave audio test");
        DCRequire(sTrace.opens == 0 && sTrace.starts == 0, "diagnostic interaction must not open a conversation");
    } else if (scenario == "speaking-interrupt") {
        app.SetDeviceState(kDeviceStateSpeaking);
        DCDrain(app);
        DCStartAndExpectRecording(app);
        DCRequire(sTrace.aborts == 1, "manual press must retain upstream speaking interruption");
        app.StopListening();
        DCDrain(app);
        DCRequire(sTrace.stops == 1 && !sTrace.voiceEnabled, "release after interruption must stop recording");
    } else {
        DCRequire(false, "unknown scenario");
    }
    return 0;
}
