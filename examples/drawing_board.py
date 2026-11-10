"""Touch drawing board with a custom color wheel.

Run on MaixCAM2 (stop the launcher / use development mode):
    python drawing_board.py

The toolbar selects a preset color or opens a custom HSV color wheel, changes
the brush size, clears the canvas, saves a PNG or exits.  Drawing writes pixels
into an LVGL canvas from the pointer indev; the color wheel is also drawn into
an LVGL canvas, so only LVGL / MaixPy APIs are used.

With MAIXPY_DEBUG_IMAGES=1 the board draws a test pattern, opens the color
wheel for the capture, exits after 10 seconds and writes drawing_board.png
into the skill run artifacts.
"""
import colorsys
import math
import os
import time

from _common import deinit_lvgl, init_lvgl, need_exit, save_screenshot

try:
    from maix import image
except ImportError:
    image = None

import maix_lvgl as lv

CANVAS_X, CANVAS_Y = 0, 60
CANVAS_W, CANVAS_H = 640, 420
TOOLBAR_H = 60

WHEEL_SIZE = 140
WHEEL_CARD_X, WHEEL_CARD_Y = 150, 30
WHEEL_X, WHEEL_Y = 100, 48  # inside the card
WHEEL_ABS_X = WHEEL_CARD_X + WHEEL_X
WHEEL_ABS_Y = WHEEL_CARD_Y + WHEEL_Y

BG = 0x1A1A24
PANEL = 0x22222E
TEXT = 0xF5F5FA
MUTED = 0x9CA3AF
ACCENT = 0x3B82F6
WHITE = 0xFFFFFF

PRESET_COLORS = (0x111111, 0xEF4444, 0x22C55E, 0x3B82F6, 0xFFFFFF)
SAVE_PATH = "/root/drawing.png"

DEBUG_IMAGES = os.environ.get("MAIXPY_DEBUG_IMAGES") == "1"
RUN_DIR = os.environ.get("MAIXPY_SKILL_RUN_DIR")
AUTO_EXIT_SECONDS = 10.0 if (DEBUG_IMAGES and RUN_DIR) else 0.0

KEEP = []
running = [True]
draw_color = [lv.color_hex(PRESET_COLORS[0])]
brush_size = [4]
last_point = [None]
dirty = [False]
custom_rgb = [0xEF4444]
wheel_hs = [0.0, 1.0]


def color(value):
    return lv.color_hex(value)


def style_panel(obj, bg, radius=0):
    obj.set_style_bg_color(color(bg), 0)
    obj.set_style_bg_opa(lv.OPA.COVER, 0)
    obj.set_style_radius(radius, 0)
    obj.set_style_border_width(0, 0)
    obj.set_style_pad_all(0, 0)


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
    label.set_style_text_color(color(WHITE), 0)
    button.add_event_cb(callback, lv.EVENT.CLICKED, None)
    KEEP.append(callback)
    return button


def save_debug_image(driver, name="drawing_board.png"):
    if not DEBUG_IMAGES or not RUN_DIR:
        return
    art = os.path.join(RUN_DIR, "artifacts")
    os.makedirs(art, exist_ok=True)
    path = os.path.join(art, name)
    if save_screenshot(driver, path):
        print(f"MAIXPY_SKILL_IMAGE {path}", flush=True)


