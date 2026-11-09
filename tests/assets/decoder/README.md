# 上游 GIF 解码一致性工具

`DCGifDecode.c` 直接链接固定子模块的 `gifdec.c`，没有复制或修改解码算法。
同目录的 `lvgl.h` 和 `esp_log.h` 只把所需文件、内存和日志调用映射到主机 libc。
工具适用于构建工具生成的合法、受控 GIF，不作为任意不可信 GIF 的解析器或安全边界。

编译（在仓库根目录；输出放在已忽略的 build 目录）：

```sh
mkdir -p build/asset-decoder
cc -std=c11 -Wall -Wextra -Wpedantic -Werror \
  -DLV_USE_DRAW_SW_ASM=0 -DLV_DRAW_SW_ASM_HELIUM=1 -DLV_GIF_CACHE_DECODE_DATA=0 \
  -I tests/assets/decoder \
  -I third_party/xiaozhi-esp32/main/display/lvgl_display/gif \
  -c tests/assets/decoder/DCGifDecode.c -o build/asset-decoder/adapter.o
cc -std=c11 \
  -DLV_USE_DRAW_SW_ASM=0 -DLV_DRAW_SW_ASM_HELIUM=1 -DLV_GIF_CACHE_DECODE_DATA=0 \
  -I tests/assets/decoder \
  -I third_party/xiaozhi-esp32/main/display/lvgl_display/gif \
  -c third_party/xiaozhi-esp32/main/display/lvgl_display/gif/gifdec.c \
  -o build/asset-decoder/gifdec.o
cc build/asset-decoder/adapter.o build/asset-decoder/gifdec.o \
  -o build/asset-decoder/DCGifDecode
```

运行时自行创建输出目录，然后传入 GIF 路径、输出目录和预期帧数。
输出为连续全帧 BGRA8888 字节 `frames.bgra`、逐行毫秒时长 `durations.txt` 和 stdout 的尺寸/帧数 JSON。
预期帧数与首次回绕检查共同限制为一轮，避免无限循环 GIF 导致测试不退出。
错误、帧数不符或输出失败时返回非零；没有显示、任务、播放时钟或任何生产调用点。
