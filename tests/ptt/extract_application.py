"""Compile selected production methods unchanged; platform ports are supplied by tests."""

import argparse
import re
from pathlib import Path

METHODS = (
    "Run",
    "WakeWordInvoke",
    "BeginWakeWordInvoke",
    "ContinueWakeWordInvoke",
    "Alert",
    "ToggleChatState",
    "ConfigureWakeWordForListening",
    "SetDeviceState",
    "StartListening",
    "StopListening",
    "HandleToggleChatEvent",
    "ContinueOpenAudioChannel",
    "HandleStartListeningEvent",
    "HandleStopListeningEvent",
    "HandleStateChangedEvent",
    "HandleNetworkDisconnectedEvent",
    "StartListeningAudio",
    "Schedule",
    "SetListeningMode",
    "GetDefaultListeningMode",
    "AbortSpeaking",
    "CancelPetPresentation",
    "FinishTtsPlayback",
    "ResetProtocol",
)


def balanced_end(source, start, opening, closing):
    # 只扫描本仓库选定方法的普通字符串、字符和注释，避免单行函数吞掉下一方法。
    tokens = re.compile(r"//[^\n]*|/\*.*?\*/|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|[{}()]", re.DOTALL)
    depth = 0
    for match in tokens.finditer(source, start):
        token = match.group()
        if token == opening:
            depth += 1
        elif token == closing:
            depth -= 1
            if depth == 0:
                return match.end()
    raise ValueError("Unbalanced production method or callback")


def method(source, name):
    match = re.search(rf"^(?:void|bool|ListeningMode) Application::{name}\(", source, re.MULTILINE)
    if match is None:
        raise ValueError(f"Production Application::{name} definition was not found")
    start = source.index("{", match.end())
    return source[match.start() : balanced_end(source, start, "{", "}")]


def callback(source, name):
    match = re.search(rf"^    protocol_->{name}\(", source, re.MULTILINE)
    if match is None:
        raise ValueError(f"Production protocol callback {name} was not found")
    end = balanced_end(source, match.end() - 1, "(", ")")
    if source[end] != ";":
        raise ValueError("Production callback registration must end with a semicolon")
    return source[match.start() : end + 1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    source = args.source.read_text()
    result = '#include "DCApplicationPlatform.h"\n#include "application.h"\n#include "esp_log.h"\n#define TAG "Application"\n\n'
    result += "\n\n".join(method(source, name) for name in METHODS)
    # 只选取原注册语句，lambda 原文不改写；其余 OTA/JSON 初始化不属于此主机测试。
    result += "\n\nvoid Application::InitializeProtocol() {\n    auto& board = Board::GetInstance();\n"
    result += "\n".join(callback(source, name) for name in ("OnNetworkError", "OnAudioChannelClosed"))
    result += "\n}\n"
    args.output.write_text(result)


if __name__ == "__main__":
    main()
