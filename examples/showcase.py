"""LVGL 9.1 feature showcase for MaixCAM2.

Run on the device (launcher stopped / development mode):

    python showcase.py

Pages:
  Controls    buttons, switch, checkbox, slider, bar, arc, dropdown,
              roller, spinbox, LED
  Data        live chart, table, calendar
  Input       textarea + on-screen keyboard, list, message box
  Canvas      canvas drawing, animation, spinner

Exit with the on-screen "Exit" button (top-right) or the system app exit.
Debug capture is disabled unless MAIXPY_DEBUG_IMAGES=1.
"""
import math
import os
import time

from maix import app, display, image, touchscreen

import maix_lvgl as lv

# ---------------------------------------------------------------- constants
BG = 0x12121A
CARD = 0x222233
CARD_BORDER = 0x35354D
TEXT = 0xF5F5FA
MUTED = 0x9CA3AF
ACCENT = 0x3B82F6
GREEN = 0x22C55E
AMBER = 0xF59E0B
RED = 0xEF4444

DEBUG_IMAGES = os.environ.get("MAIXPY_DEBUG_IMAGES") == "1"
RUN_DIR = os.environ.get("MAIXPY_SKILL_RUN_DIR")
AUTO_EXIT_SECONDS = 12.0 if (DEBUG_IMAGES and RUN_DIR) else 0.0

KEEP = []
running = [True]
clicks = [0]
slider_value = [50]


def color(value):
    return lv.color_hex(value)


def style_panel(obj, bg, radius=0, border=0, border_color=None, pad=0):
    obj.set_style_bg_color(color(bg), 0)
    obj.set_style_bg_opa(lv.OPA.COVER, 0)
    obj.set_style_radius(radius, 0)
    obj.set_style_border_width(border, 0)
    if border_color is not None:
        obj.set_style_border_color(color(border_color), 0)
    obj.set_style_pad_all(pad, 0)
    obj.set_style_shadow_width(0, 0)


def make_label(parent, text, x, y, font=None, text_color=TEXT):
    label = lv.label(parent)
    label.set_text(text)
    label.set_pos(x, y)
    label.set_style_text_color(color(text_color), 0)
    if font is not None:
        label.set_style_text_font(font, 0)
    return label


def make_button(parent, text, x, y, width, height, callback, bg=ACCENT):
    button = lv.button(parent)
    button.set_pos(x, y)
    button.set_size(width, height)
    style_panel(button, bg, radius=8, pad=0)
    label = lv.label(button)
    label.set_text(text)
    label.center()
    label.set_style_text_color(color(0xFFFFFF), 0)
    button.add_event_cb(callback, lv.EVENT.CLICKED, None)
    KEEP.append(callback)
    return button


def make_card(parent, x, y, width, height, title):
    card = lv.obj(parent)
    card.set_pos(x, y)
    card.set_size(width, height)
    style_panel(card, CARD, radius=12, border=1, border_color=CARD_BORDER, pad=12)
    make_label(card, title, 0, 0, lv.font_montserrat_16, MUTED)
    return card


def save_debug_image(driver, name="showcase.png"):
    if not DEBUG_IMAGES or not RUN_DIR:
        return
    art = os.path.join(RUN_DIR, "artifacts")
    os.makedirs(art, exist_ok=True)
    path = os.path.join(art, name)
    img = image.from_bytes(
        driver.width,
        driver.height,
        image.Format.FMT_BGRA8888,
        bytes(driver._buffer),
        True,
    )
    img.save(path)
    print(f"MAIXPY_SKILL_IMAGE {path}", flush=True)


