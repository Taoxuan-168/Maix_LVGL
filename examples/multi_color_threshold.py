"""Multi-color LAB threshold editor with LVGL.

Inspired by MaixCDK's app_find_blobs.  It keeps three color thresholds
(red/green/blue), lets you edit all six LAB values of the selected color with
sliders, switches between the original image, all-color binary and
selected-color binary views, and prints the final threshold table.

Run on MaixCAM2 (stop the launcher / use development mode):
    python multi_color_threshold.py

Only MaixPy image APIs are used for pixel work (to_format / binary); LVGL
provides the canvas and widgets.  With MAIXPY_DEBUG_IMAGES=1 the demo exits
after 10 seconds and writes multi_color_threshold.png into the run artifacts.
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
CARD = 0x1A1A24
TEXT = 0xF5F5FA
MUTED = 0x9CA3AF
ACCENT = 0x3B82F6

COLOR_NAMES = ("Red", "Green", "Blue")
COLOR_VALUES = (0xEF4444, 0x22C55E, 0x3B82F6)

# [Lmin, Lmax, Amin, Amax, Bmin, Bmax] for each color.
THRESHOLDS = [
    [0, 80, 40, 80, 10, 80],        # red
    [30, 100, -80, -20, 10, 80],    # green
    [0, 80, -20, 40, -100, -20],    # blue
]

SLIDER_SPECS = (
    ("L min", 0, 100),
    ("L max", 0, 100),
    ("A min", -128, 127),
    ("A max", -128, 127),
    ("B min", -128, 127),
    ("B max", -128, 127),
)

DEBUG_IMAGES = os.environ.get("MAIXPY_DEBUG_IMAGES") == "1"
RUN_DIR = os.environ.get("MAIXPY_SKILL_RUN_DIR")
AUTO_EXIT_SECONDS = 10.0 if (DEBUG_IMAGES and RUN_DIR) else 0.0

KEEP = []
running = [True]
color_index = [0]
mode = ["selected"]  # original | all | selected
sliders = []
value_labels = []


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


def make_button(parent, text, x, y, w, h, callback, bg):
    button = lv.button(parent)
    button.set_pos(x, y)
    button.set_size(w, h)
    button.set_style_bg_color(color(bg), 0)
    button.set_style_bg_opa(lv.OPA.COVER, 0)
    button.set_style_radius(8, 0)
    button.set_style_shadow_width(0, 0)
    label = lv.label(button)
    label.set_text(text)
    label.center()
    label.set_style_text_color(color(0xFFFFFF), 0)
    button.add_event_cb(callback, lv.EVENT.CLICKED, None)
    KEEP.append(callback)
    return button


def save_debug_image(driver, name="multi_color_threshold.png"):
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
        # Debug captures run without touch input so a noisy touch panel does
        # not move the sliders while the screenshot is being taken.
        driver, disp, ts = init_lvgl(touch=not DEBUG_IMAGES)
        scr = lv.screen_active()
        style_panel(scr, BG)

        canvas_buf = bytearray(WIDTH * HEIGHT * 4)
        KEEP.append(canvas_buf)

        canvas = lv.canvas(scr)
        canvas.set_pos(0, 0)
        canvas.set_size(WIDTH, HEIGHT)
        canvas.set_buffer(canvas_buf, WIDTH, HEIGHT, lv.COLOR_FORMAT.ARGB8888)

        # ---------------------------------------------------------- side panel
        side = lv.obj(scr)
        side.set_pos(WIDTH, 0)
        side.set_size(640 - WIDTH, HEIGHT)
        style_panel(side, PANEL)

        make_label(side, "Edit color", 10, 8, lv.font_montserrat_14, MUTED)

        color_buttons = []
        for i, (name, value) in enumerate(zip(COLOR_NAMES, COLOR_VALUES)):
            def make_color_cb(index=i):
                def callback(event):
                    select_color(index)
                return callback

            btn = make_button(
                side, name, 10 + i * 100, 30, 90, 36, make_color_cb(), value
            )
            color_buttons.append(btn)

        make_label(side, "View", 10, 76, lv.font_montserrat_14, MUTED)

        def make_mode_cb(name, label):
            def callback(event):
                mode[0] = name
                mode_label.set_text(label)
            return callback

        for i, (name, label) in enumerate(
            (("original", "Original"), ("all", "Binary All"), ("selected", "Selected"))
        ):
            make_button(
                side,
                label,
                10 + i * 100,
                98,
                90,
                36,
                make_mode_cb(name, label),
                CARD if name != "selected" else ACCENT,
            )

        def on_print(event):
            print("thresholds = [", flush=True)
            for name, th in zip(COLOR_NAMES, THRESHOLDS):
                print(
                    f"    [{th[0]}, {th[1]}, {th[2]}, "
                    f"{th[3]}, {th[4]}, {th[5]}],  # {name}",
                    flush=True,
                )
            print("]", flush=True)
            status_label.set_text("Printed to stdout")

        def on_exit(event):
            running[0] = False

        make_button(side, "Print", 10, 150, 140, 44, on_print, 0x0EA5E9)
        make_button(side, "Exit", 160, 150, 140, 44, on_exit, 0xEF4444)

        threshold_label = make_label(
            side, "", 10, 202, lv.font_montserrat_14, TEXT
        )
        mode_label = make_label(side, "Selected", 10, 220, lv.font_montserrat_14, MUTED)
        status_label = make_label(side, "", 110, 220, lv.font_montserrat_14, MUTED)

        # ------------------------------------------------------- slider panel
        panel = lv.obj(scr)
        panel.set_pos(0, HEIGHT)
        panel.set_size(640, 480 - HEIGHT)
        style_panel(panel, PANEL)
        panel.set_style_border_width(1, 0)
        panel.set_style_border_color(color(0x2A2A36), 0)

        for i, (title, vmin, vmax) in enumerate(SLIDER_SPECS):
            y = 8 + i * 38
            make_label(panel, title, 12, y + 2, lv.font_montserrat_14, MUTED)

            slider = lv.slider(panel)
            slider.set_pos(80, y)
            slider.set_size(430, 18)
            slider.set_range(vmin, vmax)
            slider.set_value(THRESHOLDS[color_index[0]][i], lv.ANIM_ENABLE.OFF)

            value_label = make_label(
                panel, str(THRESHOLDS[color_index[0]][i]), 520, y - 2, lv.font_montserrat_14
            )

            def make_slider_cb(index=i):
                def callback(event):
                    value = sliders[index].get_value()
                    # Independent sliders: never move the opposite slider and
                    # never clamp it, so both stay draggable when they are
                    # equal.  A reversed range (min > max) simply matches no
                    # pixels, which is safe in MaixPy.
                    THRESHOLDS[color_index[0]][index] = value
                    value_labels[index].set_text(str(value))
                    update_threshold_text()
                return callback

            slider.add_event_cb(make_slider_cb(), lv.EVENT.VALUE_CHANGED, None)
            sliders.append(slider)
            value_labels.append(value_label)

        def update_threshold_text():
            th = THRESHOLDS[color_index[0]]
            threshold_label.set_text(
                f"L {th[0]}-{th[1]}   A {th[2]}-{th[3]}   B {th[4]}-{th[5]}"
            )

        def select_color(index):
            color_index[0] = index
            for i, slider in enumerate(sliders):
                slider.set_value(THRESHOLDS[index][i], lv.ANIM_ENABLE.OFF)
                value_labels[i].set_text(str(THRESHOLDS[index][i]))
            update_threshold_text()
            status_label.set_text(f"Editing {COLOR_NAMES[index]}")

        update_threshold_text()
        status_label.set_text("Editing Red")

        # ------------------------------------------------------------ main loop
        while not need_exit() and running[0]:
            # Process LVGL input first so a slider change applies to this
            # frame instead of the next one.
            lv.timer_handler()

            img = cam.read()
            if img is None:
                time.sleep(0.005)
                continue

            if mode[0] == "original":
                out = img.to_format(image.Format.FMT_BGRA8888)
            else:
                gray = img.to_format(image.Format.FMT_GRAYSCALE)
                if mode[0] == "selected":
                    bw = gray.binary([THRESHOLDS[color_index[0]]])
                else:
                    bw = gray.binary(THRESHOLDS)
                out = bw.to_format(image.Format.FMT_BGRA8888)

            canvas_buf[:] = out.to_bytes(copy=True)
            canvas.invalidate()

            # Force an immediate redraw.  Without this the canvas update waits
            # for LVGL's refresh timer, so dragging a slider appears to have no
            # effect until another event (e.g. a button press) triggers a redraw.
            lv.refr_now(driver._disp)
            frames += 1

            if AUTO_EXIT_SECONDS and time.monotonic() - start >= AUTO_EXIT_SECONDS:
                save_debug_image(driver)
                break
            time.sleep(0.005)

    finally:
        deinit_lvgl(driver, disp, ts)
        cam.close()


if __name__ == "__main__":
    main()
