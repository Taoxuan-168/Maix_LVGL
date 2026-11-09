"""ZSWatch-style neon watchface for MaixCAM2 (maix_lvgl).

Run on the device:
    python watchface.py

Tap the dial to cycle color themes; Exit button quits.
Debug capture is disabled unless MAIXPY_DEBUG_IMAGES=1.
"""
import os
import time

from maix import app, display, image, touchscreen

import maix_lvgl as lv

BG = 0x05060A
DIAL_BG = 0x0B0D14
CARD = 0x10131C
GREEN = 0x39FF88
CYAN = 0x3AF7FF
ORANGE = 0xFF8A3D
PINK = 0xFF4FD8
BLUE = 0x4F8CFF
TEXT = 0xF5F5FA
MUTED = 0x8B8B96
RED = 0xEF4444

FONT_PATH = "/maixapp/share/font/SourceHanSansCN-Regular.otf"
DEBUG_IMAGES = os.environ.get("MAIXPY_DEBUG_IMAGES") == "1"
RUN_DIR = os.environ.get("MAIXPY_SKILL_RUN_DIR")
AUTO_EXIT_SECONDS = 12.0 if (DEBUG_IMAGES and RUN_DIR) else 0.0

KEEP = []
running = [True]
zh = False
ui_font = None
ui_font_small = None


def color(value):
    return lv.color_hex(value)


def panel(parent, x, y, width, height, bg, radius=0, border=0, border_color=None):
    obj = lv.obj(parent)
    obj.set_pos(x, y)
    obj.set_size(width, height)
    obj.set_style_bg_color(color(bg), 0)
    obj.set_style_bg_opa(lv.OPA.COVER, 0)
    obj.set_style_radius(radius, 0)
    obj.set_style_border_width(border, 0)
    if border_color is not None:
        obj.set_style_border_color(color(border_color), 0)
    obj.set_style_pad_all(0, 0)
    obj.set_style_shadow_width(0, 0)
    obj.set_scroll_dir(lv.DIR.NONE)
    obj.set_scrollbar_mode(lv.SCROLLBAR_MODE.OFF)
    return obj


def label(parent, text, x, y, font=None, text_color=TEXT, width=None):
    item = lv.label(parent)
    item.set_text(text)
    item.set_pos(x, y)
    item.set_style_text_color(color(text_color), 0)
    item.set_style_text_font(font or lv.font_montserrat_14, 0)
    if width is not None:
        item.set_width(width)
        item.set_style_text_align(lv.TEXT_ALIGN.CENTER, 0)
    return item


def tr(zh_text, en_text):
    return zh_text if zh else en_text


def save_debug(driver, name="watchface.png"):
    if not DEBUG_IMAGES or not RUN_DIR:
        return
    art = os.path.join(RUN_DIR, "artifacts")
    os.makedirs(art, exist_ok=True)
    path = os.path.join(art, name)
    img = image.from_bytes(
        driver.width, driver.height, image.Format.FMT_BGRA8888,
        bytes(driver._buffer), True,
    )
    img.save(path)
    print(f"MAIXPY_SKILL_IMAGE {path}", flush=True)


def stat_card(scr, x, y, title, value, unit, accent):
    card = panel(scr, x, y, 110, 90, CARD, radius=14,
                 border=1, border_color=0x242838)
    label(card, title, 10, 8, ui_font_small or lv.font_montserrat_12, MUTED)
    label(card, value, 10, 28, lv.font_montserrat_20, TEXT)
    label(card, unit, 10, 62, ui_font_small or lv.font_montserrat_12, accent)
    return card


