"""LVGL widget API test suite for maix_lvgl on MaixCAM2.

Creates every widget class, exercises its common setters/getters, renders
one frame and deletes it. Failures are reported per widget so binding gaps
can be told apart from test mistakes.
"""
import os
import time
import traceback

import maix_lvgl as lv
from maix import display, image, touchscreen

RESULTS = []
KEEP = []

SYM_OK = "\xef\x80\x81"   # LV_SYMBOL_OK
SYM_CLOSE = "\xef\x80\x8d"  # LV_SYMBOL_CLOSE


def check(name, fn):
    t0 = time.monotonic()
    try:
        fn()
        ok, err = True, ""
    except Exception as e:
        ok, err = False, f"{type(e).__name__}: {e}"
        traceback.print_exc()
    dt = (time.monotonic() - t0) * 1000.0
    RESULTS.append((name, ok, err))
    print(f"[{'PASS' if ok else 'FAIL'}] {name} ({dt:.1f} ms)" +
          ("" if ok else f"  :: {err}"), flush=True)


def eq(got, exp, label="value"):
    if got != exp:
        raise AssertionError(f"{label}: got {got!r}, expected {exp!r}")


def pump(ms):
    end = time.monotonic() + ms / 1000.0
    while time.monotonic() < end:
        lv.timer_handler()
        time.sleep(0.002)


def area(x1, y1, x2, y2):
    a = lv.area_t()
    a.set(x1, y1, x2, y2)
    return a


def t_arc():
    a = lv.arc(scr)
    a.set_size(120, 120)
    a.set_range(0, 100)
    a.set_value(40)
    eq(a.get_value(), 40)
    eq(a.get_min_value(), 0)
    eq(a.get_max_value(), 100)
    a.set_angles(0, 180)
    eq(a.get_angle_start(), 0)
    eq(a.get_angle_end(), 180)
    a.set_bg_angles(0, 360)
    eq(a.get_bg_angle_start(), 0)
    eq(a.get_bg_angle_end(), 360)
    a.set_rotation(10)
    eq(a.get_rotation(), 10)
    a.set_mode(lv.arc.MODE.SYMMETRICAL)
    eq(a.get_mode(), lv.arc.MODE.SYMMETRICAL)
    a.set_knob_offset(5)
    eq(a.get_knob_offset(), 5)
    a.set_change_rate(2)
    a.delete()


def t_bar():
    b = lv.bar(scr)
    b.set_size(160, 20)
    b.set_range(0, 200)
    eq(b.get_min_value(), 0)
    eq(b.get_max_value(), 200)
    b.set_mode(lv.bar.MODE.RANGE)
    b.set_value(100, 0)
    eq(b.get_value(), 100)
    b.set_start_value(20, 0)
    eq(b.get_start_value(), 20)
    eq(b.get_mode(), lv.bar.MODE.RANGE)
    b.is_symmetrical()
    b.delete()


def t_button():
    b = lv.button(scr)
    b.set_size(100, 50)
    lab = lv.label(b)
    lab.set_text("Btn")
    lab.center()
    b.delete()


def t_buttonmatrix():
    m = lv.buttonmatrix(scr)
    m.set_map(["a", "b", "\n", "c", "d"])
    eq(m.get_button_text(0), "a")
    m.clear_button_ctrl(0, lv.buttonmatrix.CTRL.DISABLED)
    m.set_button_ctrl(0, lv.buttonmatrix.CTRL.CHECKABLE)
    eq(m.has_button_ctrl(0, lv.buttonmatrix.CTRL.CHECKABLE), 1)
    m.clear_button_ctrl(0, lv.buttonmatrix.CTRL.CHECKABLE)
    m.set_button_width(0, 1)
    m.set_one_checked(1)
    eq(m.get_one_checked(), 1)
    m.set_selected_button(1)
    eq(m.get_selected_button(), 1)
    m.delete()


def t_calendar():
    c = lv.calendar(scr)
    c.set_today_date(2026, 11, 9)
    d = c.get_today_date()
    eq((d.year, d.month, d.day), (2026, 11, 9))
    c.set_showed_date(2026, 11)
    d2 = c.get_showed_date()
    eq((d2.year, d2.month), (2026, 11))
    if c.get_btnmatrix() is None:
        raise AssertionError("calendar btnmatrix")
    c.delete()


