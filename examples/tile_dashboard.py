"""HomeTiles-style smart-home dashboard for MaixCAM2 (maix_lvgl).

Run on the device:
    python tile_dashboard.py

Tap cards for details, use the top-right Exit button to quit.
Debug capture is disabled unless MAIXPY_DEBUG_IMAGES=1.
"""
import os
import time

from maix import app, display, image, touchscreen

import maix_lvgl as lv

BG = 0x0A0A0F
CARD = 0x16161D
CARD_BORDER = 0x2A2A36
TEXT = 0xF5F5FA
MUTED = 0x9CA3AF
ACCENT = 0x39FF88
AMBER = 0xF7FF3A
ORANGE = 0xFF8A3D
PURPLE = 0x8B5CF6
RED = 0xEF4444
BLUE = 0x3B82F6

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


def panel(parent, x, y, width, height, bg, radius=18, border=0, border_color=None):
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
    return obj


def label(parent, text, x, y, font=None, text_color=TEXT):
    item = lv.label(parent)
    item.set_text(text)
    item.set_pos(x, y)
    item.set_style_text_color(color(text_color), 0)
    item.set_style_text_font(font or lv.font_montserrat_14, 0)
    return item


def button(parent, text, x, y, width, height, callback, bg=ACCENT, font=None):
    item = lv.button(parent)
    item.set_pos(x, y)
    item.set_size(width, height)
    item.set_style_bg_color(color(bg), 0)
    item.set_style_bg_opa(lv.OPA.COVER, 0)
    item.set_style_radius(10, 0)
    item.set_style_shadow_width(0, 0)
    text_label = lv.label(item)
    text_label.set_text(text)
    text_label.center()
    text_label.set_style_text_color(color(0xFFFFFF), 0)
    text_label.set_style_text_font(font or lv.font_montserrat_14, 0)
    item.add_event_cb(callback, lv.EVENT.CLICKED, None)
    KEEP.append(callback)
    return item


def tr(zh_text, en_text):
    return zh_text if zh else en_text


def save_debug(driver, name="tile_dashboard.png"):
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


def open_modal(scr, title, body):
    overlay = lv.obj(scr)
    overlay.set_pos(0, 0)
    overlay.set_size(640, 480)
    overlay.set_style_bg_color(color(0x000000), 0)
    overlay.set_style_bg_opa(lv.OPA._70, 0)
    overlay.set_style_border_width(0, 0)
    overlay.add_flag(lv.OBJ_FLAG.CLICKABLE)

    card = panel(overlay, 100, 90, 440, 300, 0x1A1A24, radius=20,
                 border=1, border_color=0x333344)
    label(card, title, 24, 20, ui_font or lv.font_montserrat_20, TEXT)
    label(card, body, 24, 70, ui_font_small or lv.font_montserrat_14, MUTED)

    def close(event):
        overlay.delete()

    KEEP.append(close)
    button(card, tr("关闭", "Close"), 24, 230, 110, 42, close, RED,
           ui_font or lv.font_montserrat_14)
    overlay.add_event_cb(close, lv.EVENT.CLICKED, None)
    KEEP.append(close)
    return overlay


def build_light_card(scr, x, y):
    card = panel(scr, x, y, 196, 190, CARD, radius=18,
                 border=1, border_color=CARD_BORDER)
    label(card, tr("灯光", "Light"), 16, 12, ui_font or lv.font_montserrat_16, MUTED)
    label(card, lv.SYMBOL.POWER, 150, 10, lv.font_montserrat_20, AMBER)
    state = label(card, tr("开", "ON"), 16, 46, ui_font or lv.font_montserrat_24, TEXT)

    def toggle(event):
        switch_state = not switch.has_state(lv.STATE.CHECKED)
        switch.add_state(lv.STATE.CHECKED) if switch_state else switch.remove_state(lv.STATE.CHECKED)
        state.set_text(tr("开", "ON") if switch_state else tr("关", "OFF"))
        state.set_style_text_color(color(ACCENT if switch_state else MUTED), 0)

    switch = lv.switch(card)
    switch.set_pos(16, 130)
    switch.set_size(64, 32)
    switch.add_state(lv.STATE.CHECKED)
    switch.add_event_cb(toggle, lv.EVENT.VALUE_CHANGED, None)
    KEEP.append(toggle)
    label(card, tr("客厅主灯", "Living room"), 16, 170, ui_font_small or lv.font_montserrat_12, MUTED)
    return card


