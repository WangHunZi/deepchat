#pragma once

#include <cstring>

#include "device_state.h"

/**
 * @brief 小智现有状态到角色动作的显示映射，不拥有录音、网络或业务状态机。
 * @note 由 Application 主任务串行调用，无分配、回调、锁或释放操作。
 * 三个成员只记录现有事件无法从 DeviceState 单独区分的显示信息：等待回复、
 * TTS 结束标记和本轮情绪。播放是否排空由 AudioService 的既有合同提供。
 */
class DCPetPresentation {
public:
    /** @brief 按键松开并发送停止录音指令后，进入等待回复的显示阶段。 */
    void OnRecordingStopped() { awaitingReply_ = true; }

    /** @brief 收到 TTS start，保留本轮已收到的情绪。 */
    void OnPlaybackStarted() {
        awaitingReply_ = false;
        stopReceived_  = false;
    }

    /**
     * @brief 记录服务端停止发送，再依据播放排空状态决定是否可以结束。
     * @param[in] drained AudioService 当前是否已排空；不是请求已被接收的状态。
     * @return
     * - true：标记与排空均已具备，可结束一次。
     * - false：继续等待排空事件。
     */
    bool OnPlaybackStopped(bool drained) {
        stopReceived_ = true;
        return OnPlaybackDrained(drained);
    }

    /**
     * @brief 处理已有播放队列排空事件，防止句间暂时排空被当作整轮结束。
     * @param[in] drained AudioService 当前排空结果。
     * @return
     * - true：服务端 stop 已收到且已排空，本轮只返回一次。
     * - false：条件未满足。
     */
    bool OnPlaybackDrained(bool drained) {
        if (!stopReceived_ || !drained) {
            return false;
        }
        stopReceived_ = false;
        return true;
    }

    /**
     * @brief 在外部 LLM 情绪边界仅接收当前已有的反馈素材；不创建回退队列。
     * @param[in] emotion 可空、以零结尾的外部名字，不保留调用者指针。
     * @return
     * - true：happy/confused 已记录或 neutral 已清除。
     * - false：无对应素材，保持原值。
     */
    bool SetFeedback(const char *emotion) {
        if (emotion == nullptr) {
            return false;
        }
        if (std::strcmp(emotion, "neutral") == 0) {
            feedback_ = nullptr;
        } else if (std::strcmp(emotion, "happy") == 0) {
            feedback_ = "happy";
        } else if (std::strcmp(emotion, "confused") == 0) {
            feedback_ = "confused";
        } else {
            return false;
        }
        return true;
    }

    /**
     * @brief 在已有状态变更处理器中选择动作，启动/配置/升级时保留原诊断界面。
     * @param[in] state 小智当前真实状态，不由此类修改。
     * @return 静态动作名字；nullptr 表示应显示原诊断界面，调用者不释放。
     * @note 手动停止录音后的 Idle 显示 thinking；完成回复后的 Idle 消费一次本轮反馈。
     */
    const char *OnState(DeviceState state) {
        switch (state) {
            case kDeviceStateIdle:
                if (awaitingReply_) {
                    return "thinking";
                }
                if (feedback_ != nullptr) {
                    const char *result = feedback_;
                    feedback_          = nullptr;
                    return result;
                }
                return "neutral";
            case kDeviceStateConnecting: Cancel(); return "thinking";
            case kDeviceStateListening:  Cancel(); return "listening";
            case kDeviceStateSpeaking:   return "speaking";
            case kDeviceStateNotifying:  Cancel(); return "speaking";
            default:                     Cancel(); return nullptr;
        }
    }

    /**
     * @brief 清除本轮信息；已处于 Idle 时返回刷新动作，避免同状态转换不发通知而滞留思考。
     * @param[in] state 当前真实状态；内部仅清理信息时可省略。
     * @return 静态 neutral 名称表示应立即刷新待机；nullptr 表示由后续真实状态变更更新画面。
     * @note 不触发录音、网络或状态转换，调用者不释放返回值。
     */
    const char *Cancel(DeviceState state = kDeviceStateUnknown) {
        awaitingReply_ = false;
        stopReceived_  = false;
        feedback_      = nullptr;
        return state == kDeviceStateIdle ? "neutral" : nullptr;
    }

private:
    bool        awaitingReply_ = false;
    bool        stopReceived_  = false;
    const char *feedback_      = nullptr;
};
