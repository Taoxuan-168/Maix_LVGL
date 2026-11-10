"""LVGL-Music-style player for MaixCAM2 (maix_lvgl).

Run on the device:
    python music_player.py

Tap play/pause, prev/next, seek or volume. Exit button quits.
Debug capture is disabled unless MAIXPY_DEBUG_IMAGES=1.
"""
import math
import os
import time

from _common import HAS_MAIX, deinit_lvgl, init_lvgl, need_exit, save_screenshot

import maix_lvgl as lv

BG_TOP = 0x120A20
BG_BOTTOM = 0x2A0F3A
PURPLE = 0x8B5CF6
PINK = 0xEC4899
CYAN = 0x22D3EE
TEXT = 0xF5F5FA
MUTED = 0x9CA3AF
RED = 0xEF4444
DARK = 0x1A1A2A

FONT_PATH = "/maixapp/share/font/SourceHanSansCN-Regular.otf"
DEBUG_IMAGES = os.environ.get("MAIXPY_DEBUG_IMAGES") == "1"
RUN_DIR = os.environ.get("MAIXPY_SKILL_RUN_DIR")
AUTO_EXIT_SECONDS = 12.0 if (DEBUG_IMAGES and RUN_DIR) else 0.0

KEEP = []
running = [True]
zh = False
ui_font = None
ui_font_small = None

SONGS = [
    ("月光", "Clair de Lune", "Claude Debussy"),
    ("夜曲", "Nocturne", "Frédéric Chopin"),
    ("雨滴", "Raindrop", "Frédéric Chopin"),
]


def color(value):
    return lv.color_hex(value)


def panel(parent, x, y, width, height, bg, radius=0):
    obj = lv.obj(parent)
    obj.set_pos(x, y)
    obj.set_size(width, height)
    obj.set_style_bg_color(color(bg), 0)
    obj.set_style_bg_opa(lv.OPA.COVER, 0)
    obj.set_style_radius(radius, 0)
    obj.set_style_border_width(0, 0)
    obj.set_style_pad_all(0, 0)
    obj.set_style_shadow_width(0, 0)
    obj.set_scroll_dir(lv.DIR.NONE)
    obj.set_scrollbar_mode(lv.SCROLLBAR_MODE.OFF)
    return obj


def label(parent, text, x, y, font=None, text_color=TEXT):
    item = lv.label(parent)
    item.set_text(text)
    item.set_pos(x, y)
    item.set_style_text_color(color(text_color), 0)
    item.set_style_text_font(font or lv.font_montserrat_14, 0)
    return item