def build_climate_card(scr, x, y):
    card = panel(scr, x, y, 196, 190, CARD, radius=18,
                 border=1, border_color=CARD_BORDER)
    label(card, tr("温控", "Climate"), 16, 12, ui_font or lv.font_montserrat_16, MUTED)
    value = label(card, "21.5°C", 16, 46, lv.font_montserrat_24, TEXT)
    arc = lv.arc(card)
    arc.set_pos(104, 66)
    arc.set_size(76, 76)
    arc.set_range(16, 30)
    arc.set_value(22)
    arc.set_bg_angles(135, 45)
    arc.set_angles(135, 45)
    arc.set_style_arc_color(color(ORANGE), lv.PART.INDICATOR)
    arc.set_style_arc_width(6, lv.PART.INDICATOR)

    def adjust(delta):
        def handler(event):
            current = arc.get_value() + delta
            current = max(16.0, min(30.0, current))
            arc.set_value(int(round(current)))
            value.set_text(f"{current:.1f}°C")

        KEEP.append(handler)
        return handler

    button(card, "-", 16, 136, 44, 36, adjust(-0.5), CARD_BORDER, lv.font_montserrat_20)
    button(card, "+", 68, 136, 44, 36, adjust(0.5), CARD_BORDER, lv.font_montserrat_20)
    label(card, tr("目标温度", "Target"), 16, 174, ui_font_small or lv.font_montserrat_12, MUTED)
    return card


def build_weather_card(scr, x, y):
    card = panel(scr, x, y, 196, 190, CARD, radius=18,
                 border=1, border_color=CARD_BORDER)
    label(card, tr("天气", "Weather"), 16, 12, ui_font or lv.font_montserrat_16, MUTED)
    label(card, "18°", 16, 42, lv.font_montserrat_32, TEXT)
    label(card, tr("多云", "Partly cloudy"), 16, 96, ui_font or lv.font_montserrat_14, MUTED)
    label(card, tr("最高 15°  最低 8°", "H 15°   L 8°"), 16, 128, ui_font_small or lv.font_montserrat_12, MUTED)
    label(card, lv.SYMBOL.TINT, 150, 44, lv.font_montserrat_24, BLUE)

    def show(event):
        open_modal(
            scr, tr("未来 5 天", "5-day forecast"),
            tr("今天  多云  15°/8°\n明天  晴    20°/14°\n周五  小雨  18°/13°\n周六  多云  16°/9°\n周日  晴    21°/15°",
               "Today  Partly cloudy  15/8\nThu    Sunny          20/14\nFri    Light rain     18/13\nSat    Cloudy         16/9\nSun    Sunny          21/15"),
        )

    KEEP.append(show)
    card.add_event_cb(show, lv.EVENT.CLICKED, None)
    return card


def build_media_card(scr, x, y):
    card = panel(scr, x, y, 196, 190, CARD, radius=18,
                 border=1, border_color=CARD_BORDER)
    label(card, tr("媒体", "Media"), 16, 12, ui_font or lv.font_montserrat_16, MUTED)

    cover = panel(card, 16, 42, 70, 70, PURPLE, radius=14)
    cover.set_style_bg_grad_color(color(0x4C1D95), 0)
    cover.set_style_bg_grad_dir(lv.GRAD_DIR.VER, 0)
    cover.set_style_shadow_width(12, 0)
    cover.set_style_shadow_color(color(PURPLE), 0)
    cover.set_style_shadow_opa(lv.OPA._40, 0)
    label(cover, lv.SYMBOL.AUDIO, 22, 14, lv.font_montserrat_32, TEXT)

    label(card, tr("月光", "Clair de Lune"), 96, 48, ui_font or lv.font_montserrat_14, TEXT)
    label(card, "Debussy", 96, 70, lv.font_montserrat_12, MUTED)

    state = {"playing": True}
    play_button = lv.button(card)
    play_button.set_pos(16, 128)
    play_button.set_size(44, 36)
    play_button.set_style_bg_color(color(PURPLE), 0)
    play_button.set_style_bg_opa(lv.OPA.COVER, 0)
    play_button.set_style_radius(10, 0)
    play_label = lv.label(play_button)
    play_label.set_text(lv.SYMBOL.PAUSE)
    play_label.center()
    play_label.set_style_text_color(color(0xFFFFFF), 0)

    def toggle_play(event):
        state["playing"] = not state["playing"]
        play_label.set_text(lv.SYMBOL.PAUSE if state["playing"] else lv.SYMBOL.PLAY)

    play_button.add_event_cb(toggle_play, lv.EVENT.CLICKED, None)
    KEEP.append(toggle_play)
    label(card, tr("正在播放", "Now playing"), 16, 172, ui_font_small or lv.font_montserrat_12, MUTED)
    return card, cover, state


