"""Threshold editor: live camera preview and a binary threshold slider.

Run on MaixCAM2 (stop the launcher / use development mode):
    python threshold_editor.py

The left canvas shows the camera image, the right canvas shows the binary
result.  Slide the slider to change the gray threshold (0-255).

Only MaixPy image APIs are used for pixel work (to_format / binary); LVGL
provides the canvas and widgets.  With MAIXPY_DEBUG_IMAGES=1 the demo exits
after 10 seconds and writes threshold_editor.png into the skill run artifacts.
"""
import os
import time

from _common import deinit_lvgl, init_lvgl, need_exit, save_screenshot

try:
    from maix import camera
except ImportError:
    camera = None

import maix_lvgl as lv

WIDTH, HEIGHT = 320, 240
BG = 0x0B0D14
PANEL = 0x12121A
TEXT = 0xF5F5FA
MUTED = 0x9CA3AF
ACCENT = 0x3B82F6
RED = 0xEF4444

DEBUG_IMAGES = os.environ.get("MAIXPY_DEBUG_IMAGES") == "1"
RUN_DIR = os.environ.get("MAIXPY_SKILL_RUN_DIR")
AUTO_EXIT_SECONDS = 10.0 if (DEBUG_IMAGES and RUN_DIR) else 0.0

KEEP = []
running = [True]
threshold = [128]


def color(value):
    return lv.color_hex(value)


def style_panel(obj, bg, radius=0, pad=0):
    obj.set_style_bg_color(color(bg), 0)
    obj.set_style_bg_opa(lv.OPA.COVER, 0)
    obj.set_style_radius(radius, 0)
    obj.set_style_border_width(0, 0)
    obj.set_style_pad_all(pad, 0)


def make_label(parent, text, x, y, font=None, text_color=TEXT):
    label = lv.label(parent)
    label.set_text(text)
    label.set_pos(x, y)
    label.set_style_text_color(color(text_color), 0)
    if font is not None:
        label.set_style_text_font(font, 0)
    return label


def save_debug_image(driver, name="threshold_editor.png"):
    if not DEBUG_IMAGES or not RUN_DIR:
        return
    art = os.path.join(RUN_DIR, "artifacts")
    os.makedirs(art, exist_ok=True)
    path = os.path.join(art, name)
    if save_screenshot(driver, path):
        print(f"MAIXPY_SKILL_IMAGE {path}", flush=True)


def main():
    if camera is None:
        print(
            "This example requires the MaixPy camera; run it on MaixCAM/MaixCAM2.",
            flush=True,
        )
        return

    cam = camera.Camera(WIDTH, HEIGHT)
    disp = ts = None
    driver = None
    start = time.monotonic()
    frames = 0

    try:
        driver, disp, ts = init_lvgl()
        scr = lv.screen_active()
        style_panel(scr, BG)

        raw_buf = bytearray(WIDTH * HEIGHT * 4)
        bin_buf = bytearray(WIDTH * HEIGHT * 4)
        KEEP.extend([raw_buf, bin_buf])

        raw_canvas = lv.canvas(scr)
        raw_canvas.set_pos(0, 0)
        raw_canvas.set_size(WIDTH, HEIGHT)
        raw_canvas.set_buffer(raw_buf, WIDTH, HEIGHT, lv.COLOR_FORMAT.ARGB8888)

        bin_canvas = lv.canvas(scr)
        bin_canvas.set_pos(WIDTH, 0)
        bin_canvas.set_size(WIDTH, HEIGHT)
        bin_canvas.set_buffer(bin_buf, WIDTH, HEIGHT, lv.COLOR_FORMAT.ARGB8888)

        raw_tag = make_label(scr, "Camera", 8, 8, lv.font_montserrat_14)
        raw_tag.set_style_bg_color(color(0x000000), 0)
        raw_tag.set_style_bg_opa(lv.OPA._60, 0)
        raw_tag.set_style_radius(6, 0)
        raw_tag.set_style_pad_all(4, 0)

        bin_tag = make_label(scr, "Binary", WIDTH + 8, 8, lv.font_montserrat_14)
        bin_tag.set_style_bg_color(color(0x000000), 0)
        bin_tag.set_style_bg_opa(lv.OPA._60, 0)
        bin_tag.set_style_radius(6, 0)
        bin_tag.set_style_pad_all(4, 0)

        panel = lv.obj(scr)
        panel.set_pos(0, HEIGHT)
        panel.set_size(640, 480 - HEIGHT)
        style_panel(panel, PANEL)
        panel.set_style_border_width(1, 0)
        panel.set_style_border_color(color(0x2A2A36), 0)

        make_label(panel, "Threshold", 20, 16, lv.font_montserrat_20)
        value_label = make_label(
            panel, str(threshold[0]), 160, 18, lv.font_montserrat_20, ACCENT
        )
        fps_label = make_label(panel, "0 fps", 240, 22, lv.font_montserrat_14, MUTED)

        slider = lv.slider(panel)
        slider.set_pos(20, 72)
        slider.set_size(600, 20)
        slider.set_range(0, 255)
        slider.set_value(threshold[0], lv.ANIM_ENABLE.OFF)

        make_label(
            panel,
            "Slide to adjust the threshold.\nLeft: camera   Right: binary",
            20,
            120,
            lv.font_montserrat_14,
            MUTED,
        )

        def on_threshold(event):
            threshold[0] = slider.get_value()
            value_label.set_text(str(threshold[0]))

        slider.add_event_cb(on_threshold, lv.EVENT.VALUE_CHANGED, None)
        KEEP.append(on_threshold)

        def on_exit(event):
            running[0] = False

        exit_btn = lv.button(panel)
        exit_btn.set_pos(520, 16)
        exit_btn.set_size(100, 44)
        exit_btn.set_style_bg_color(color(RED), 0)
        exit_btn.set_style_bg_opa(lv.OPA.COVER, 0)
        exit_btn.set_style_radius(8, 0)
        exit_label = lv.label(exit_btn)
        exit_label.set_text("Exit")
        exit_label.center()
        exit_btn.add_event_cb(on_exit, lv.EVENT.CLICKED, None)
        KEEP.append(on_exit)

        while not need_exit() and running[0]:
            img = cam.read()
            if img is None:
                lv.timer_handler()
                time.sleep(0.005)
                continue

            # 1. Camera frame -> BGRA8888 for the LVGL canvas.
            raw = img.to_format(image.Format.FMT_BGRA8888)
            raw_buf[:] = raw.to_bytes(copy=True)
            raw_canvas.invalidate()

            # 2. Camera frame -> grayscale -> binary with the MaixPy API.
            gray = img.to_format(image.Format.FMT_GRAYSCALE)
            bw = gray.binary([(threshold[0], 255)])
            bw_bgra = bw.to_format(image.Format.FMT_BGRA8888)
            bin_buf[:] = bw_bgra.to_bytes(copy=True)
            bin_canvas.invalidate()

            lv.timer_handler()
            frames += 1
            if frames % 10 == 0:
                elapsed = max(time.monotonic() - start, 1e-6)
                fps_label.set_text(f"{frames / elapsed:.0f} fps")

            if AUTO_EXIT_SECONDS and time.monotonic() - start >= AUTO_EXIT_SECONDS:
                save_debug_image(driver)
                break
            time.sleep(0.005)

    finally:
        deinit_lvgl(driver, disp, ts)
        cam.close()


if __name__ == "__main__":
    main()