# ------------------------------------------------------------------ pages
def build_controls_page(page):
    left = make_card(page, 0, 0, 300, 330, "Controls")

    def on_click(event):
        clicks[0] += 1
        count_label.set_text(f"Clicked {clicks[0]} times")

    make_button(left, "Click me", 0, 30, 140, 40, on_click)
    count_label = make_label(left, "Clicked 0 times", 150, 40, lv.font_montserrat_14, MUTED)

    make_label(left, "Switch", 0, 88, lv.font_montserrat_14)
    switch = lv.switch(left)
    switch.set_pos(90, 82)
    switch_label = make_label(left, "OFF", 170, 88, lv.font_montserrat_14, MUTED)

    def on_switch(event):
        switch_label.set_text(
            "ON" if switch.has_state(lv.STATE.CHECKED) else "OFF"
        )

    switch.add_event_cb(on_switch, lv.EVENT.VALUE_CHANGED, None)
    KEEP.append(on_switch)

    checkbox = lv.checkbox(left)
    checkbox.set_pos(0, 122)
    checkbox.set_text("Enable feature")
    checkbox.add_state(lv.STATE.CHECKED)

    make_label(left, "Slider", 0, 165, lv.font_montserrat_14)
    slider = lv.slider(left)
    slider.set_pos(0, 190)
    slider.set_size(250, 16)
    slider.set_range(0, 100)
    slider.set_value(slider_value[0], 0)
    slider_label = make_label(left, f"Value: {slider_value[0]}", 0, 212, lv.font_montserrat_14, MUTED)

    def on_slider(event):
        slider_value[0] = slider.get_value()
        slider_label.set_text(f"Value: {slider_value[0]}")

    slider.add_event_cb(on_slider, lv.EVENT.VALUE_CHANGED, None)
    KEEP.append(on_slider)

    make_label(left, "Progress", 0, 248, lv.font_montserrat_14)
    bar = lv.bar(left)
    bar.set_pos(0, 272)
    bar.set_size(250, 16)
    bar.set_range(0, 100)
    bar.set_value(35, 0)

    right = make_card(page, 312, 0, 300, 330, "More widgets")

    make_label(right, "Dropdown", 0, 30, lv.font_montserrat_14)
    dropdown_options = ["Option A", "Option B", "Option C"]
    dropdown = lv.dropdown(right)
    dropdown.set_pos(0, 54)
    dropdown.set_size(250, 40)
    dropdown.set_options("\n".join(dropdown_options))
    dropdown.set_selected(0)
    dropdown_label = make_label(right, dropdown_options[0], 0, 98, lv.font_montserrat_14, MUTED)

    def on_dropdown(event):
        index = dropdown.get_selected()
        if 0 <= index < len(dropdown_options):
            dropdown_label.set_text(dropdown_options[index])

    dropdown.add_event_cb(on_dropdown, lv.EVENT.VALUE_CHANGED, None)
    KEEP.append(on_dropdown)

    make_label(right, "Roller", 0, 126, lv.font_montserrat_14)
    roller_options = ["Red", "Green", "Blue"]
    roller = lv.roller(right)
    roller.set_pos(0, 148)
    roller.set_size(120, 84)
    roller.set_options("\n".join(roller_options), lv.roller.MODE.NORMAL)
    roller.set_selected(0, 0)
    roller.set_visible_row_count(2)
    roller.set_style_bg_color(color(0xE5E7EB), 0)
    roller.set_style_bg_opa(lv.OPA.COVER, 0)
    roller.set_style_text_color(color(0x111111), 0)

    make_label(right, "Spinbox", 140, 126, lv.font_montserrat_14)
    spinbox = lv.spinbox(right)
    spinbox.set_pos(140, 148)
    spinbox.set_size(120, 40)
    spinbox.set_range(0, 999)
    spinbox.set_value(100)
    spinbox.set_digit_format(3, 0)
    spinbox.set_style_bg_opa(lv.OPA.TRANSP, lv.PART.CURSOR)
    spinbox.set_style_border_width(0, lv.PART.CURSOR)

    def on_spin_up(event):
        spinbox.increment()

    def on_spin_down(event):
        spinbox.decrement()

    make_button(right, "+", 140, 194, 50, 32, on_spin_up, GREEN)
    make_button(right, "-", 200, 194, 50, 32, on_spin_down, RED)

    make_label(right, "LED", 0, 250, lv.font_montserrat_14)
    led = lv.led(right)
    led.set_pos(50, 244)
    led.set_size(24, 24)
    led.set_color(color(AMBER))
    led.on()

    def on_led(event):
        led.toggle()

    make_button(right, "Toggle", 84, 240, 80, 32, on_led, AMBER)

    arc = lv.arc(right)
    arc.set_pos(192, 228)
    arc.set_size(76, 76)
    arc.set_range(0, 100)
    arc.set_value(30)

    def on_arc(event):
        arc.set_value((arc.get_value() + 10) % 110)

    arc.add_event_cb(on_arc, lv.EVENT.CLICKED, None)
    KEEP.append(on_arc)

    return {
        "slider": slider,
        "bar": bar,
        "switch": switch,
    }


