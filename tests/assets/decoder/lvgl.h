#ifndef DC_TEST_GIF_LVGL_H
#define DC_TEST_GIF_LVGL_H

/* 仅供主机一致性测试：保持上游解码器的 LVGL 名称，映射为 libc 文件与内存操作。 */
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

typedef struct {
    FILE *stream;
} lv_fs_file_t;

typedef enum { LV_FS_RES_OK, LV_FS_RES_FS_ERR } lv_fs_res_t;

#define LV_FS_MODE_RD  1
#define LV_FS_SEEK_SET SEEK_SET
#define LV_FS_SEEK_CUR SEEK_CUR
#define lv_malloc      malloc
#define lv_realloc     realloc
#define lv_free        free

static inline lv_fs_res_t lv_fs_open(lv_fs_file_t *file, const char *path, int mode) {
    (void) mode;
    file->stream = fopen(path, "rb");
    return file->stream != NULL ? LV_FS_RES_OK : LV_FS_RES_FS_ERR;
}

static inline lv_fs_res_t lv_fs_read(lv_fs_file_t *file, void *buffer, size_t length, uint32_t *bytesRead) {
    size_t count = fread(buffer, 1, length, file->stream);
    if (bytesRead != NULL) *bytesRead = (uint32_t) count;
    return count == length ? LV_FS_RES_OK : LV_FS_RES_FS_ERR;
}

static inline lv_fs_res_t lv_fs_seek(lv_fs_file_t *file, size_t offset, int origin) {
    return fseek(file->stream, (long) offset, origin) == 0 ? LV_FS_RES_OK : LV_FS_RES_FS_ERR;
}

static inline lv_fs_res_t lv_fs_tell(lv_fs_file_t *file, uint32_t *position) {
    long current = ftell(file->stream);
    if (current < 0) return LV_FS_RES_FS_ERR;
    *position = (uint32_t) current;
    return LV_FS_RES_OK;
}

static inline lv_fs_res_t lv_fs_close(lv_fs_file_t *file) {
    return fclose(file->stream) == 0 ? LV_FS_RES_OK : LV_FS_RES_FS_ERR;
}

#endif
