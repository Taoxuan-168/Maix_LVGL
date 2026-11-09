"""Project-Aura-style neon air-quality dashboard for MaixCAM2 (maix_lvgl).

Run on the device:
    python neon_dashboard.py

Tap the CO2 card for a 24h history chart; Exit button quits.
Debug capture is disabled unless MAIXPY_DEBUG_IMAGES=1.
"""
import math
import os
import time

from maix import app, display, image, touchscreen

import maix_lvgl as lv

BG = 0x050507
CARD = 0x0B0B0D
GREEN = 0x39FF88
YELLOW = 0xF7FF3A
ORANGE = 0xFF8A3D
CYAN = 0x3AF7FF
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
neon_cards = []


def color(value):
    return lv.color_hex(value)


def panel(parent, x, y, width, height, bg, radius=14, border=0, border_color=None):
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


def neon_card(parent, x, y, accent, title):
    card = panel(parent, x, y, 196, 190, CARD, radius=14,
                 border=2, border_color=accent)
    card.set_style_shadow_width(0, 0)
    label(card, title, 14, 10, ui_font or lv.font_montserrat_16, MUTED)
    neon_cards.append((card, accent))
    return card


def label(parent, text, x, y, font=None, text_color=TEXT):
    item = lv.label(parent)
    item.set_text(text)
    item.set_pos(x, y)
    item.set_style_text_color(color(text_color), 0)
    item.set_style_text_font(font or lv.font_montserrat_14, 0)
    return item


def button(parent, text, x, y, width, height, callback, bg=GREEN, font=None):
    item = lv.button(parent)
    item.set_pos(x, y)
    item.set_size(width, height)
    item.set_style_bg_color(color(bg), 0)
    item.set_style_bg_opa(lv.OPA.COVER, 0)
    item.set_style_radius(8, 0)
    item.set_style_shadow_width(0, 0)
    text_label = lv.label(item)
    text_label.set_text(text)
    text_label.center()
    text_label.set_style_text_color(color(0x000000), 0)
    text_label.set_style_text_font(font or lv.font_montserrat_14, 0)
    item.add_event_cb(callback, lv.EVENT.CLICKED, None)
    KEEP.append(callback)
    return item


def tr(zh_text, en_text):
    return zh_text if zh else en_text


def save_debug(driver, name="neon_dashboard.png"):
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


def open_history(scr, co2_value):
    overlay = lv.obj(scr)
    overlay.set_pos(0, 0)
    overlay.set_size(640, 480)
    overlay.set_style_bg_color(color(0x000000), 0)
    overlay.set_style_bg_opa(lv.OPA._80, 0)
    overlay.set_style_border_width(0, 0)
    overlay.add_flag(lv.OBJ_FLAG.CLICKABLE)

    card = panel(overlay, 70, 80, 500, 320, CARD, radius=16,
                 border=2, border_color=GREEN)
    label(card, tr("CO2 24 小时趋势", "CO2 24h history"), 20, 16,
          ui_font or lv.font_montserrat_20, TEXT)
    label(card, f"{co2_value} ppm", 20, 50, lv.font_montserrat_24, GREEN)

    chart = lv.chart(card)
    chart.set_pos(20, 90)
    chart.set_size(460, 180)
    chart.set_type(lv.chart.TYPE.LINE)
    chart.set_range(lv.chart.AXIS.PRIMARY_Y, 0, 2000)
    chart.set_point_count(40)
    chart.set_div_line_count(3, 6)
    chart.set_style_bg_opa(lv.OPA.TRANSP, 0)
    chart.set_style_border_width(0, 0)
    series = chart.add_series(color(GREEN), lv.chart.AXIS.PRIMARY_Y)
    for i in range(40):
        chart.set_next_value(series, int(1200 + 300 * math.sin(i / 4.0)))

    def close(event):
        overlay.delete()

    KEEP.append(close)
    button(card, tr("关闭", "Close"), 20, 282, 100, 28, close, GREEN,
           ui_font_small or lv.font_montserrat_14)
    overlay.add_event_cb(close, lv.EVENT.CLICKED, None)
    KEEP.append(close)