def build_energy_card(scr, x, y):
    card = panel(scr, x, y, 196, 190, CARD, radius=18,
                 border=1, border_color=CARD_BORDER)
    label(card, tr("能耗", "Energy"), 16, 12, ui_font or lv.font_montserrat_16, MUTED)
    label(card, "2.8 kW", 16, 40, lv.font_montserrat_24, TEXT)
    chart = lv.chart(card)
    chart.set_pos(16, 78)
    chart.set_size(164, 82)
    chart.set_type(lv.chart.TYPE.BAR)
    chart.set_range(lv.chart.AXIS.PRIMARY_Y, 0, 100)
    chart.set_point_count(7)
    chart.set_div_line_count(2, 0)
    chart.set_style_bg_opa(lv.OPA.TRANSP, 0)
    chart.set_style_border_width(0, 0)
    series = chart.add_series(color(ACCENT), lv.chart.AXIS.PRIMARY_Y)
    for value in (40, 58, 32, 72, 60, 84, 52):
        chart.set_next_value(series, value)
    label(card, tr("本周用电", "This week"), 16, 168, ui_font_small or lv.font_montserrat_12, MUTED)
    return card


def build_security_card(scr, x, y):
    card = panel(scr, x, y, 196, 190, CARD, radius=18,
                 border=1, border_color=CARD_BORDER)
    label(card, tr("安防", "Security"), 16, 12, ui_font or lv.font_montserrat_16, MUTED)
    state = label(card, tr("已上锁", "Locked"), 16, 46, ui_font or lv.font_montserrat_20, ACCENT)
    label(card, lv.SYMBOL.HOME, 150, 44, lv.font_montserrat_24, ACCENT)

    def toggle(event):
        locked = not switch.has_state(lv.STATE.CHECKED)
        if locked:
            switch.add_state(lv.STATE.CHECKED)
        else:
            switch.remove_state(lv.STATE.CHECKED)
        state.set_text(tr("已上锁", "Locked") if locked else tr("已解锁", "Unlocked"))
        state.set_style_text_color(color(ACCENT if locked else RED), 0)

    switch = lv.switch(card)
    switch.set_pos(16, 126)
    switch.set_size(64, 32)
    switch.add_state(lv.STATE.CHECKED)
    switch.add_event_cb(toggle, lv.EVENT.VALUE_CHANGED, None)
    KEEP.append(toggle)
    label(card, tr("前门门锁", "Front door"), 16, 168, ui_font_small or lv.font_montserrat_12, MUTED)
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

        header = panel(scr, 0, 0, 640, 48, 0x111118, radius=0)
        label(header, tr("首页", "Home"), 16, 10, font or lv.font_montserrat_20, TEXT)
        clock = label(header, "--:--", 250, 14, lv.font_montserrat_16, TEXT)
        date_label = label(header, "", 330, 16, lv.font_montserrat_12, MUTED)

        def show_about(event):
            open_modal(scr, tr("关于", "About"),
                       "HomeTiles-style dashboard\nmaix_lvgl · LVGL 9.1 · 640x480")

        KEEP.append(show_about)
        button(header, lv.SYMBOL.SETTINGS, 520, 8, 36, 32, show_about, 0x22222C,
               lv.font_montserrat_16)

        def on_exit(event):
            running[0] = False

        button(header, tr("退出", "Exit"), 566, 8, 64, 32, on_exit, RED,
               font or lv.font_montserrat_14)

        build_light_card(scr, 14, 60)
        build_climate_card(scr, 222, 60)
        build_weather_card(scr, 430, 60)
        _, cover, media_state = build_media_card(scr, 14, 260)
        build_energy_card(scr, 222, 260)
        build_security_card(scr, 430, 260)

        label(scr, "HomeTiles style  |  LVGL 9.1  |  640x480", 14, 460,
              lv.font_montserrat_12, MUTED)

        start = time.monotonic()
        last_status = start
        last_shot = start
        angle = 0
        while not app.need_exit() and running[0]:
            lv.timer_handler()
            now = time.monotonic()

            if media_state["playing"]:
                angle = (angle + 3) % 3600
                cover.set_style_transform_pivot_x(35, 0)
                cover.set_style_transform_pivot_y(35, 0)
                cover.set_style_transform_rotation(angle, 0)

            if now - last_status >= 0.25:
                last_status = now
                clock.set_text(time.strftime("%H:%M"))
                date_label.set_text(time.strftime("%a, %d %b"))

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