def build_data_page(page, width, height):
    chart = lv.chart(page)
    chart.set_pos(0, 0)
    chart.set_size(360, 200)
    chart.set_type(lv.chart.TYPE.LINE)
    chart.set_point_count(40)
    chart.set_range(lv.chart.AXIS.PRIMARY_Y, -100, 100)
    chart.set_div_line_count(4, 6)
    chart.set_update_mode(lv.chart.UPDATE_MODE.SHIFT)
    series_a = chart.add_series(color(ACCENT), lv.chart.AXIS.PRIMARY_Y)
    series_b = chart.add_series(color(GREEN), lv.chart.AXIS.PRIMARY_Y)
    make_label(page, "Live sin / cos", 250, 8, lv.font_montserrat_14, MUTED)

    table = lv.table(page)
    table.set_pos(0, 210)
    table.set_size(360, 140)
    table.set_column_count(2)
    table.set_row_count(3)
    table.set_column_width(0, 120)
    table.set_column_width(1, 180)
    table.set_style_pad_top(0, lv.PART.ITEMS)
    table.set_style_pad_bottom(0, lv.PART.ITEMS)
    table.set_style_text_font(lv.font_montserrat_12, lv.PART.ITEMS)
    table.set_scrollbar_mode(lv.SCROLLBAR_MODE.OFF)
    rows = [
        ("LVGL", "9.1.0"),
        ("Display", f"{width}x{height}"),
        ("Uptime", "0s"),
    ]
    for row, (name, value) in enumerate(rows):
        table.set_cell_value(row, 0, name)
        table.set_cell_value(row, 1, value)

    calendar = lv.calendar(page)
    calendar.set_pos(372, 130)
    calendar.set_size(240, 210)
    now = time.localtime()
    calendar.set_today_date(now.tm_year, now.tm_mon, now.tm_mday)
    calendar.set_showed_date(now.tm_year, now.tm_mon)

    return {
        "chart": chart,
        "series_a": series_a,
        "series_b": series_b,
        "table": table,
    }


def build_input_page(page):
    list_widget = lv.list(page)
    list_widget.set_pos(0, 0)
    list_widget.set_size(280, 150)
    style_panel(list_widget, CARD, radius=10, border=1, border_color=CARD_BORDER, pad=8)
    for text in (
        "Welcome to LVGL",
        "Switch tabs to explore",
        "Type and press Send",
    ):
        item = list_widget.add_text(text)
        item.set_style_text_color(color(TEXT), 0)
        item.set_style_text_font(lv.font_montserrat_14, 0)

    textarea = lv.textarea(page)
    textarea.set_pos(292, 0)
    textarea.set_size(320, 100)
    textarea.set_one_line(0)
    textarea.set_max_length(200)
    textarea.set_placeholder_text("Type here...")
    style_panel(textarea, CARD, radius=10, border=1, border_color=CARD_BORDER, pad=8)
    textarea.set_style_text_color(color(TEXT), 0)

    def on_send(event):
        text = textarea.get_text()
        if text:
            item = list_widget.add_text(text)
            item.set_style_text_color(color(TEXT), 0)
            item.set_style_text_font(lv.font_montserrat_14, 0)
            textarea.set_text("")

    def on_clear(event):
        textarea.set_text("")

    def on_about(event):
        box = lv.msgbox(lv.screen_active())
        box.add_title("About")
        box.add_text("LVGL 9.1.0 on MaixCAM2\nmaix_lvgl showcase")
        close_btn = box.add_footer_button("OK")

        def close_box(e):
            box.close()

        close_btn.add_event_cb(close_box, lv.EVENT.CLICKED, None)
        KEEP.append(close_box)

    make_button(page, "Send", 292, 110, 100, 36, on_send, GREEN)
    make_button(page, "Clear", 402, 110, 100, 36, on_clear, ACCENT)
    make_button(page, "About", 512, 110, 100, 36, on_about, AMBER)

    keyboard = lv.keyboard(page)
    keyboard.set_size(620, 180)
    # lv_keyboard aligns itself to the parent bottom by default; pin it
    # explicitly so it stays inside the tab content instead of the screen.
    keyboard.align(lv.ALIGN.BOTTOM_MID, 0, -6)
    keyboard.set_textarea(textarea)
    keyboard.set_mode(lv.keyboard.MODE.TEXT_LOWER)

    return {
        "textarea": textarea,
        "keyboard": keyboard,
    }