def circle_button(parent, symbol, x, y, size, callback, bg=PURPLE):
    item = lv.button(parent)
    item.set_pos(x, y)
    item.set_size(size, size)
    item.set_style_bg_color(color(bg), 0)
    item.set_style_bg_opa(lv.OPA.COVER, 0)
    item.set_style_radius(size // 2, 0)
    item.set_style_shadow_width(0, 0)
    icon = lv.label(item)
    icon.set_text(symbol)
    icon.center()
    icon.set_style_text_color(color(0xFFFFFF), 0)
    icon.set_style_text_font(lv.font_montserrat_20, 0)
    item.add_event_cb(callback, lv.EVENT.CLICKED, None)
    KEEP.append(callback)
    return item


def tr(zh_text, en_text):
    return zh_text if zh else en_text


def save_debug(driver, name="music_player.png"):
    if not DEBUG_IMAGES or not RUN_DIR:
        return
    art = os.path.join(RUN_DIR, "artifacts")
    os.makedirs(art, exist_ok=True)
    path = os.path.join(art, name)
    if save_screenshot(driver, path):
        print(f"MAIXPY_SKILL_IMAGE {path}", flush=True)


def main():
    global zh, ui_font, ui_font_small
    disp = ts = None
    driver = None
    font = None
    font_small = None
    try:
        driver, disp, ts = init_lvgl()
        scr = lv.screen_active()
        scr.set_style_bg_color(color(BG_TOP), 0)
        scr.set_style_bg_grad_color(color(BG_BOTTOM), 0)
        scr.set_style_bg_grad_dir(lv.GRAD_DIR.VER, 0)
        scr.set_style_bg_opa(lv.OPA.COVER, 0)

        if HAS_MAIX:
            font = lv.freetype_font_create(FONT_PATH, 0, 20, 0)
            font_small = lv.freetype_font_create(FONT_PATH, 0, 12, 0)
            zh = font is not None
            ui_font = font
            ui_font_small = font_small or font or lv.font_montserrat_12

        header = panel(scr, 0, 0, 640, 48, 0x0E0818)
        label(header, tr("音乐播放器", "LVGL Music"), 18, 10,
              ui_font or lv.font_montserrat_20, TEXT)
        label(header, "LVGL 9.1", 150, 16, lv.font_montserrat_12, MUTED)

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

        cover = panel(scr, 30, 72, 260, 260, 0x3B1D6E, radius=130)
        cover.set_style_bg_grad_color(color(0x0E7490), 0)
        cover.set_style_bg_grad_dir(lv.GRAD_DIR.VER, 0)
        cover.set_style_shadow_width(16, 0)
        cover.set_style_shadow_color(color(PURPLE), 0)
        cover.set_style_shadow_opa(lv.OPA._60, 0)
        cover.set_style_transform_pivot_x(130, 0)
        cover.set_style_transform_pivot_y(130, 0)
        label(cover, lv.SYMBOL.AUDIO, 112, 100, lv.font_montserrat_32, TEXT)

        label(scr, tr("正在播放", "Now playing"), 320, 78,
              ui_font_small or lv.font_montserrat_12, MUTED)
        song_label = label(scr, SONGS[0][0], 320, 104,
                           ui_font or lv.font_montserrat_20, TEXT)
        artist_label = label(scr, SONGS[0][2], 320, 140,
                             lv.font_montserrat_14, MUTED)
        song_index = [0]

        progress = [0.0]
        slider = lv.slider(scr)
        slider.set_pos(320, 192)
        slider.set_size(280, 8)
        slider.set_range(0, 100)
        slider.set_value(0, 0)
        slider.set_style_bg_color(color(DARK), 0)
        slider.set_style_bg_opa(lv.OPA.COVER, 0)
        slider.set_style_bg_color(color(PURPLE), lv.PART.INDICATOR)
        slider.set_style_radius(4, 0)

        current_time = label(scr, "0:00", 320, 208, lv.font_montserrat_12, MUTED)
        label(scr, "5:12", 566, 208, lv.font_montserrat_12, MUTED)

        def on_seek(event):
            progress[0] = float(slider.get_value())

        slider.add_event_cb(on_seek, lv.EVENT.VALUE_CHANGED, None)
        KEEP.append(on_seek)

        state = {"playing": True}
        play_icon = None

        def toggle_play(event):
            state["playing"] = not state["playing"]
            if play_icon is not None:
                play_icon.set_text(lv.SYMBOL.PAUSE if state["playing"] else lv.SYMBOL.PLAY)

        def previous(event):
            song_index[0] = (song_index[0] - 1) % len(SONGS)
            song_label.set_text(SONGS[song_index[0]][0])
            artist_label.set_text(SONGS[song_index[0]][2])
            progress[0] = 0.0

        def next_song(event):
            song_index[0] = (song_index[0] + 1) % len(SONGS)
            song_label.set_text(SONGS[song_index[0]][0])
            artist_label.set_text(SONGS[song_index[0]][2])
            progress[0] = 0.0

        circle_button(scr, lv.SYMBOL.PREV, 320, 250, 56, previous, 0x2A2140)
        play_button = circle_button(scr, lv.SYMBOL.PAUSE, 390, 242, 72,
                                    toggle_play, PURPLE)
        play_icon = play_button.get_child(0)
        circle_button(scr, lv.SYMBOL.NEXT, 476, 250, 56, next_song, 0x2A2140)

        label(scr, lv.SYMBOL.VOLUME_MAX, 320, 338, lv.font_montserrat_16, MUTED)
        volume = lv.slider(scr)
        volume.set_pos(348, 344)
        volume.set_size(180, 8)
        volume.set_range(0, 100)
        volume.set_value(35, 0)
        volume.set_style_bg_color(color(DARK), 0)
        volume.set_style_bg_opa(lv.OPA.COVER, 0)
        volume.set_style_bg_color(color(CYAN), lv.PART.INDICATOR)
        volume.set_style_radius(4, 0)

        bars = []
        for index in range(24):
            x = 30 + index * 24
            panel(scr, x, 390, 14, 60, 0x1A1428, radius=7)
            bar = panel(scr, x, 410, 14, 40, 0xFFFFFF, radius=7)
            hue = int(index * 360 / 24)
            bar.set_style_bg_color(lv.color_hsv_to_rgb(hue, 80, 100), 0)
            bars.append(bar)

        label(scr, "LVGL 9.1  |  maix_lvgl  |  640x480", 30, 458,
              lv.font_montserrat_12, MUTED)

        start = time.monotonic()
        last_update = start
        last_shot = start
        phase = 0.0
        angle = 0
        while not need_exit() and running[0]:
            lv.timer_handler()
            now = time.monotonic()

            if state["playing"]:
                angle = (angle + 2) % 3600
                cover.set_style_transform_rotation(angle, 0)
                progress[0] = (progress[0] + 0.15) % 100.0
                slider.set_value(int(progress[0]), 0)
                total = 312
                seconds = int(progress[0] / 100.0 * total)
                current_time.set_text(f"{seconds // 60}:{seconds % 60:02d}")

            if now - last_update >= 0.08:
                last_update = now
                phase += 0.25
                for index, bar in enumerate(bars):
                    value = int(12 + 48 * abs(math.sin(phase + index * 0.35)))
                    bar.set_height(value)
                    bar.set_y(450 - value)

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
        deinit_lvgl(driver, disp, ts)


if __name__ == "__main__":
    main()