def t_canvas():
    cv = lv.canvas(scr)
    cv.set_size(100, 100)
    buf = bytearray(100 * 100 * 4)
    KEEP.append(buf)
    cv.set_buffer(buf, 100, 100, lv.COLOR_FORMAT.ARGB8888)
    cv.fill_bg(lv.color_make(0, 0, 255), lv.OPA.COVER)
    cv.set_px(10, 10, lv.color_make(255, 0, 0), lv.OPA.COVER)
    px = cv.get_px(10, 10)
    eq((px.red, px.green, px.blue), (255, 0, 0), "canvas px")
    if cv.get_buf() is None:
        raise AssertionError("canvas get_buf")
    if cv.get_draw_buf() is None:
        raise AssertionError("canvas get_draw_buf")
    if cv.get_image() is None:
        raise AssertionError("canvas get_image")
    if lv.canvas_buf_size(100, 100, 32, 400) <= 0:
        raise AssertionError("canvas buf_size")
    cv.delete()


def t_chart():
    ch = lv.chart(scr)
    ch.set_size(200, 120)
    ch.set_type(lv.chart.TYPE.LINE)
    eq(ch.get_type(), lv.chart.TYPE.LINE)
    ch.set_range(lv.chart.AXIS.PRIMARY_Y, 0, 100)
    ch.set_point_count(10)
    eq(ch.get_point_count(), 10)
    ser = ch.add_series(lv.color_make(255, 0, 0), lv.chart.AXIS.PRIMARY_Y)
    if ser is None:
        raise AssertionError("chart series")
    ch.set_next_value(ser, 50)
    ch.set_series_color(ser, lv.color_make(0, 255, 0))
    ch.set_div_line_count(2, 2)
    ch.set_update_mode(lv.chart.UPDATE_MODE.SHIFT)
    ch.refresh()
    ch.delete()


def t_checkbox():
    c = lv.checkbox(scr)
    c.set_text("Check")
    eq(c.get_text(), "Check")
    c.add_state(lv.STATE.CHECKED)
    eq(c.has_state(lv.STATE.CHECKED), 1)
    c.delete()


def t_dropdown():
    d = lv.dropdown(scr)
    d.set_options("A\nB\nC")
    eq(d.get_options(), "A\nB\nC")
    eq(d.get_option_count(), 3)
    d.set_selected(1)
    eq(d.get_selected(), 1)
    d.open()
    d.close()
    if d.get_list() is None:
        raise AssertionError("dropdown list")
    d.add_option("D", 3)
    eq(d.get_option_count(), 4)
    d.clear_options()
    eq(d.get_option_count(), 0)
    d.delete()


def t_image():
    im = lv.image(scr)
    im.set_size(64, 64)
    KEEP.append(SYM_OK)
    im.set_src(SYM_OK)
    if im.get_src() is None:
        raise AssertionError("image src")
    im.set_rotation(90)
    im.set_scale(256)
    im.set_offset_x(1)
    im.set_offset_y(1)
    im.set_inner_align(lv.image.ALIGN.CENTER)
    im.set_antialias(1)
    im.set_blend_mode(lv.BLEND_MODE.NORMAL)
    im.delete()


def t_imagebutton():
    ib = lv.imagebutton(scr)
    KEEP.append(SYM_OK)
    ib.set_src(lv.imagebutton.STATE.RELEASED, SYM_OK, SYM_OK, SYM_OK)
    ib.set_state(lv.imagebutton.STATE.PRESSED)
    if ib.get_src_left(lv.imagebutton.STATE.RELEASED) is None:
        raise AssertionError("imagebutton src")
    ib.delete()


def t_keyboard():
    kb = lv.keyboard(scr)
    kb.set_mode(lv.keyboard.MODE.NUMBER)
    eq(kb.get_mode(), lv.keyboard.MODE.NUMBER)
    ta = lv.textarea(scr)
    kb.set_textarea(ta)
    kb.get_button_text(0)
    kb.delete()
    ta.delete()


def t_label():
    lb = lv.label(scr)
    lb.set_text("Hello")
    eq(lb.get_text(), "Hello")
    lb.set_long_mode(lv.label.LONG.WRAP)
    eq(lb.get_long_mode(), lv.label.LONG.WRAP)
    lb.ins_text(0, "X")
    lb.cut_text(0, 1)
    eq(lb.get_text(), "Hello")
    lb.set_text_selection_start(1)
    lb.set_text_selection_end(2)
    eq(lb.get_text_selection_start(), 1)
    eq(lb.get_text_selection_end(), 2)
    lb.delete()