def main():
    global zh, ui_font, ui_font_small
    disp = display.Display()
    ts = touchscreen.TouchScreen()
    driver = None
    font = None
    font_small = None
    try:
        driver = lv.init(disp, ts)
        scr = lv.screen_active()
        scr.set_style_bg_color(color(BG), 0)
        scr.set_style_bg_opa(lv.OPA.COVER, 0)

        font = lv.freetype_font_create(FONT_PATH, 0, 20, 0)
        font_small = lv.freetype_font_create(FONT_PATH, 0, 12, 0)
        zh = font is not None
        ui_font = font
        ui_font_small = font_small or font or lv.font_montserrat_12

        header = panel(scr, 0, 0, 640, 48, 0x080A10)
        label(header, tr("腕表", "ZSWatch"), 18, 10,
              ui_font or lv.font_montserrat_20, TEXT)
        label(header, "ZSWatch style  |  LVGL 9.1", 120, 16,
              lv.font_montserrat_12, MUTED)

        def on_exit(event):
            running[0] = False

        exit_button = lv.button(header)
        exit_button.set_pos(566, 8)
        exit_button.set_size(64, 32)
        exit_button.set_style_bg_color(color(RED), 0)
        exit_button.set_style_bg_opa(lv.OPA.COVER, 0)
        exit_button.set_style_radius(10, 0)
        exit_label = lv.label(exit_button)
        exit_label.set_text(tr("退出", "Exit"))
        exit_label.set_style_text_font(ui_font_small or lv.font_montserrat_12, 0)
        exit_label.set_style_text_color(color(0xFFFFFF), 0)
        exit_label.center()
        exit_button.add_event_cb(on_exit, lv.EVENT.CLICKED, None)
        KEEP.append(on_exit)

        dial = panel(scr, 140, 60, 360, 360, DIAL_BG, radius=180,
                     border=2, border_color=GREEN)
        dial.add_flag(lv.OBJ_FLAG.CLICKABLE)

        outer = lv.arc(dial)
        outer.set_pos(10, 10)
        outer.set_size(340, 340)
        outer.set_bg_angles(135, 45)
        outer.set_angles(135, 45)
        outer.set_range(0, 100)
        outer.set_value(70)
        outer.set_style_arc_width(4, lv.PART.MAIN)
        outer.set_style_arc_width(8, lv.PART.INDICATOR)
        outer.set_style_arc_color(color(0x1A2030), lv.PART.MAIN)
        outer.set_style_arc_color(color(GREEN), lv.PART.INDICATOR)
        outer.set_style_bg_opa(lv.OPA.TRANSP, lv.PART.KNOB)
        outer.set_style_border_width(0, lv.PART.KNOB)

        inner = lv.arc(dial)
        inner.set_pos(30, 30)
        inner.set_size(300, 300)
        inner.set_bg_angles(135, 45)
        inner.set_angles(135, 45)
        inner.set_range(0, 100)
        inner.set_value(84)
        inner.set_style_arc_width(3, lv.PART.MAIN)
        inner.set_style_arc_width(6, lv.PART.INDICATOR)
        inner.set_style_arc_color(color(0x1A2030), lv.PART.MAIN)
        inner.set_style_arc_color(color(CYAN), lv.PART.INDICATOR)
        inner.set_style_bg_opa(lv.OPA.TRANSP, lv.PART.KNOB)
        inner.set_style_border_width(0, lv.PART.KNOB)

        hand = panel(dial, 179, 110, 2, 130, RED, radius=1)
        hand.set_style_transform_pivot_x(1, 0)
        hand.set_style_transform_pivot_y(130, 0)
        hub = panel(dial, 174, 234, 12, 12, RED, radius=6)

        time_label = label(dial, "00:00", 80, 176, lv.font_montserrat_32, TEXT, width=200)
        date_label = label(dial, "", 80, 222, ui_font_small or lv.font_montserrat_12,
                           MUTED, width=200)
        weather_label = label(dial, tr("17°C  多云", "17°C  Cloudy"),
                              80, 248, ui_font or lv.font_montserrat_14, TEXT, width=200)
        steps_label = label(dial, tr("9999 步", "9999 steps"),
                            80, 278, ui_font_small or lv.font_montserrat_12,
                            GREEN, width=200)

        stat_card(scr, 10, 80, tr("步数", "STEPS"), "9999", tr("步", "steps"), GREEN)
        stat_card(scr, 10, 180, tr("天气", "WEATHER"), "17°C", tr("多云", "Cloudy"), CYAN)
        stat_card(scr, 10, 280, tr("通知", "NOTIFY"), "2", tr("条", "new"), PINK)
        stat_card(scr, 520, 80, tr("电量", "BATTERY"), "100%", tr("满电", "full"), GREEN)
        stat_card(scr, 520, 180, tr("心率", "HEART"), "72", "bpm", PINK)
        stat_card(scr, 520, 280, tr("日期", "DATE"), time.strftime("%d"), tr("八月", "Aug"), ORANGE)

        themes = [(GREEN, CYAN, RED), (ORANGE, PINK, ORANGE), (BLUE, GREEN, BLUE)]
        theme_index = [0]

        def next_theme(event):
            theme_index[0] = (theme_index[0] + 1) % len(themes)
            accent, second, hand_color = themes[theme_index[0]]
            dial.set_style_border_color(color(accent), 0)
            outer.set_style_arc_color(color(accent), lv.PART.INDICATOR)
            inner.set_style_arc_color(color(second), lv.PART.INDICATOR)
            hand.set_style_bg_color(color(hand_color), 0)
            hub.set_style_bg_color(color(hand_color), 0)

        dial.add_event_cb(next_theme, lv.EVENT.CLICKED, None)
        KEEP.append(next_theme)

        footer = label(scr, "ZSWatch style  |  LVGL 9.1  |  640x480", 140, 458,
                       lv.font_montserrat_12, MUTED)

        start = time.monotonic()
        last_tick = start
        last_shot = start
        while not app.need_exit() and running[0]:
            lv.timer_handler()
            now = time.monotonic()
            if now - last_tick >= 0.1:
                last_tick = now
                local = time.localtime()
                time_label.set_text(time.strftime("%H:%M", local))
                date_label.set_text(time.strftime("%A  %d %B", local))
                angle = (local.tm_sec * 60) % 3600
                hand.set_style_transform_rotation(angle, 0)
                steps_label.set_text(
                    tr(f"{9999 + int(now - start) * 3} 步",
                       f"{9999 + int(now - start) * 3} steps")
                )
                footer.set_text(
                    f"ZSWatch style  |  {time.strftime('%H:%M:%S', local)}  |  LVGL 9.1"
                )

            if DEBUG_IMAGES and RUN_DIR and now - last_shot >= 2.0:
                last_shot = now
                save_debug(driver)

            if AUTO_EXIT_SECONDS and now - start >= AUTO_EXIT_SECONDS:
                running[0] = False

            time.sleep(0.005)
    finally:
        try:
            lv.screen_active().clean()
        except Exception:
            pass
        if font_small is not None:
            try:
                font_small.freetype_font_delete()
            except Exception:
                pass
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