def build_co2_card(scr, x, y):
    card = neon_card(scr, x, y, GREEN, tr("二氧化碳", "CO2"))
    value = label(card, "1498", 14, 40, lv.font_montserrat_32, GREEN)
    label(card, "ppm", 118, 58, lv.font_montserrat_12, MUTED)
    bar = lv.bar(card)
    bar.set_pos(14, 104)
    bar.set_size(168, 10)
    bar.set_range(0, 2000)
    bar.set_value(1498, 0)
    bar.set_style_bg_color(color(0x1F2A22), 0)
    bar.set_style_bg_opa(lv.OPA.COVER, 0)
    bar.set_style_bg_color(color(GREEN), lv.PART.INDICATOR)
    label(card, tr("偏高 · 建议通风", "HIGH - VENTILATE"), 14, 126,
          ui_font_small or lv.font_montserrat_12, YELLOW)
    label(card, "STATUS", 14, 158, lv.font_montserrat_12, MUTED)

    def show(event):
        open_history(scr, int(value.get_text()) if value.get_text().isdigit() else 1498)

    KEEP.append(show)
    card.add_event_cb(show, lv.EVENT.CLICKED, None)
    return card, value, bar


def build_temp_card(scr, x, y):
    card = neon_card(scr, x, y, YELLOW, tr("温度", "TEMP"))
    label(card, "24.6", 14, 40, lv.font_montserrat_32, TEXT)
    label(card, "°C", 106, 58, lv.font_montserrat_14, MUTED)
    label(card, tr("舒适", "COMFORT"), 14, 96, ui_font_small or lv.font_montserrat_12, GREEN)
    chart = lv.chart(card)
    chart.set_pos(14, 120)
    chart.set_size(168, 56)
    chart.set_type(lv.chart.TYPE.LINE)
    chart.set_range(lv.chart.AXIS.PRIMARY_Y, 200, 300)
    chart.set_point_count(20)
    chart.set_style_bg_opa(lv.OPA.TRANSP, 0)
    chart.set_style_border_width(0, 0)
    series = chart.add_series(color(YELLOW), lv.chart.AXIS.PRIMARY_Y)
    for i in range(20):
        chart.set_next_value(series, int(246 + 5 * math.sin(i / 3.0)))
    return card, chart, series


def build_humidity_card(scr, x, y):
    card = neon_card(scr, x, y, CYAN, tr("湿度", "HUMIDITY"))
    for index, (name, value) in enumerate(
        ((tr("相对", "RH"), "50 %"), (tr("绝对", "AH"), "11 g/m3"), (tr("露点", "DP"), "13 °C"))
    ):
        label(card, name, 14, 40 + index * 38, ui_font_small or lv.font_montserrat_12, MUTED)
        label(card, value, 84, 34 + index * 38, lv.font_montserrat_16, TEXT)
        dot = lv.obj(card)
        dot.set_pos(180, 44 + index * 38)
        dot.set_size(10, 10)
        dot.set_style_bg_color(color(GREEN), 0)
        dot.set_style_bg_opa(lv.OPA.COVER, 0)
        dot.set_style_radius(5, 0)
        dot.set_style_border_width(0, 0)
    return card


def build_particle_card(scr, x, y):
    card = neon_card(scr, x, y, ORANGE, tr("颗粒物", "PARTICLES"))
    label(card, "PM2.5", 14, 42, lv.font_montserrat_12, MUTED)
    label(card, "6.2", 14, 60, lv.font_montserrat_24, TEXT)
    label(card, "ug/m3", 14, 94, lv.font_montserrat_12, MUTED)
    label(card, "PM10", 110, 42, lv.font_montserrat_12, MUTED)
    label(card, "9.0", 110, 60, lv.font_montserrat_24, TEXT)
    label(card, "ug/m3", 110, 94, lv.font_montserrat_12, MUTED)
    label(card, tr("空气质量良好", "AIR QUALITY GOOD"), 14, 130,
          ui_font_small or lv.font_montserrat_12, GREEN)
    return card