def t_led():
    led = lv.led(scr)
    led.set_color(lv.color_make(255, 0, 0))
    led.on()
    if led.get_brightness() <= 0:
        raise AssertionError("led on brightness")
    led.off()
    # LV_LED_BRIGHT_MIN is 80, not 0 (LVGL clamps brightness).
    eq(led.get_brightness(), 80)
    led.set_brightness(128)
    eq(led.get_brightness(), 128)
    led.toggle()
    led.delete()


def t_line():
    ln = lv.line(scr)
    ln.set_y_invert(1)
    eq(ln.get_y_invert(), 1)
    ln.delete()


def t_list():
    lst = lv.list(scr)
    lst.set_size(160, 160)
    txt = lst.add_text("Item")
    if txt is None:
        raise AssertionError("list text")
    KEEP.append(SYM_OK)
    btn = lst.add_button(SYM_OK, "Btn")
    eq(lst.get_button_text(btn), "Btn")
    lst.set_button_text(btn, "B2")
    eq(lst.get_button_text(btn), "B2")
    lst.delete()


def t_menu():
    m = lv.menu(scr)
    page = lv.menu_page(m, "Page")
    m.set_page(page)
    if m.get_cur_main_page() is None:
        raise AssertionError("menu current page")
    page.set_page_title("Title")
    page.set_page_title_static("Title")
    m.get_main_header()
    if m.get_main_header() is None:
        raise AssertionError("menu main header")
    sec = lv.menu_section(page)
    sep = lv.menu_separator(page)
    cont = lv.menu_cont(page)
    m.set_mode_header(lv.menu.HEADER.TOP_FIXED)
    m.set_mode_root_back_button(lv.menu.ROOT_BACK_BUTTON.ENABLED)
    m.delete()


def t_msgbox():
    mb = lv.msgbox(scr)
    title = mb.add_title("Title")
    if title is None:
        raise AssertionError("msgbox title")
    txt = mb.add_text("Text")
    if txt is None:
        raise AssertionError("msgbox text")
    btn = mb.add_footer_button("OK")
    if btn is None:
        raise AssertionError("msgbox footer button")
    KEEP.append(SYM_CLOSE)
    mb.add_header_button(SYM_CLOSE)
    mb.add_close_button()
    if mb.get_content() is None:
        raise AssertionError("msgbox content")
    mb.close()


def t_roller():
    r = lv.roller(scr)
    r.set_options("A\nB\nC", lv.roller.MODE.NORMAL)
    eq(r.get_options(), "A\nB\nC")
    eq(r.get_option_count(), 3)
    r.set_selected(1, 0)
    eq(r.get_selected(), 1)
    r.set_visible_row_count(2)
    r.delete()


def t_scale():
    s = lv.scale(scr)
    s.set_size(150, 150)
    s.set_range(0, 100)
    eq(s.get_range_min_value(), 0)
    eq(s.get_range_max_value(), 100)
    s.set_total_tick_count(11)
    eq(s.get_total_tick_count(), 11)
    s.set_major_tick_every(2)
    eq(s.get_major_tick_every(), 2)
    s.set_label_show(1)
    eq(s.get_label_show(), 1)
    s.set_angle_range(270)
    eq(s.get_angle_range(), 270)
    s.set_rotation(45)
    s.set_mode(0)
    s.set_post_draw(1)
    s.set_text_src(["a", "b"])
    sec = s.add_section()
    if sec is None:
        raise AssertionError("scale add_section")
    s.delete()


def t_scale_section():
    s = lv.scale(scr)
    s.set_range(0, 100)
    sec = s.add_section()
    sec.set_range(10, 20)
    s.delete()


def t_slider():
    sl = lv.slider(scr)
    sl.set_size(160, 20)
    sl.set_range(0, 100)
    eq(sl.get_min_value(), 0)
    eq(sl.get_max_value(), 100)
    sl.set_value(50, 0)
    eq(sl.get_value(), 50)
    sl.set_mode(lv.slider.MODE.RANGE)
    sl.set_left_value(20, 0)
    eq(sl.get_left_value(), 20)
    eq(sl.get_mode(), lv.slider.MODE.RANGE)
    sl.is_dragged()
    sl.is_symmetrical()
    sl.delete()


def t_spangroup():
    sg = lv.spangroup(scr)
    sg.set_size(160, 80)
    sp = sg.new_span()
    sp.set_text("Hello")
    eq(sg.get_span_count(), 1)
    sg.set_align(lv.TEXT_ALIGN.CENTER)
    eq(sg.get_align(), lv.TEXT_ALIGN.CENTER)
    sg.set_mode(lv.SPAN_MODE.FIXED)
    eq(sg.get_mode(), lv.SPAN_MODE.FIXED)
    sg.set_overflow(lv.SPAN_OVERFLOW.CLIP)
    eq(sg.get_overflow(), lv.SPAN_OVERFLOW.CLIP)
    sg.set_max_lines(2)
    eq(sg.get_max_lines(), 2)
    sg.delete_span(sp)
    eq(sg.get_span_count(), 0)
    sg.delete()