def main():
    disp = ts = None
    driver = None
    start = time.monotonic()

    try:
        driver, disp, ts = init_lvgl()
        scr = lv.screen_active()
        style_panel(scr, BG)

        canvas_buf = bytearray(CANVAS_W * CANVAS_H * 4)
        KEEP.append(canvas_buf)

        canvas = lv.canvas(scr)
        canvas.set_pos(CANVAS_X, CANVAS_Y)
        canvas.set_size(CANVAS_W, CANVAS_H)
        canvas.set_buffer(
            canvas_buf, CANVAS_W, CANVAS_H, lv.COLOR_FORMAT.ARGB8888
        )
        canvas.fill_bg(color(WHITE), lv.OPA.COVER)
        # lv_canvas inherits lv_image, which is not clickable by default.
        canvas.add_flag(lv.OBJ_FLAG.CLICKABLE)

        # ----------------------------------------------------------- toolbar
        toolbar = lv.obj(scr)
        toolbar.set_pos(0, 0)
        toolbar.set_size(640, TOOLBAR_H)
        style_panel(toolbar, BG)

        color_buttons = []
        custom_btn = None

        def highlight(index):
            for i, button in enumerate(color_buttons):
                button.set_style_border_width(3 if i == index else 0, 0)
                if i == index:
                    button.set_style_border_color(color(ACCENT), 0)
            custom_btn.set_style_border_width(3 if index == 5 else 0, 0)
            custom_btn.set_style_border_color(color(ACCENT), 0)

        def select_color(index):
            draw_color[0] = lv.color_hex(PRESET_COLORS[index])
            highlight(index)

        for i, value in enumerate(PRESET_COLORS):
            def make_color_cb(index=i):
                def callback(event):
                    select_color(index)
                return callback

            btn = lv.button(toolbar)
            btn.set_pos(6 + i * 42, 10)
            btn.set_size(38, 38)
            btn.set_style_bg_color(color(value), 0)
            btn.set_style_bg_opa(lv.OPA.COVER, 0)
            btn.set_style_radius(6, 0)
            btn.set_style_border_width(0, 0)
            btn.set_style_shadow_width(0, 0)
            btn.add_event_cb(make_color_cb(), lv.EVENT.CLICKED, None)
            color_buttons.append(btn)

        # Custom color entry.
        custom_btn = lv.button(toolbar)
        custom_btn.set_pos(216, 10)
        custom_btn.set_size(38, 38)
        custom_btn.set_style_bg_color(color(custom_rgb[0]), 0)
        custom_btn.set_style_bg_opa(lv.OPA.COVER, 0)
        custom_btn.set_style_radius(6, 0)
        custom_btn.set_style_border_width(0, 0)
        custom_btn.set_style_shadow_width(0, 0)
        custom_label = lv.label(custom_btn)
        custom_label.set_text("+")
        custom_label.center()
        custom_label.set_style_text_color(color(WHITE), 0)

        select_color(0)

        make_label(toolbar, "Size", 262, 4, lv.font_montserrat_14, MUTED)
        size_label = make_label(
            toolbar, str(brush_size[0]), 416, 4, lv.font_montserrat_14, TEXT
        )

        size_slider = lv.slider(toolbar)
        size_slider.set_pos(262, 28)
        size_slider.set_size(150, 14)
        size_slider.set_range(1, 16)
        size_slider.set_value(brush_size[0], lv.ANIM_ENABLE.OFF)

        def on_size(event):
            brush_size[0] = size_slider.get_value()
            size_label.set_text(str(brush_size[0]))

        size_slider.add_event_cb(on_size, lv.EVENT.VALUE_CHANGED, None)
        KEEP.append(on_size)

        def on_clear(event):
            canvas.fill_bg(color(WHITE), lv.OPA.COVER)
            dirty[0] = True

        def on_save(event):
            if image is not None:
                img = image.from_bytes(
                    CANVAS_W,
                    CANVAS_H,
                    image.Format.FMT_BGRA8888,
                    bytes(canvas_buf),
                    True,
                )
                img.save(SAVE_PATH)
            else:
                from PIL import Image

                Image.frombytes(
                    "RGBA", (CANVAS_W, CANVAS_H), bytes(canvas_buf), "raw", "BGRA"
                ).save(SAVE_PATH)
            print(f"saved {SAVE_PATH}", flush=True)

        def on_exit(event):
            running[0] = False

        make_button(toolbar, "Clear", 434, 10, 60, 40, on_clear, 0x0EA5E9)
        make_button(toolbar, "Save", 500, 10, 60, 40, on_save, 0x22C55E)
        make_button(toolbar, "Exit", 566, 10, 68, 40, on_exit, 0xEF4444)

        # ------------------------------------------------------ color picker
        overlay = lv.obj(scr)
        overlay.set_pos(0, 0)
        overlay.set_size(640, 480)
        overlay.set_style_bg_color(color(0x000000), 0)
        overlay.set_style_bg_opa(lv.OPA._50, 0)
        overlay.set_style_border_width(0, 0)
        overlay.set_style_pad_all(0, 0)
        overlay.add_flag(lv.OBJ_FLAG.CLICKABLE)
        overlay.add_flag(lv.OBJ_FLAG.HIDDEN)

        card = lv.obj(overlay)
        card.set_pos(WHEEL_CARD_X, WHEEL_CARD_Y)
        card.set_size(340, 420)
        style_panel(card, PANEL, radius=14)
        card.set_style_border_width(1, 0)
        card.set_style_border_color(color(0x35354D), 0)

        make_label(card, "Custom color", 20, 12, lv.font_montserrat_16, TEXT)

        wheel_buf = bytearray(WHEEL_SIZE * WHEEL_SIZE * 4)
        KEEP.append(wheel_buf)
        wheel_canvas = lv.canvas(card)
        wheel_canvas.set_pos(WHEEL_X, WHEEL_Y)
        wheel_canvas.set_size(WHEEL_SIZE, WHEEL_SIZE)
        wheel_canvas.set_buffer(
            wheel_buf, WHEEL_SIZE, WHEEL_SIZE, lv.COLOR_FORMAT.ARGB8888
        )
        wheel_canvas.add_flag(lv.OBJ_FLAG.CLICKABLE)

        # Draw the HSV wheel once: hue is the angle, saturation the radius,
        # value is controlled by the V slider below.
        wheel_canvas.fill_bg(color(PANEL), lv.OPA.COVER)
        radius = WHEEL_SIZE / 2.0 - 2
        center = WHEEL_SIZE / 2.0
        for y in range(WHEEL_SIZE):
            for x in range(WHEEL_SIZE):
                dx = x - center
                dy = y - center
                dist = math.hypot(dx, dy)
                if dist > radius:
                    continue
                hue = (math.degrees(math.atan2(dy, dx)) + 360.0) % 360.0
                sat = min(1.0, dist / radius)
                rr, gg, bb = colorsys.hsv_to_rgb(hue / 360.0, sat, 1.0)
                rgb = (
                    (int(rr * 255) << 16)
                    | (int(gg * 255) << 8)
                    | int(bb * 255)
                )
                wheel_canvas.set_px(x, y, lv.color_hex(rgb), lv.OPA.COVER)

        make_label(card, "Preview", 20, 200, lv.font_montserrat_14, MUTED)
        preview = lv.obj(card)
        preview.set_pos(100, 196)
        preview.set_size(200, 32)
        style_panel(preview, custom_rgb[0], radius=6)
        preview.set_style_border_width(1, 0)
        preview.set_style_border_color(color(0x55556A), 0)

        make_label(card, "V", 20, 244, lv.font_montserrat_14, MUTED)
        value_label = make_label(
            card, "255", 310, 240, lv.font_montserrat_14, TEXT
        )
        value_slider = lv.slider(card)
        value_slider.set_pos(50, 244)
        value_slider.set_size(250, 14)
        value_slider.set_range(0, 255)
        value_slider.set_value(255, lv.ANIM_ENABLE.OFF)

        def update_custom_preview():
            value = value_slider.get_value() / 255.0
            rr, gg, bb = colorsys.hsv_to_rgb(
                wheel_hs[0] / 360.0, wheel_hs[1], value
            )
            rgb = (
                (int(rr * 255) << 16)
                | (int(gg * 255) << 8)
                | int(bb * 255)
            )
            custom_rgb[0] = rgb
            preview.set_style_bg_color(color(rgb), 0)

        def wheel_point(event):
            indev = event.get_indev()
            if indev is None:
                return None
            point = lv.point_t()
            indev.get_point(point)
            x = point.x - WHEEL_ABS_X
            y = point.y - WHEEL_ABS_Y
            if 0 <= x < WHEEL_SIZE and 0 <= y < WHEEL_SIZE:
                return x, y
            return None

        def on_wheel(event):
            pos = wheel_point(event)
            if pos is None:
                return
            dx = pos[0] - center
            dy = pos[1] - center
            dist = math.hypot(dx, dy)
            if dist > radius:
                return
            wheel_hs[0] = (math.degrees(math.atan2(dy, dx)) + 360.0) % 360.0
            wheel_hs[1] = min(1.0, dist / radius)
            update_custom_preview()

        def on_value(event):
            value_label.set_text(str(value_slider.get_value()))
            update_custom_preview()

        wheel_canvas.add_event_cb(on_wheel, lv.EVENT.PRESSED, None)
        wheel_canvas.add_event_cb(on_wheel, lv.EVENT.PRESSING, None)
        value_slider.add_event_cb(on_value, lv.EVENT.VALUE_CHANGED, None)
        KEEP.extend([on_wheel, on_value])

        def close_picker(apply_color):
            if apply_color:
                draw_color[0] = lv.color_hex(custom_rgb[0])
                custom_btn.set_style_bg_color(color(custom_rgb[0]), 0)
                highlight(5)
            overlay.add_flag(lv.OBJ_FLAG.HIDDEN)

        def on_ok(event):
            close_picker(True)

        def on_cancel(event):
            close_picker(False)

        make_button(card, "OK", 60, 300, 100, 44, on_ok, 0x22C55E)
        make_button(card, "Cancel", 180, 300, 100, 44, on_cancel, 0x475569)

        def open_picker(event):
            update_custom_preview()
            overlay.remove_flag(lv.OBJ_FLAG.HIDDEN)

        custom_btn.add_event_cb(open_picker, lv.EVENT.CLICKED, None)
        KEEP.append(open_picker)

        # ----------------------------------------------------------- drawing
        def draw_dot(cx, cy, dot_radius, pen_color):
            r2 = dot_radius * dot_radius
            for dy in range(-dot_radius, dot_radius + 1):
                for dx in range(-dot_radius, dot_radius + 1):
                    if dx * dx + dy * dy > r2:
                        continue
                    x = cx + dx
                    y = cy + dy
                    if 0 <= x < CANVAS_W and 0 <= y < CANVAS_H:
                        canvas.set_px(x, y, pen_color, lv.OPA.COVER)

        def draw_line(x0, y0, x1, y1, line_radius, pen_color):
            dx = abs(x1 - x0)
            dy = abs(y1 - y0)
            sx = 1 if x0 < x1 else -1
            sy = 1 if y0 < y1 else -1
            err = dx - dy
            while True:
                draw_dot(x0, y0, line_radius, pen_color)
                if x0 == x1 and y0 == y1:
                    break
                e2 = 2 * err
                if e2 > -dy:
                    err -= dy
                    x0 += sx
                if e2 < dx:
                    err += dx
                    y0 += sy

        def canvas_point(event):
            indev = event.get_indev()
            if indev is None:
                return None
            point = lv.point_t()
            indev.get_point(point)
            x = point.x - CANVAS_X
            y = point.y - CANVAS_Y
            if 0 <= x < CANVAS_W and 0 <= y < CANVAS_H:
                return x, y
            return None

        def on_pressed(event):
            pos = canvas_point(event)
            if pos is None:
                last_point[0] = None
                return
            draw_dot(pos[0], pos[1], brush_size[0] // 2, draw_color[0])
            last_point[0] = pos
            dirty[0] = True

        def on_pressing(event):
            pos = canvas_point(event)
            if pos is None:
                last_point[0] = None
                return
            if last_point[0] is None:
                draw_dot(pos[0], pos[1], brush_size[0] // 2, draw_color[0])
            else:
                draw_line(
                    last_point[0][0],
                    last_point[0][1],
                    pos[0],
                    pos[1],
                    brush_size[0] // 2,
                    draw_color[0],
                )
            last_point[0] = pos
            dirty[0] = True

        def on_released(event):
            last_point[0] = None

        canvas.add_event_cb(on_pressed, lv.EVENT.PRESSED, None)
        canvas.add_event_cb(on_pressing, lv.EVENT.PRESSING, None)
        canvas.add_event_cb(on_released, lv.EVENT.RELEASED, None)
        KEEP.extend([on_pressed, on_pressing, on_released])

        if DEBUG_IMAGES:
            # Draw a visible test pattern and open the color wheel for the
            # capture.
            for i in range(10):
                draw_line(
                    40 + i * 55,
                    30,
                    40,
                    390,
                    brush_size[0],
                    lv.color_hex(PRESET_COLORS[1 + (i % 4)]),
                )
            for i in range(5):
                draw_line(
                    40,
                    390 - i * 80,
                    600,
                    30 + i * 80,
                    brush_size[0],
                    lv.color_hex(PRESET_COLORS[1 + (i % 4)]),
                )
            dirty[0] = True
            overlay.remove_flag(lv.OBJ_FLAG.HIDDEN)

        # ------------------------------------------------------------ main loop
        while not need_exit() and running[0]:
            lv.timer_handler()
            if dirty[0]:
                canvas.invalidate()
                lv.refr_now(driver._disp)
                dirty[0] = False

            if AUTO_EXIT_SECONDS and time.monotonic() - start >= AUTO_EXIT_SECONDS:
                save_debug_image(driver)
                break
            time.sleep(0.005)

    finally:
        deinit_lvgl(driver, disp, ts)


if __name__ == "__main__":
    main()
