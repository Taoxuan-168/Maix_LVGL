"""Load the device OTF font with LVGL FreeType and render Chinese text."""
import os
import time

from maix import display, image, touchscreen

import maix_lvgl as lv

FONT_PATH = "/maixapp/share/font/SourceHanSansCN-Regular.otf"
DEBUG_IMAGES = os.environ.get("MAIXPY_DEBUG_IMAGES") == "1"
RUN_DIR = os.environ.get("MAIXPY_SKILL_RUN_DIR")


def main():
    disp = display.Display()
    ts = touchscreen.TouchScreen()
    driver = None
    font = None
    try:
        driver = lv.init(disp, ts)
        scr = lv.screen_active()
        scr.set_style_bg_color(lv.color_hex(0x101018), 0)
        scr.set_style_bg_opa(lv.OPA.COVER, 0)

        # lv_init() already initializes FreeType (LV_USE_FREETYPE) and
        # lv_deinit() cleans it up; do not init/uninit manually.
        font = lv.freetype_font_create(FONT_PATH, 0, 24, 0)
        print("font:", font)
        if font is None:
            raise RuntimeError("freetype_font_create returned None")

        title = lv.label(scr)
        title.set_text("SourceHanSansCN 中文字体测试")
        title.set_style_text_font(font, 0)
        title.set_style_text_color(lv.color_hex(0xFFFFFF), 0)
        title.set_pos(20, 20)

        body = lv.label(scr)
        body.set_text(
            "你好，MaixCAM2！\n"
            "LVGL FreeType 渲染中文：\n"
            "汉字 0123456789 ABC abc\n"
            "字体：/maixapp/share/font/\n"
            "SourceHanSansCN-Regular.otf"
        )
        body.set_style_text_font(font, 0)
        body.set_style_text_color(lv.color_hex(0x9CA3AF), 0)
        body.set_pos(20, 70)

        for _ in range(80):
            lv.timer_handler()
            time.sleep(0.01)
        lv.refr_now(driver._disp)

        if DEBUG_IMAGES and RUN_DIR:
            art = os.path.join(RUN_DIR, "artifacts")
            os.makedirs(art, exist_ok=True)
            path = os.path.join(art, "cjk_font.png")
            img = image.from_bytes(
                driver.width,
                driver.height,
                image.Format.FMT_BGRA8888,
                bytes(driver._buffer),
                True,
            )
            img.save(path)
            print(f"MAIXPY_SKILL_IMAGE {path}", flush=True)

        time.sleep(0.5)
        body.delete()
        title.delete()
        font.freetype_font_delete()
        font = None
        print("CJK FONT TEST OK", flush=True)
    finally:
        if font is not None:
            try:
                font.freetype_font_delete()
            except Exception:
                pass
        if driver is not None:
            lv.deinit()
        try:
            ts.close()
        except Exception:
            pass
        try:
            disp.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
