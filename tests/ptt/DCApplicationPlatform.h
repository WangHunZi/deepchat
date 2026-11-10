#ifndef DC_PTT_APPLICATION_PLATFORM_H
#define DC_PTT_APPLICATION_PLATFORM_H

#include <atomic>
#include <cstdint>
#include <functional>
#include <memory>
#include <string>
#include <string_view>
#include <vector>

#include "freertos/event_groups.h"

// 使用真实 application.h 的字段和签名，仅替换这些硬件/网络头的实现。
#define PROTOCOL_H
#define AUDIO_SERVICE_H
#define _OTA_H
#define NOTIFY_PLAYER_H_

struct AudioStreamPacket {};

struct NotifySubtitle {};

enum AbortReason { kAbortReasonNone, kAbortReasonWakeWordDetected };

enum ListeningMode { kListeningModeAutoStop, kListeningModeManualStop, kListeningModeRealtime };

struct DCTrace {
    bool          stopSawRecording = false;
    int           opens            = 0;
    int           closes           = 0;
    int           starts           = 0;
    int           stops            = 0;
    int           voiceEnables     = 0;
    int           aborts           = 0;
    ListeningMode lastMode         = kListeningModeAutoStop;
    bool          voiceEnabled     = false;
    std::string   emotion;
};

extern DCTrace               sTrace;
extern std::function<void()> sDuringOpen;
extern std::function<void()> sBeforeWait;
extern bool                  sOpenSucceeds;
extern bool                  sInitiallyOpened;

class Protocol {
public:
    Protocol() : opened(sInitiallyOpened) {}

    bool OpenAudioChannel();

    bool IsAudioChannelOpened() const { return opened; }

    void CloseAudioChannel();

    void SendStartListening(ListeningMode mode) {
        ++sTrace.starts;
        sTrace.lastMode = mode;
    }

    void SendStopListening() {
        sTrace.stopSawRecording |= sTrace.voiceEnabled;
        ++sTrace.stops;
    }

    void SendAbortSpeaking(AbortReason) { ++sTrace.aborts; }

    bool SendAudio(std::unique_ptr<AudioStreamPacket>) { return true; }

    void OnNetworkError(std::function<void(const std::string &)> callback) { networkError = std::move(callback); }

    void OnAudioChannelClosed(std::function<void()> callback) { channelClosed = std::move(callback); }

    void EmitNetworkError() { networkError("test connection failure"); }

    void EmitChannelClosed() {
        opened = false;
        channelClosed();
    }

private:
    bool                                     opened;
    std::function<void(const std::string &)> networkError;
    std::function<void()>                    channelClosed;
};

extern Protocol *sProtocol;

class AudioService {
public:
    bool IsVoiceDetected() const { return false; }

    bool IsPlaybackIdle() const { return true; }

    bool IsAudioProcessorRunning() const { return sTrace.voiceEnabled; }

    bool IsAfeWakeWord() const { return false; }

    void EnableVoiceProcessing(bool enabled) {
        sTrace.voiceEnabled = enabled;
        if (enabled) {
            ++sTrace.voiceEnables;
        }
    }

    void EnableWakeWordDetection(bool) {}

    void EnableAudioTesting(bool) {}

    void ResetDecoder() {}

    void EncodeWakeWord() {}

    void PlaySound(std::string_view) {}

    std::unique_ptr<AudioStreamPacket> PopPacketFromSendQueue() { return {}; }
};

class NotifyPlayer {
public:
    explicit NotifyPlayer(AudioService &) {}

    void OnPlaybackDrained() {}
};

class Ota {};

class DCDisplay {
public:
    void SetPetMode(bool) {}

    bool SetEmotion(const char *emotion) {
        sTrace.emotion = emotion == nullptr ? "" : emotion;
        return true;
    }

    void SetStatus(const char *) {}

    void SetChatMessage(const char *, const char *) {}

    void ClearChatMessages() {}

    void UpdateStatusBar(bool = false) {}
};

class DCLed {
public:
    void OnStateChanged() {}
};

enum class PowerSaveLevel { LOW_POWER, BALANCED, PERFORMANCE };

class Board {
public:
    static Board &GetInstance() {
        static Board board;
        return board;
    }

    DCDisplay *GetDisplay() { return &display; }

    DCLed *GetLed() { return &led; }

    void SetPowerSaveLevel(PowerSaveLevel) {}

private:
    DCDisplay display;
    DCLed     led;
};

namespace SystemInfo {
inline void PrintHeapStats() {}
}  // namespace SystemInfo

namespace Lang::Strings {
inline constexpr const char *ERROR      = "error";
inline constexpr const char *STANDBY    = "standby";
inline constexpr const char *CONNECTING = "connecting";
inline constexpr const char *LISTENING  = "listening";
inline constexpr const char *SPEAKING   = "speaking";
}  // namespace Lang::Strings

namespace Lang::Sounds {
inline constexpr std::string_view OGG_EXCLAMATION = "";
inline constexpr std::string_view OGG_POPUP       = "";
}  // namespace Lang::Sounds

#endif