def t_spinbox():
    sb = lv.spinbox(scr)
    sb.set_range(0, 1000)
    sb.set_value(500)
    eq(sb.get_value(), 500)
    sb.set_step(10)
    eq(sb.get_step(), 10)
    # step_next()/step_prev() change the step size, not the value.
    sb.step_next()
    eq(sb.get_step(), 1)
    sb.step_prev()
    eq(sb.get_step(), 10)
    sb.increment()
    eq(sb.get_value(), 510)
    sb.decrement()
    eq(sb.get_value(), 500)
    sb.set_digit_format(4, 2)
    sb.set_rollover(1)
    eq(sb.get_rollover(), 1)
    sb.delete()


def t_spinner():
    sp = lv.spinner(scr)
    sp.set_size(60, 60)
    sp.set_anim_params(1000, 60)
    pump(100)
    sp.delete()


def t_switch():
    sw = lv.switch(scr)
    sw.get_state()
    sw.delete()


def t_table():
    tb = lv.table(scr)
    tb.set_row_count(3)
    tb.set_column_count(2)
    eq(tb.get_row_count(), 3)
    eq(tb.get_column_count(), 2)
    tb.set_cell_value(0, 0, "A")
    eq(tb.get_cell_value(0, 0), "A")
    tb.set_column_width(0, 80)
    eq(tb.get_column_width(0), 80)
    tb.add_cell_ctrl(0, 0, lv.table.CELL_CTRL.TEXT_CROP)
    eq(tb.has_cell_ctrl(0, 0, lv.table.CELL_CTRL.TEXT_CROP), 1)
    tb.clear_cell_ctrl(0, 0, lv.table.CELL_CTRL.TEXT_CROP)
    eq(tb.has_cell_ctrl(0, 0, lv.table.CELL_CTRL.TEXT_CROP), 0)
    tb.delete()


def t_tabview():
    tv = lv.tabview(scr)
    tv.set_size(240, 180)
    tv.add_tab("A")
    tv.add_tab("B")
    eq(tv.get_tab_count(), 2)
    eq(tv.get_tab_active(), 0)
    tv.set_active(1, 0)
    eq(tv.get_tab_active(), 1)
    tv.rename_tab(1, "C")
    if tv.get_content() is None:
        raise AssertionError("tabview content")
    if tv.get_tab_bar() is None:
        raise AssertionError("tabview bar")
    tv.set_tab_bar_position(lv.DIR.TOP)
    tv.set_tab_bar_size(40)
    tv.delete()


def t_textarea():
    ta = lv.textarea(scr)
    ta.set_text("Hello")
    eq(ta.get_text(), "Hello")
    ta.set_placeholder_text("ph")
    eq(ta.get_placeholder_text(), "ph")
    ta.set_one_line(1)
    eq(ta.get_one_line(), 1)
    ta.set_max_length(10)
    eq(ta.get_max_length(), 10)
    ta.add_char(ord("X"))
    ta.add_text("Y")
    eq(ta.get_text(), "HelloXY")
    ta.set_accepted_chars("0123456789")
    eq(ta.get_accepted_chars(), "0123456789")
    ta.set_align(lv.TEXT_ALIGN.CENTER)
    ta.set_password_mode(1)
    eq(ta.get_password_mode(), 1)
    ta.clear_selection()
    ta.delete()


def t_tileview():
    tv = lv.tileview(scr)
    tv.set_size(240, 180)
    t0 = tv.add_tile(0, 0, lv.DIR.HOR)
    t1 = tv.add_tile(1, 0, lv.DIR.HOR)
    if t0 is None or t1 is None:
        raise AssertionError("tileview tile")
    tv.set_tile_by_index(0, 0, 0)
    if tv.get_tile_active() is None:
        raise AssertionError("tileview active")
    tv.set_tile_by_index(1, 0, 0)
    tv.set_tile(t0, 0)
    tv.delete()


def t_win():
    w = lv.win(scr)
    w.set_size(240, 180)
    if w.add_title("Title") is None:
        raise AssertionError("win title")
    KEEP.append(SYM_CLOSE)
    if w.add_button(SYM_CLOSE, 40) is None:
        raise AssertionError("win button")
    if w.get_header() is None:
        raise AssertionError("win header")
    if w.get_content() is None:
        raise AssertionError("win content")
    w.delete()