def draw_canvas(canvas):
    width, height = 320, 180
    buffer = bytearray(width * height * 4)
    KEEP.append(buffer)
    canvas.set_size(width, height)
    canvas.set_buffer(buffer, width, height, lv.COLOR_FORMAT.ARGB8888)
    canvas.fill_bg(color(0x0E0E16), lv.OPA.COVER)
    grid = color(0x1F2937)
    for x in range(0, width, 40):
        for y in range(height):
            canvas.set_px(x, y, grid, lv.OPA.COVER)
    for y in range(0, height, 30):
        for x in range(width):
            canvas.set_px(x, y, grid, lv.OPA.COVER)
    wave_a = color(ACCENT)
    wave_b = color(GREEN)
    for x in range(width):
        y_a = int(height // 2 + 55 * math.sin(x / 24.0))
        y_b = int(height // 2 + 55 * math.cos(x / 24.0))
        if 0 <= y_a < height:
            canvas.set_px(x, y_a, wave_a, lv.OPA.COVER)
        if 0 <= y_b < height:
            canvas.set_px(x, y_b, wave_b, lv.OPA.COVER)


def build_canvas_page(page):
    canvas = lv.canvas(page)
    canvas.set_pos(0, 0)
    draw_canvas(canvas)
    make_label(page, "Canvas: sin / cos pixels", 0, 186, lv.font_montserrat_14, MUTED)

    box = lv.obj(page)
    box.set_pos(340, 10)
    box.set_size(80, 80)
    style_panel(box, AMBER, radius=16, border=0, pad=0)
    box.set_style_shadow_width(16, 0)
    box.set_style_shadow_color(color(AMBER), 0)
    box.set_style_shadow_opa(lv.OPA._50, 0)

    def animate_box(anim, value):
        box.set_x(value)

    KEEP.append(animate_box)
    anim = lv.anim_t()
    anim.init()
    anim.set_values(340, 500)
    anim.set_time(1400)
    anim.set_playback_time(1400)
    anim.set_repeat_count(0xFFFF)
    anim.set_custom_exec_cb(animate_box)
    anim.start()
    KEEP.append(anim)

    anim_label = make_label(page, "anim x = 340", 340, 100, lv.font_montserrat_14, MUTED)

    spinner = lv.spinner(page)
    spinner.set_pos(340, 140)
    spinner.set_size(60, 60)
    spinner.set_anim_params(1000, 60)
    make_label(page, "Spinner", 410, 158, lv.font_montserrat_14, MUTED)

    info = make_label(
        page,
        "Custom styles, shadows, animation\nand direct canvas pixels.",
        340, 210, lv.font_montserrat_14, MUTED,
    )

    return {
        "anim_label": anim_label,
        "box": box,
    }


# ------------------------------------------------------------------- main
def main():
    disp = display.Display()
    ts = touchscreen.TouchScreen()
    driver = None
    try:
        driver = lv.init(disp, ts)
        screen = lv.screen_active()
        width, height = driver.width, driver.height
        style_panel(screen, BG, pad=0)

        header = lv.obj(screen)
        header.set_pos(0, 0)
        header.set_size(width, 44)
        style_panel(header, 0x1A1A24, radius=0, pad=0)
        header.set_style_border_width(1, 0)
        header.set_style_border_side(lv.BORDER_SIDE.BOTTOM, 0)
        header.set_style_border_color(color(0x2A2A3A), 0)
        make_label(header, "LVGL 9.1 - MaixCAM2 Showcase", 14, 10,
                   lv.font_montserrat_20, TEXT)

        def on_exit(event):
            running[0] = False

        make_button(header, "Exit", width - 90, 6, 78, 32, on_exit, RED)

        tabview = lv.tabview(screen)
        tabview.set_pos(8, 48)
        tabview.set_size(width - 16, height - 84)
        tabview.set_tab_bar_size(42)
        controls_page = tabview.add_tab("Controls")
        data_page = tabview.add_tab("Data")
        input_page = tabview.add_tab("Input")
        canvas_page = tabview.add_tab("Canvas")
        for page in (controls_page, data_page, input_page, canvas_page):
            page.set_style_pad_all(0, 0)
            # Absolute positioning must not be overridden by a tab-content
            # layout; the keyboard in particular was pushed off-screen.
            page.set_layout(lv.LAYOUT.NONE)
            page.set_scroll_dir(lv.DIR.NONE)
            page.set_scrollbar_mode(lv.SCROLLBAR_MODE.OFF)

        controls = build_controls_page(controls_page)
        data = build_data_page(data_page, width, height)
        text_input = build_input_page(input_page)
        canvas_info = build_canvas_page(canvas_page)

        status = lv.obj(screen)
        status.set_pos(0, height - 28)
        status.set_size(width, 28)
        style_panel(status, 0x0D0D14, radius=0, pad=0)
        clock_label = make_label(status, "--:--:--", 12, 5,
                                 lv.font_montserrat_12, MUTED)
        info_label = make_label(status, "booting...", 140, 5,
                                lv.font_montserrat_12, MUTED)

        tab_names = ["Controls", "Data", "Input", "Canvas"]

        def on_tab(event):
            index = tabview.get_tab_active()
            if 0 <= index < len(tab_names):
                info_label.set_text(f"Tab: {tab_names[index]}")

        tabview.add_event_cb(on_tab, lv.EVENT.VALUE_CHANGED, None)
        KEEP.append(on_tab)

        start = time.monotonic()
        last_chart = start
        last_status = start
        last_shot = start
        last_tab_switch = start
        frames = 0
        fps = 0.0
        chart_phase = 0.0

        while not app.need_exit() and running[0]:
            lv.timer_handler()
            frames += 1
            now = time.monotonic()

            if now - last_chart >= 0.1:
                last_chart = now
                chart_phase += 0.2
                data["chart"].set_next_value(
                    data["series_a"], int(85 * math.sin(chart_phase))
                )
                data["chart"].set_next_value(
                    data["series_b"], int(85 * math.cos(chart_phase))
                )

            if now - last_status >= 0.25:
                elapsed = now - last_status
                fps = frames / max(elapsed, 1e-6)
                frames = 0
                last_status = now
                uptime = now - start
                clock_label.set_text(time.strftime("%H:%M:%S"))
                info_label.set_text(
                    f"Tab: {tab_names[tabview.get_tab_active()]}   "
                    f"Clicks: {clicks[0]}   Slider: {slider_value[0]}   "
                    f"FPS: {fps:.0f}"
                )
                data["table"].set_cell_value(2, 1, f"{uptime:.0f}s")
                canvas_info["anim_label"].set_text(
                    f"anim x = {canvas_info['box'].get_x()}"
                )
                bar_value = int((uptime * 20) % 101)
                controls["bar"].set_value(bar_value, 0)

            if DEBUG_IMAGES and AUTO_EXIT_SECONDS and now - last_tab_switch >= 3.0:
                last_tab_switch = now
                tabview.set_active((tabview.get_tab_active() + 1) % 4, 0)

            if DEBUG_IMAGES and RUN_DIR and now - last_shot >= 2.0:
                last_shot = now
                save_debug_image(
                    driver, f"showcase_{tabview.get_tab_active()}.png"
                )

            if AUTO_EXIT_SECONDS and now - start >= AUTO_EXIT_SECONDS:
                running[0] = False

            time.sleep(0.005)

        save_debug_image(driver)
    finally:
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