def build_voc_card(scr, x, y):
    card = neon_card(scr, x, y, GREEN, tr("挥发性气体", "VOC / NOx"))
    label(card, "VOC", 14, 42, lv.font_montserrat_12, MUTED)
    label(card, "31", 14, 60, lv.font_montserrat_24, TEXT)
    label(card, tr("指数", "Index"), 60, 70, ui_font_small or lv.font_montserrat_12, MUTED)
    label(card, "NOx", 110, 42, lv.font_montserrat_12, MUTED)
    label(card, "1", 110, 60, lv.font_montserrat_24, TEXT)
    label(card, tr("指数", "Index"), 132, 70, ui_font_small or lv.font_montserrat_12, MUTED)
    label(card, tr("全部正常", "ALL NORMAL"), 14, 130,
          ui_font_small or lv.font_montserrat_12, GREEN)
    return card


def build_time_card(scr, x, y):
    card = neon_card(scr, x, y, YELLOW, tr("时间", "TIME"))
    clock = label(card, "--:--", 14, 38, lv.font_montserrat_32, TEXT)
    date = label(card, "", 14, 84, lv.font_montserrat_14, MUTED)
    label(card, tr("设备在线", "DEVICE ONLINE"), 14, 130,
          ui_font_small or lv.font_montserrat_12, GREEN)
    return card, clock, date


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

        header = panel(scr, 0, 0, 640, 52, BG, radius=0)
        label(header, "AURA", 14, 8, lv.font_montserrat_24, GREEN)
        label(header, "AIR QUALITY MONITOR", 16, 34, lv.font_montserrat_12, MUTED)

        status = panel(header, 220, 10, 280, 32, 0x0A0A0A, radius=6,
                       border=1, border_color=YELLOW)
        label(status, tr("状态：CO2 偏高 - 建议通风", "STATUS: CO2 HIGH - VENTILATE SOON"),
              8, 9, ui_font_small or lv.font_montserrat_12, YELLOW)

        def on_exit(event):
            running[0] = False

        button(header, tr("退出", "Exit"), 560, 10, 66, 30, on_exit, RED,
               ui_font_small or lv.font_montserrat_12)

        _, co2_value, co2_bar = build_co2_card(scr, 14, 62)
        _, temp_chart, temp_series = build_temp_card(scr, 222, 62)
        build_humidity_card(scr, 430, 62)
        build_particle_card(scr, 14, 260)
        build_voc_card(scr, 222, 260)
        _, clock, date = build_time_card(scr, 430, 260)

        footer = label(scr, "UPTIME 00:00  |  FPS 0  |  LVGL 9.1", 14, 458,
                       lv.font_montserrat_12, MUTED)

        start = time.monotonic()
        last_update = start
        last_shot = start
        phase = 0.0
        while not app.need_exit() and running[0]:
            lv.timer_handler()
            now = time.monotonic()

            breath = 140 + int(100 * (0.5 + 0.5 * math.sin(now * 2.0)))
            for card, _accent in neon_cards:
                card.set_style_border_opa(breath, 0)

            if now - last_update >= 0.4:
                last_update = now
                phase += 0.35
                co2 = int(1450 + 120 * math.sin(phase))
                co2_value.set_text(str(co2))
                co2_bar.set_value(co2, 0)
                temp_chart.set_next_value(temp_series, int(246 + 4 * math.sin(phase * 0.7)))
                clock.set_text(time.strftime("%H:%M"))
                date.set_text(time.strftime("%d.%m.%Y"))
                uptime = now - start
                footer.set_text(
                    f"UPTIME {int(uptime // 60):02d}:{int(uptime % 60):02d}  |  "
                    f"CO2 {co2} ppm  |  LVGL 9.1"
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