def t_animimg():
    ai = lv.animimg(scr)
    ai.set_duration(100)
    eq(ai.get_duration(), 100)
    ai.set_repeat_count(2)
    eq(ai.get_repeat_count(), 2)
    ai.get_src_count()
    ai.delete()


def t_gif():
    gf = lv.gif(scr)
    gf.delete()


def t_symbols():
    if not hasattr(lv, "SYMBOL"):
        raise AssertionError("lv.SYMBOL missing (MicroPython bindings expose it)")


def t_render_widgets():
    w, h = driver.width, driver.height
    root = lv.obj(scr)
    root.set_pos(0, 0)
    root.set_size(w, h)
    root.set_style_bg_color(lv.color_make(20, 20, 20), 0)
    root.set_style_bg_opa(lv.OPA.COVER, 0)
    btn = lv.button(root)
    btn.set_pos(20, 20)
    btn.set_size(120, 50)
    lv.label(btn).set_text("Button")
    bar = lv.bar(root)
    bar.set_pos(20, 90)
    bar.set_size(200, 20)
    bar.set_value(60, 0)
    sl = lv.slider(root)
    sl.set_pos(20, 130)
    sl.set_size(200, 20)
    sl.set_value(40, 0)
    sw = lv.switch(root)
    sw.set_pos(20, 170)
    sw.add_state(lv.STATE.CHECKED)
    cb = lv.checkbox(root)
    cb.set_pos(20, 210)
    cb.set_text("Check")
    cb.add_state(lv.STATE.CHECKED)
    arc = lv.arc(root)
    arc.set_pos(20, 250)
    arc.set_size(100, 100)
    arc.set_value(70)
    pump(200)
    lv.refr_now(driver._disp)
    # Sample inside the button (80, 45), not the empty center of the screen.
    idx = (45 * w + 80) * 4
    b, g, r, a = driver._buffer[idx: idx + 4]
    if (r, g, b) == (20, 20, 20):
        raise AssertionError("render buffer unchanged at button area")
    run_dir = os.environ.get("MAIXPY_SKILL_RUN_DIR")
    if run_dir:
        art = os.path.join(run_dir, "artifacts")
        os.makedirs(art, exist_ok=True)
        img = image.from_bytes(w, h, image.Format.FMT_BGRA8888,
                               bytes(driver._buffer), True)
        out = os.path.join(art, "suite_widgets.png")
        img.save(out)
        print("    screenshot:", out, flush=True)
    root.delete()


def main():
    global scr, driver
    disp = display.Display()
    ts = touchscreen.TouchScreen()
    driver = lv.init(disp, ts)
    scr = lv.screen_active()

    tests = [
        ("arc", t_arc),
        ("bar", t_bar),
        ("button", t_button),
        ("buttonmatrix", t_buttonmatrix),
        ("calendar", t_calendar),
        ("canvas", t_canvas),
        ("chart", t_chart),
        ("checkbox", t_checkbox),
        ("dropdown", t_dropdown),
        ("image", t_image),
        ("imagebutton", t_imagebutton),
        ("keyboard", t_keyboard),
        ("label", t_label),
        ("led", t_led),
        ("line", t_line),
        ("list", t_list),
        ("menu", t_menu),
        ("msgbox", t_msgbox),
        ("roller", t_roller),
        ("scale", t_scale),
        ("scale_section", t_scale_section),
        ("slider", t_slider),
        ("spangroup", t_spangroup),
        ("spinbox", t_spinbox),
        ("spinner", t_spinner),
        ("switch", t_switch),
        ("table", t_table),
        ("tabview", t_tabview),
        ("textarea", t_textarea),
        ("tileview", t_tileview),
        ("win", t_win),
        ("animimg", t_animimg),
        ("gif", t_gif),
        ("symbols", t_symbols),
        ("render_widgets", t_render_widgets),
    ]
    for name, fn in tests:
        check(name, fn)

    lv.deinit()
    try:
        ts.close()
        disp.close()
    except Exception:
        pass

    total = len(RESULTS)
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    failed = [n for n, ok, _ in RESULTS if not ok]
    print("\nSUMMARY: %d/%d passed" % (passed, total), flush=True)
    if failed:
        print("FAILED: " + ", ".join(failed), flush=True)
    print("RESULT:", "OK" if not failed else "FAIL", flush=True)


if __name__ == "__main__":
    main()
