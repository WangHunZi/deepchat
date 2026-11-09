#include <errno.h>
#include <stdio.h>
#include <stdlib.h>

#include "gifdec.h"

/**
 * @brief 解码一轮合法 GIF，输出 BGRA 帧和毫秒时长；用于与预览素材逐帧比较。
 * @note 参数为 GIF 文件、已存在的输出目录和预期帧数。只适用于构建工具生成的受控 GIF，
 * 不承担任意不可信或截断 GIF 的安全解析责任。无硬件、显示任务或播放时钟。
 */
int main(int argc, char **argv) {
    if (argc != 4 || argv[3][0] < '0' || argv[3][0] > '9') {
        fprintf(stderr, "Usage: DCGifDecode INPUT.gif OUTPUT_DIRECTORY EXPECTED_FRAME_COUNT\n");
        return 2;
    }
    char *end;
    errno                        = 0;
    unsigned long expectedFrames = strtoul(argv[3], &end, 10);
    if (errno != 0 || *end != '\0' || expectedFrames == 0 || expectedFrames > 10000) {
        fprintf(stderr, "Expected frame count must be in 1..10000\n");
        return 2;
    }
    char framePath[4096];
    char durationPath[4096];
    int  frameLength    = snprintf(framePath, sizeof(framePath), "%s/frames.bgra", argv[2]);
    int  durationLength = snprintf(durationPath, sizeof(durationPath), "%s/durations.txt", argv[2]);
    if (frameLength < 0 || (size_t) frameLength >= sizeof(framePath) || durationLength < 0 ||
        (size_t) durationLength >= sizeof(durationPath)) {
        fprintf(stderr, "Output path is too long\n");
        return 2;
    }
    gd_GIF *gif = gd_open_gif_file(argv[1]);
    if (gif == NULL) {
        fprintf(stderr, "Cannot open GIF: %s\n", argv[1]);
        return 1;
    }
    FILE *frames    = fopen(framePath, "wb");
    FILE *durations = fopen(durationPath, "w");
    if (frames == NULL || durations == NULL) {
        fprintf(stderr, "Cannot create output files in %s\n", argv[2]);
        if (frames != NULL) fclose(frames);
        if (durations != NULL) fclose(durations);
        gd_close_gif(gif);
        return 1;
    }
    size_t frameBytes = (size_t) gif->width * gif->height * 4;
    int    status     = 0;
    for (unsigned long index = 0; index < expectedFrames; ++index) {
        long before  = ftell(gif->fd.stream);
        int  decoded = gd_get_frame(gif);
        long after   = ftell(gif->fd.stream);
        if (decoded != 1 || before < 0 || after <= before) {
            fprintf(stderr, "GIF ended, rewound or failed before expected frame %lu\n", index);
            status = 1;
            break;
        }
        gd_render_frame(gif, gif->canvas);
        if (fwrite(gif->canvas, 1, frameBytes, frames) != frameBytes ||
            fprintf(durations, "%u\n", (unsigned) gif->gce.delay * 10) < 0) {
            fprintf(stderr, "Cannot write decoded frame %lu\n", index);
            status = 1;
            break;
        }
    }
    if (status == 0) {
        long before  = ftell(gif->fd.stream);
        int  decoded = gd_get_frame(gif);
        long after   = ftell(gif->fd.stream);
        if (decoded < 0 || (decoded == 1 && after > before)) {
            fprintf(stderr, "GIF contains more frames than expected or failed at trailer\n");
            status = 1;
        }
    }
    if (fclose(frames) != 0) status = 1;
    if (fclose(durations) != 0) status = 1;
    if (status == 0) {
        printf("{\"width\":%u,\"height\":%u,\"frames\":%lu,\"format\":\"BGRA8888\"}\n",
               (unsigned) gif->width,
               (unsigned) gif->height,
               expectedFrames);
    }
    gd_close_gif(gif);
    return status;
}
