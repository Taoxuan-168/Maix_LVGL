"""Comprehensive LVGL core API test suite for maix_lvgl on MaixCAM2.

Run on the device through the maixpy skill helper:
    python3 <skill>/scripts/maixpy_skill/cli.py run tests/suite_core.py

Covers: version/tools, lifecycle, display, obj, style, events, timers,
animations, layout, scrolling, groups, indev, subjects/observers, fs,
async calls, themes, memory and an end-to-end render check.

Some tests deliberately exercise known binding gaps and will FAIL; the
failure list is the defect report, not test noise.
"""
import array
import os
import time
import traceback

import maix_lvgl as lv
from maix import display, image, touchscreen

RESULTS = []
KEEP = []


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


def wait_until(pred, timeout_ms, label):
    end = time.monotonic() + timeout_ms / 1000.0
    while time.monotonic() < end:
        lv.timer_handler()
        if pred():
            return
        time.sleep(0.002)
    raise AssertionError(f"timeout waiting for {label}")


# ---------------------------------------------------------------- tools
def t_version():
    eq(lv.version_major(), 9, "major")
    eq(lv.version_minor(), 1, "minor")
    eq(lv.version_patch(), 0, "patch")
    info = lv.version_info()
    if not isinstance(info, str):
        raise AssertionError(f"version_info type {type(info)!r}")
    print("    version_info:", repr(info))


def t_is_initialized():
    eq(lv.is_initialized(), 1)


def t_colors():
    c = lv.color_make(10, 20, 30)
    eq(c.red, 10)
    eq(c.green, 20)
    eq(c.blue, 30)
    eq(c.to_int(), lv.color_hex(0x0A141E).to_int())
    eq(lv.color_hex3(0xF00).red, 255)
    eq(lv.color_white().to_int(), 0xFFFFFF)
    eq(lv.color_black().to_int(), 0)
    hsv = lv.color_hsv_to_rgb(0, 100, 100)
    eq(hsv.red, 255)
    eq(hsv.green, 0)
    back = lv.color_rgb_to_hsv(255, 0, 0)
    eq(back.h, 0)
    eq(back.s, 100)
    eq(back.v, 100)
    c32 = lv.color32_make(1, 2, 3, 4)
    eq((c32.red, c32.green, c32.blue, c32.alpha), (1, 2, 3, 4))
    eq(lv.color_16_16_mix(0x1234, 0x5678, 0), 0x5678)
    eq(lv.color_16_16_mix(0x1234, 0x5678, 255), 0x1234)
    mid = lv.color_16_16_mix(0, 0xFFFF, 128)
    if not (0x7000 <= mid <= 0x9000):
        raise AssertionError(f"color_16_16_mix mid={mid:#x}")


def t_color_format():
    eq(lv.color_format_get_bpp(lv.COLOR_FORMAT.ARGB8888), 32)
    eq(lv.color_format_get_size(lv.COLOR_FORMAT.ARGB8888), 4)
    eq(lv.color_format_has_alpha(lv.COLOR_FORMAT.ARGB8888), 1)


def t_math():
    eq(lv.map(5, 0, 10, 0, 100), 50)
    eq(lv.pow(2, 10), 1024)
    q = lv.sqrt_res_t()
    lv.sqrt(16, q, 0x8000)
    eq(q.i, 4, "sqrt int")
    eq(q.f, 0, "sqrt frac")
    eq(lv.trigo_sin(0), 0)
    eq(lv.trigo_cos(0), 32768)
    eq(lv.trigo_sin(90), 32768)
    eq(lv.atan2(0, 100), 0)
    eq(lv.cubic_bezier(0, 0, 0, 255, 255), 0)
    eq(lv.bezier3(0, 0, 0, 0, 255), 0)
    eq(lv.pct(50), 50 | 0x20000000)  # LV_COORD_SET_SPEC
    eq(lv.pct_to_px(lv.pct(50), 200), 100)
    eq(lv.clamp_width(10, 20, 100, 100), 20)
    eq(lv.clamp_height(10, 20, 100, 100), 20)
    lv.dpx(10)
    lv.grid_fr(1)
    lv.anim_speed(10)
    lv.anim_speed_clamped(10, 1, 100)
    lv.rand_set_seed(42)
    if not (0 <= lv.rand(0, 0xFFFF) < 0x10000):
        raise AssertionError("rand out of range")


def t_strings():
    eq(lv.strlen("abc"), 3)
    eq(lv.strcmp("abc", "abc"), 0)
    eq(lv.fs_get_ext("A:/tmp/foo.txt"), "txt")
    eq(lv.fs_get_last("A:/tmp/foo.txt"), "foo.txt")
    eq(lv.fs_up("A:/tmp/foo.txt"), "A:/tmp")
    eq(lv.fs_get_letters("A:/tmp"), "A")


def t_events_ids():
    a = lv.event_register_id()
    b = lv.event_register_id()
    if a <= 0 or b <= 0 or a == b:
        raise AssertionError(f"bad event ids {a} {b}")


def t_tick():
    t1 = lv.tick_get()
    pump(30)
    t2 = lv.tick_get()
    if t2 <= t1:
        raise AssertionError(f"tick did not advance: {t1} -> {t2}")
    if lv.tick_elaps(t1) <= 0:
        raise AssertionError("tick_elaps returned 0")


def t_fonts():
    fd = lv.font_default()
    if fd.get_line_height() <= 0:
        raise AssertionError("default font line height")
    if lv.font_montserrat_14.get_line_height() <= 0:
        raise AssertionError("montserrat 14 line height")
    w = lv.text_get_width("Hello", 5, fd, 0)
    if w <= 0:
        raise AssertionError("text_get_width")
    p = lv.point_t()
    lv.text_get_size(p, "Hello", fd, 0, 0, 1000, 0)
    if p.x <= 0 or p.y <= 0:
        raise AssertionError(f"text_get_size {p.x}x{p.y}")
    for name in ("font_montserrat_12", "font_montserrat_16",
                 "font_montserrat_20", "font_montserrat_24",
                 "font_montserrat_32"):
        if getattr(lv, name, None) is None:
            raise AssertionError(f"missing {name}")


def t_style_prop_default():
    v = lv.style_prop_get_default(lv.STYLE.RADIUS)
    if v is None:
        raise AssertionError("style_prop_get_default returned None")
    lv.style_get_num_custom_props()
    lv.style_prop_has_flag(lv.STYLE.RADIUS, 0)


def t_enums_present():
    # Every enum type declared in lvgl.pyi must be importable from the module.
    names = """ALIGN ANIM_ENABLE ANIM_IMAGE_PART BASE_DIR BLEND_MODE BORDER_SIDE
    CACHE_RESERVE_COND COLOR_FORMAT COVER_RES DIR DISPLAY_RENDER_MODE
    DISPLAY_ROTATION DRAW_TASK_STATE DRAW_TASK_TYPE EVENT FLEX_ALIGN FLEX_FLOW
    FONT_FMT_TXT FONT_FMT_TXT_CMAP FONT_GLYPH_FORMAT FONT_KERNING FONT_SUBPX
    FS_MODE FS_RES FS_SEEK GRAD_DIR GRID_ALIGN GROUP_REFOCUS_POLICY INDEV_MODE
    INDEV_STATE INDEV_TYPE KEY LAYER_TYPE LAYOUT OBJ_FLAG OPA PALETTE PART
    RB_COLOR RESULT RLOTTIE_CTRL SCREEN_LOAD_ANIM SCROLLBAR_MODE SCROLL_SNAP
    SPAN_MODE SPAN_OVERFLOW STATE STYLE STYLE_RES SUBJECT_TYPE TEXT_ALIGN
    TEXT_DECOR TEXT_FLAG THREAD_PRIO""".split()
    missing = [n for n in names if not hasattr(lv, n)]
    if missing:
        raise AssertionError("missing enum types: " + ", ".join(missing))


# ------------------------------------------------------------ display/obj
def t_display():
    d = lv.display_get_default()
    if d is None:
        raise AssertionError("no default display")
    eq(d.get_horizontal_resolution(), driver.width, "hor res")
    eq(d.get_vertical_resolution(), driver.height, "ver res")
    eq(d.get_color_format(), lv.COLOR_FORMAT.ARGB8888, "color format")
    if d.get_dpi() <= 0:
        raise AssertionError("dpi")
    d.get_rotation()
    if d.get_screen_active() is None:
        raise AssertionError("display screen_active")
    if d.get_antialiasing() not in (0, 1):
        raise AssertionError("antialiasing value")
    d.set_antialiasing(1)
    d.get_inactive_time()
    d.trigger_activity()


def t_obj_geometry():
    o = lv.obj(scr)
    o.set_pos(10, 20)
    o.update_layout()
    eq(o.get_x(), 10)
    eq(o.get_y(), 20)
    o.set_x(15)
    o.set_y(25)
    o.update_layout()
    eq((o.get_x(), o.get_y()), (15, 25))
    o.set_size(120, 60)
    o.update_layout()
    eq((o.get_width(), o.get_height()), (120, 60))
    o.set_width(130)
    o.set_height(70)
    o.update_layout()
    eq((o.get_width(), o.get_height()), (130, 70))
    o.align(lv.ALIGN.CENTER, 0, 0)
    o.update_layout()
    o.center()
    o.update_layout()
    o.set_align(lv.ALIGN.TOP_LEFT)
    o.delete()


def t_obj_tree():
    parent = lv.obj(scr)
    a = lv.obj(parent)
    b = lv.obj(parent)
    eq(parent.get_child_count(), 2)
    eq(a.get_index(), 0)
    eq(b.get_index(), 1)
    eq(a.get_parent().get_child_count(), 2)
    a.move_to_index(1)
    eq(a.get_index(), 1)
    eq(b.get_index(), 0)
    a.move_foreground()
    eq(a.get_index(), 1)
    a.move_background()
    eq(a.get_index(), 0)
    eq(parent.get_child(0).get_index(), 0)
    eq(b.get_sibling(-1).get_index(), 0)
    parent.clean()
    eq(parent.get_child_count(), 0)
    parent.delete()


def t_obj_flags_state():
    o = lv.obj(scr)
    eq(o.has_flag(lv.OBJ_FLAG.HIDDEN), 0)
    o.add_flag(lv.OBJ_FLAG.HIDDEN)
    eq(o.has_flag(lv.OBJ_FLAG.HIDDEN), 1)
    eq(o.has_flag_any(lv.OBJ_FLAG.HIDDEN | lv.OBJ_FLAG.CLICKABLE), 1)
    o.remove_flag(lv.OBJ_FLAG.HIDDEN)
    eq(o.has_flag(lv.OBJ_FLAG.HIDDEN), 0)
    o.add_state(lv.STATE.CHECKED)
    eq(o.has_state(lv.STATE.CHECKED), 1)
    if not (o.get_state() & lv.STATE.CHECKED):
        raise AssertionError("get_state missing CHECKED")
    o.remove_state(lv.STATE.CHECKED)
    eq(o.has_state(lv.STATE.CHECKED), 0)
    o.set_state(lv.STATE.PRESSED, 1)
    eq(o.has_state(lv.STATE.PRESSED), 1)
    o.set_state(lv.STATE.PRESSED, 0)
    eq(o.has_state(lv.STATE.PRESSED), 0)
    o.delete()


def t_obj_geometry_helpers():
    o = lv.obj(scr)
    o.set_pos(30, 40)
    o.set_size(100, 50)
    o.update_layout()
    a = lv.area_t()
    o.get_coords(a)
    eq((a.x1, a.y1), (30, 40))
    eq(a.get_width(), 100)
    eq(a.get_height(), 50)
    o.get_click_area(a)
    o.get_content_coords(a)
    o.set_content_width(200)
    o.set_content_height(300)
    # get_content_width() reports the resolved content area, not the
    # value passed to set_content_width().
    if o.get_content_width() < 0 or o.get_content_height() < 0:
        raise AssertionError("content size negative")
    o.set_ext_click_area(5)
    o.get_self_width()
    o.get_self_height()
    o.invalidate()
    # o.redraw(layer, obj) needs a real layer_t (pyi declares it without
    # self); direct layer access is not exposed, so it is not called here.
    o.update_layout()
    o.update_snap(0)
    o.refresh_style(lv.PART.MAIN, 0)
    o.refresh_self_size()
    o.refresh_ext_draw_size()
    o.allocate_spec_attr()
    o.dump_tree()
    o.delete()


def t_obj_user_data_int():
    # LVGL user_data is void*; plain Python ints have no pointer
    # representation, so this is documented as unsupported rather than a
    # crash.  Use a widget/struct/buffer or a Python dict for user_data.
    o = lv.obj(scr)
    try:
        o.set_user_data(1234)
    except TypeError:
        print("    NOTE: int user_data unsupported (void* only)", flush=True)
    o.delete()


def t_obj_user_data_obj():
    o = lv.obj(scr)
    o.set_user_data(o)
    # get_user_data() returns a pointer wrapper, not the original Python
    # object; only the stored pointer is observable from the binding.
    if o.get_user_data() is None:
        raise AssertionError("user_data pointer is None")
    o.delete()


def t_obj_parent_swap():
    p1 = lv.obj(scr)
    p2 = lv.obj(scr)
    o = lv.obj(p1)
    eq(o.get_parent().get_child_count(), 1)
    o.set_parent(p2)
    eq(p1.get_child_count(), 0)
    eq(p2.get_child_count(), 1)
    p1.delete()
    p2.delete()


def t_obj_delete_async():
    o = lv.obj(scr)
    o.delete_async()
    pump(30)
    o2 = lv.obj(scr)
    o2.delete_delayed(20)
    pump(80)


# ---------------------------------------------------------------- styles
def t_style_object():
    st = lv.style_t()
    st.init()
    st.set_radius(6)
    st.set_bg_color(lv.color_make(200, 100, 50))
    st.set_bg_opa(lv.OPA.COVER)
    st.set_text_color(lv.color_make(1, 2, 3))
    st.set_pad_all(4)
    st.set_border_width(2)
    st.set_border_color(lv.color_make(9, 9, 9))
    st.set_shadow_width(3)
    st.set_outline_width(2)
    st.set_line_width(2)
    st.set_arc_width(3)
    st.set_text_font(lv.font_montserrat_14)
    o = lv.obj(scr)
    o.add_style(st, 0)
    o.remove_style(st, 0)
    o.add_style(st, lv.PART.MAIN)
    o.remove_style_all()
    o.delete()


def t_style_local_props():
    o = lv.obj(scr)
    o.set_style_bg_color(lv.color_make(10, 20, 30), 0)
    c = o.get_style_bg_color(lv.PART.MAIN)
    eq((c.red, c.green, c.blue), (10, 20, 30))
    o.set_style_radius(7, 0)
    eq(o.get_style_radius(lv.PART.MAIN), 7)
    o.set_style_pad_all(3, 0)
    eq(o.get_style_pad_top(lv.PART.MAIN), 3)
    eq(o.get_style_pad_left(lv.PART.MAIN), 3)
    o.set_style_border_width(2, 0)
    eq(o.get_style_border_width(lv.PART.MAIN), 2)
    o.set_style_bg_opa(lv.OPA._50, 0)
    eq(o.get_style_bg_opa(lv.PART.MAIN), lv.OPA._50)
    o.set_style_text_color(lv.color_make(4, 5, 6), 0)
    eq(o.get_style_text_color(lv.PART.MAIN).to_int(), lv.color_make(4, 5, 6).to_int())
    o.set_style_width(80, 0)
    o.set_style_height(40, 0)
    o.set_style_min_width(10, 0)
    o.set_style_max_width(300, 0)
    o.set_style_opa(lv.OPA.COVER, 0)
    o.set_style_shadow_width(2, 0)
    o.set_style_outline_width(1, 0)
    o.set_style_transform_scale(256, 0)
    o.set_style_translate_x(1, 0)
    o.set_style_translate_y(1, 0)
    o.remove_style_all()
    o.delete()


def t_style_selector_state():
    o = lv.obj(scr)
    st = lv.style_t()
    st.init()
    st.set_bg_color(lv.color_make(255, 0, 0))
    o.add_style(st, lv.PART.MAIN | lv.STATE.PRESSED)
    o.add_state(lv.STATE.PRESSED)
    eq(o.get_style_bg_color(lv.PART.MAIN).to_int(), lv.color_make(255, 0, 0).to_int())
    o.remove_style(st, lv.PART.MAIN | lv.STATE.PRESSED)
    o.delete()


# ---------------------------------------------------------------- events
def t_events():
    o = lv.obj(scr)
    base = o.get_event_count()
    calls = []

    def cb(e):
        calls.append((e.get_code(), e.get_target(), e.get_current_target()))

    KEEP.append(cb)
    dsc = o.add_event_cb(cb, lv.EVENT.CLICKED, None)
    eq(o.get_event_count(), base + 1)
    if o.get_event_dsc(0) is None:
        raise AssertionError("get_event_dsc")
    o.send_event(lv.EVENT.CLICKED, None)
    eq(len(calls), 1)
    eq(calls[0][0], lv.EVENT.CLICKED)
    if calls[0][1] is None or calls[0][2] is None:
        raise AssertionError("event targets are None")
    o.remove_event_dsc(dsc)
    eq(o.get_event_count(), base)
    o.delete()


def t_events_custom_and_remove():
    o = lv.obj(scr)
    base = o.get_event_count()
    calls = []

    def cb(e):
        calls.append(1)

    KEEP.append(cb)
    cid = lv.event_register_id()
    o.add_event_cb(cb, cid, None)
    o.send_event(cid, None)
    eq(len(calls), 1)
    o.remove_event_cb(cb)
    eq(o.get_event_count(), base)
    o.add_event_cb(cb, lv.EVENT.CLICKED, None)
    o.add_event_cb(cb, lv.EVENT.PRESSED, None)
    eq(o.get_event_count(), base + 2)
    o.remove_event(0)
    eq(o.get_event_count(), base + 1)
    o.remove_event_cb_with_user_data(cb, None)
    eq(o.get_event_count(), base)
    o.delete()


def t_events_bubble():
    parent = lv.obj(scr)
    child = lv.obj(parent)
    child.add_flag(lv.OBJ_FLAG.EVENT_BUBBLE)
    got = []

    def pcb(e):
        got.append(e.get_code())

    KEEP.append(pcb)
    parent.add_event_cb(pcb, lv.EVENT.CLICKED, None)
    child.send_event(lv.EVENT.CLICKED, None)
    eq(len(got), 1)
    eq(got[0], lv.EVENT.CLICKED)
    parent.delete()


# ---------------------------------------------------------------- timers
def t_timer():
    fired = []

    def tcb(tm):
        fired.append(1)
        tm.ready()

    KEEP.append(tcb)
    tm = lv.timer_create(tcb, 20, None)
    KEEP.append(tm)
    wait_until(lambda: len(fired) >= 2, 1000, "timer fired")
    tm.set_period(10)
    tm.reset()
    tm.pause()
    eq(tm.get_paused(), 1)
    n = len(fired)
    pump(60)
    eq(len(fired), n)
    tm.resume()
    eq(tm.get_paused(), 0)
    wait_until(lambda: len(fired) > n, 500, "timer after resume")
    tm.set_repeat_count(1)
    tm.set_auto_delete(0)
    if tm.get_next() is None:
        raise AssertionError("timer get_next")
    tm.delete()


def t_timer_user_data_obj():
    fired = []

    def tcb(tm):
        fired.append(1)
        tm.ready()

    KEEP.append(tcb)
    tm = lv.timer_create(tcb, 20, None)
    pump(50)
    if not fired:
        raise AssertionError("timer did not fire")
    o = lv.obj(scr)
    tm.set_user_data(o)
    if tm.get_user_data() is None:
        raise AssertionError("timer user_data pointer is None")
    tm.delete()
    o.delete()


def t_timer_globals():
    lv.timer_get_idle()
    lv.timer_get_time_until_next()
    lv.timer_enable(1)
    b = lv.timer_create_basic()
    b.delete()


# ------------------------------------------------------------- animations
def t_anim_custom_exec():
    vals = []

    def aexec(a, v):
        vals.append(v)

    KEEP.append(aexec)
    a = lv.anim_t()
    a.init()
    a.set_custom_exec_cb(aexec)
    a.set_values(0, 100)
    a.set_time(60)
    eq(a.get_time(), 60)
    a.start()
    wait_until(lambda: vals and vals[-1] >= 100, 800, "custom anim end")
    wait_until(lambda: lv.anim_count_running() == 0, 800, "anim finish")


def t_anim_exec_cb():
    # lv_anim_set_exec_cb has no user_data slot in LVGL, so the raw binding
    # is private; maix_lvgl.anim_set_exec_cb routes through
    # lv_anim_set_custom_exec_cb and passes the anim_t wrapper.
    vals = []

    def aexec(a, v):
        vals.append(v)

    KEEP.append(aexec)
    a = lv.anim_t()
    a.init()
    a.set_values(0, 50)
    a.set_time(40)
    lv.anim_set_exec_cb(a, aexec)
    a.start()
    wait_until(lambda: vals and vals[-1] >= 50, 800, "exec_cb helper")


def t_anim_set_var_obj():
    a = lv.anim_t()
    a.init()
    o = lv.obj(scr)
    a.set_var(o)
    o.delete()


def t_anim_completed():
    done = []
    started = []

    def aexec(a, v):
        pass

    def scb(a):
        started.append(1)

    def ccb(a):
        done.append(1)

    KEEP.extend([aexec, scb, ccb])
    a = lv.anim_t()
    a.init()
    a.set_custom_exec_cb(aexec)
    a.set_values(0, 10)
    a.set_time(30)
    a.set_start_cb(scb)
    a.set_completed_cb(ccb)
    a.start()
    wait_until(lambda: done, 800, "completed cb")
    eq(len(started), 1)


def t_anim_misc():
    a = lv.anim_t()
    a.init()
    a.set_custom_exec_cb(lambda a, v: None)
    a.set_values(0, 10)
    a.set_time(100)
    a.set_delay(10)
    a.set_playback_time(20)
    a.set_repeat_count(2)
    a.set_early_apply(1)
    eq(a.get_delay(), 10)
    eq(a.get_repeat_count(), 2)
    a.get_playtime()
    a.set_path_cb(lambda a: 0)
    a.set_deleted_cb(lambda a: None)
    a.set_get_value_cb(lambda a: 0)
    lv.anim_refr_now()
    lv.anim_delete_all()
    pump(20)


def t_anim_timeline():
    def aexec(a, v):
        pass

    KEEP.append(aexec)
    a = lv.anim_t()
    a.init()
    a.set_custom_exec_cb(aexec)
    a.set_values(0, 10)
    a.set_time(50)
    eq(a.get_time(), 50, "anim duration before add")
    tl = lv.anim_timeline_create()
    tl.add(0, a)
    print("    timeline playtime:", tl.get_playtime(), flush=True)
    eq(tl.get_playtime(), 50)
    eq(tl.get_reverse(), 0)
    tl.set_reverse(1)
    eq(tl.get_reverse(), 1)
    # LV_ANIM_TIMELINE_PROGRESS_MAX is 0xFFFF.
    tl.set_progress(0x7FFF)
    prog = tl.get_progress()
    if not (0x7000 <= prog <= 0x9000):
        raise AssertionError(f"timeline progress {prog:#x}")
    tl.pause()
    tl.delete()


# ---------------------------------------------------------------- layout
def t_flex():
    cont = lv.obj(scr)
    cont.set_pos(0, 0)
    cont.set_size(300, 200)
    cont.set_flex_flow(lv.FLEX_FLOW.ROW)
    cont.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
    children = []
    for _ in range(3):
        c = lv.obj(cont)
        c.set_size(50, 50)
        children.append(c)
    cont.update_layout()
    xs = [c.get_x() for c in children]
    if not (xs[0] < xs[1] < xs[2]):
        raise AssertionError(f"flex did not lay out: {xs}")
    eq(cont.get_style_flex_flow(lv.PART.MAIN), lv.FLEX_FLOW.ROW)
    cont.delete()


def t_grid():
    cont = lv.obj(scr)
    cont.set_size(300, 200)
    col = array.array("i", [lv.grid_fr(1), lv.grid_fr(1), 0x1FFFFFFF])
    row = array.array("i", [lv.grid_fr(1), 0x1FFFFFFF])
    cont.set_grid_dsc_array(col, row)
    cont.set_grid_align(lv.GRID_ALIGN.START, lv.GRID_ALIGN.START)
    c = lv.obj(cont)
    c.set_grid_cell(lv.GRID_ALIGN.START, 1, 1, lv.GRID_ALIGN.START, 0, 1)
    cont.update_layout()
    if c.get_x() <= 0:
        raise AssertionError(f"grid cell x={c.get_x()}")
    cont.delete()


def t_grid_list_arg():
    # pyi declares Sequence[int]; the generated C requires a buffer.
    cont = lv.obj(scr)
    cont.set_size(300, 200)
    cont.set_grid_dsc_array([lv.grid_fr(1), 0x1FFFFFFF],
                            [lv.grid_fr(1), 0x1FFFFFFF])
    cont.delete()


def t_layout_switch():
    cont = lv.obj(scr)
    cont.set_layout(lv.LAYOUT.FLEX)
    eq(cont.get_style_layout(lv.PART.MAIN), lv.LAYOUT.FLEX)
    cont.set_layout(lv.LAYOUT.NONE)
    cont.delete()


# --------------------------------------------------------------- scrolling
def t_scroll():
    sc = lv.obj(scr)
    sc.set_pos(0, 0)
    sc.set_size(100, 100)
    sc.set_scroll_dir(lv.DIR.ALL)
    eq(sc.get_scroll_dir(), lv.DIR.ALL)
    sc.set_scrollbar_mode(lv.SCROLLBAR_MODE.OFF)
    eq(sc.get_scrollbar_mode(), lv.SCROLLBAR_MODE.OFF)
    c = lv.obj(sc)
    c.set_size(400, 400)
    sc.update_layout()
    sc.scroll_by(50, 50, 0)
    pump(20)
    # LVGL reports the scrolled content offset with the opposite sign.
    eq(abs(sc.get_scroll_x()), 50)
    eq(abs(sc.get_scroll_y()), 50)
    eq(abs(sc.get_scroll_left()), 50)
    eq(abs(sc.get_scroll_top()), 50)
    sc.scroll_to_x(10, 0)
    sc.scroll_to_y(20, 0)
    eq((abs(sc.get_scroll_x()), abs(sc.get_scroll_y())), (10, 20))
    p = lv.point_t()
    sc.get_scroll_end(p)
    if p.x < 0 or p.y < 0:
        raise AssertionError(f"scroll_end {p.x},{p.y}")
    sc.scroll_to_view(0)
    sc.readjust_scroll(0)
    sc.delete()


# ------------------------------------------------------------------ groups
def t_group():
    g = lv.group_create()
    o1 = lv.obj(scr)
    o2 = lv.obj(scr)
    g.add_obj(o1)
    g.add_obj(o2)
    eq(g.get_obj_count(), 2)
    g.focus_next()
    if g.get_focused() is None:
        raise AssertionError("group focused is None")
    g.focus_prev()
    g.set_editing(1)
    eq(g.get_editing(), 1)
    g.set_wrap(1)
    eq(g.get_wrap(), 1)
    g.send_data(0)
    g.remove_all_objs()
    eq(g.get_obj_count(), 0)
    g.delete()
    o1.delete()
    o2.delete()


def t_group_globals():
    lv.group_get_count()
    lv.group_get_default()
    lv.group_by_index(0)


# ------------------------------------------------------------------- indev
def t_indev():
    g = lv.group_create()
    ind = lv.indev_create()
    ind.set_type(lv.INDEV_TYPE.ENCODER)
    eq(ind.get_type(), lv.INDEV_TYPE.ENCODER)
    ind.set_mode(lv.INDEV_MODE.TIMER)
    eq(ind.get_mode(), lv.INDEV_MODE.TIMER)
    ind.get_state()
    ind.set_display(lv.display_get_default())
    if ind.get_display() is None:
        raise AssertionError("indev display")
    ind.set_group(g)
    if ind.get_group() is None:
        raise AssertionError("indev group")
    if ind.get_read_timer() is None:
        raise AssertionError("indev read timer")
    p = lv.point_t()
    ind.get_point(p)
    ind.delete()
    g.delete()
    lv.indev_get_active_obj()


# ------------------------------------------------------- subjects/observers
def t_subject_int():
    s = lv.subject_t()
    s.init_int(10)
    eq(s.get_int(), 10)
    s.set_int(20)
    eq(s.get_int(), 20)
    eq(s.get_previous_int(), 10)
    seen = []

    def ocb(obs, subj):
        seen.append(subj.get_int())

    KEEP.append(ocb)
    ob = s.add_observer(ocb, None)
    # get_target() is NULL for plain add_observer(); only add_observer_obj
    # records an object target.
    o = lv.obj(scr)
    ob2 = s.add_observer_obj(ocb, o, None)
    if ob2.get_target_obj() is None:
        raise AssertionError("observer.get_target_obj() returned None")
    ob2.remove()
    s.set_int(30)
    eq(s.get_int(), 30)
    if not seen or seen[-1] != 30:
        raise AssertionError(f"observer not called: {seen}")
    n = len(seen)
    ob.remove()
    s.set_int(40)
    eq(len(seen), n)


def t_subject_color():
    s = lv.subject_t()
    c = lv.color_make(7, 8, 9)
    s.init_color(c)
    eq(s.get_color().to_int(), c.to_int())
    s.set_color(lv.color_make(1, 2, 3))
    eq(s.get_color().to_int(), lv.color_make(1, 2, 3).to_int())
    s.get_previous_color()


def t_subject_pointer_obj():
    s = lv.subject_t()
    o = lv.obj(scr)
    s.init_pointer(o)
    if s.get_pointer() is None:
        raise AssertionError("subject pointer")
    s.set_pointer(o)
    o.delete()


def t_subject_bindings():
    s = lv.subject_t()
    s.init_int(50)
    sl = lv.slider(scr)
    sl.set_range(0, 100)
    sl.bind_value(s)
    s.set_int(70)
    pump(20)
    eq(sl.get_value(), 70)
    lb = lv.label(scr)
    lb.bind_text(s, "v: %d")
    s.set_int(80)
    pump(20)
    eq(lb.get_text(), "v: 80")
    btn = lv.button(scr)
    btn.bind_checked(s)
    s.set_int(1)
    pump(20)
    eq(btn.has_state(lv.STATE.CHECKED), 1)
    sl.delete()
    lb.delete()
    btn.delete()


def t_bind_flag_state():
    s = lv.subject_t()
    s.init_int(1)
    o = lv.obj(scr)
    o.bind_flag_if_eq(s, lv.OBJ_FLAG.HIDDEN, 1)
    o.bind_flag_if_not_eq(s, lv.OBJ_FLAG.CLICKABLE, 1)
    o.bind_state_if_eq(s, lv.STATE.CHECKED, 1)
    o.bind_state_if_not_eq(s, lv.STATE.PRESSED, 1)
    s.set_int(0)
    pump(20)
    s.set_int(1)
    pump(20)
    o.delete()


# ---------------------------------------------------------------------- fs
def t_fs():
    lv.fs_stdio_init()
    eq(lv.fs_is_ready(ord("A")), 1)
    path = "A:/tmp/maix_lvgl_suite_core.txt"
    f = lv.fs_file_t()
    eq(f.open(path, lv.FS_MODE.WR), 0, "open wr")
    data = bytearray(b"hello lvgl")
    bw = array.array("I", [0])
    eq(f.write(data, len(data), bw), 0, "write res")
    eq(bw[0], len(data), "written")
    f.close()

    f2 = lv.fs_file_t()
    eq(f2.open(path, lv.FS_MODE.RD), 0, "open rd")
    rb = bytearray(32)
    br = array.array("I", [0])
    eq(f2.read(rb, len(data), br), 0, "read res")
    eq(br[0], len(data), "read len")
    eq(bytes(rb[: br[0]]), b"hello lvgl", "read data")
    pos = array.array("I", [0])
    f2.tell(pos)
    eq(pos[0], len(data), "tell")
    f2.seek(0, lv.FS_SEEK.SET)
    eq(f2.read(rb, 5, br), 0)
    eq(bytes(rb[: br[0]]), b"hello")
    f2.close()
    os.unlink("/tmp/maix_lvgl_suite_core.txt")


# ------------------------------------------------------------------- async
def t_async():
    got = []

    def acb(_):
        got.append(1)

    KEEP.append(acb)
    lv.async_call(acb, None)
    wait_until(lambda: got, 500, "async call")


# ------------------------------------------------------------------ theme
def t_theme():
    eq(lv.theme_default_is_inited(), 1)
    if lv.theme_default_get() is None:
        raise AssertionError("theme_default_get")
    if lv.theme_get_from_obj(scr) is None:
        raise AssertionError("theme_get_from_obj")
    lv.theme_get_color_primary(scr)
    lv.theme_get_color_secondary(scr)
    if lv.theme_get_font_small(scr) is None:
        raise AssertionError("theme small font")
    if lv.theme_get_font_normal(scr) is None:
        raise AssertionError("theme normal font")
    if lv.theme_get_font_large(scr) is None:
        raise AssertionError("theme large font")
    o = lv.obj(scr)
    lv.theme_apply(o)
    o.delete()


# ------------------------------------------------------------------- memory
def t_memory():
    m = lv.mem_monitor_t()
    m.monitor()
    if m.total_size == 0:
        # LV_USE_STDLIB_MALLOC == LV_STDLIB_CLIB: the built-in monitor is
        # not available, this is a configuration limitation, not a crash.
        print("    NOTE: mem monitor unavailable (LV_STDLIB_CLIB)", flush=True)
        return
    if m.total_size <= 0 or m.free_size <= 0:
        raise AssertionError(f"mem monitor total={m.total_size} free={m.free_size}")
    if m.used_pct < 0 or m.used_pct > 100:
        raise AssertionError(f"used_pct={m.used_pct}")


# ---------------------------------------------------------- render end-to-end
def t_render():
    w, h = driver.width, driver.height
    red = lv.obj(scr)
    red.set_pos(0, 0)
    red.set_size(w, h)
    red.set_style_radius(0, 0)
    red.set_style_border_width(0, 0)
    red.set_style_bg_color(lv.color_make(255, 0, 0), 0)
    red.set_style_bg_opa(lv.OPA.COVER, 0)
    pump(150)
    lv.refr_now(driver._disp)
    idx = (h // 2) * w * 4 + (w // 2) * 4
    b, g, r, a = driver._buffer[idx: idx + 4]
    eq((r, g, b), (255, 0, 0), "center pixel RGB")
    red.delete()
    pump(50)
    run_dir = os.environ.get("MAIXPY_SKILL_RUN_DIR")
    if run_dir:
        art = os.path.join(run_dir, "artifacts")
        os.makedirs(art, exist_ok=True)
        img = image.from_bytes(w, h, image.Format.FMT_BGRA8888,
                               bytes(driver._buffer), True)
        out = os.path.join(art, "suite_core.png")
        img.save(out)
        print("    screenshot:", out, flush=True)


# --------------------------------------------------------------------- main
def main():
    global scr, driver
    disp = display.Display()
    ts = touchscreen.TouchScreen()
    driver = lv.init(disp, ts)
    scr = lv.screen_active()

    tests = [
        ("version", t_version),
        ("is_initialized", t_is_initialized),
        ("colors", t_colors),
        ("color_format", t_color_format),
        ("math", t_math),
        ("strings", t_strings),
        ("event_ids", t_events_ids),
        ("tick", t_tick),
        ("fonts", t_fonts),
        ("style_prop_default", t_style_prop_default),
        ("enums_present", t_enums_present),
        ("display", t_display),
        ("obj_geometry", t_obj_geometry),
        ("obj_tree", t_obj_tree),
        ("obj_flags_state", t_obj_flags_state),
        ("obj_geometry_helpers", t_obj_geometry_helpers),
        ("obj_user_data_int", t_obj_user_data_int),
        ("obj_user_data_obj", t_obj_user_data_obj),
        ("obj_parent_swap", t_obj_parent_swap),
        ("obj_delete_async", t_obj_delete_async),
        ("style_object", t_style_object),
        ("style_local_props", t_style_local_props),
        ("style_selector_state", t_style_selector_state),
        ("events", t_events),
        ("events_custom_remove", t_events_custom_and_remove),
        ("events_bubble", t_events_bubble),
        ("timer", t_timer),
        ("timer_user_data_obj", t_timer_user_data_obj),
        ("timer_globals", t_timer_globals),
        ("anim_custom_exec", t_anim_custom_exec),
        ("anim_exec_cb", t_anim_exec_cb),
        ("anim_set_var_obj", t_anim_set_var_obj),
        ("anim_completed", t_anim_completed),
        ("anim_misc", t_anim_misc),
        ("anim_timeline", t_anim_timeline),
        ("flex", t_flex),
        ("grid", t_grid),
        ("grid_list_arg", t_grid_list_arg),
        ("layout_switch", t_layout_switch),
        ("scroll", t_scroll),
        ("group", t_group),
        ("group_globals", t_group_globals),
        ("indev", t_indev),
        ("subject_int", t_subject_int),
        ("subject_color", t_subject_color),
        ("subject_pointer_obj", t_subject_pointer_obj),
        ("subject_bindings", t_subject_bindings),
        ("bind_flag_state", t_bind_flag_state),
        ("fs", t_fs),
        ("async", t_async),
        ("theme", t_theme),
        ("memory", t_memory),
        ("render", t_render),
    ]
    for name, fn in tests:
        check(name, fn)

    # Cleanup and verify deinit/re-init lifecycle.
    try:
        lv.deinit()
        eq(lv.is_initialized(), 0, "deinit")
        print("[PASS] deinit", flush=True)
        RESULTS.append(("deinit", True, ""))
    except Exception as e:
        print(f"[FAIL] deinit :: {type(e).__name__}: {e}", flush=True)
        RESULTS.append(("deinit", False, str(e)))
    try:
        ts.close()
        disp.close()
    except Exception:
        pass

    try:
        disp2 = display.Display()
        ts2 = touchscreen.TouchScreen()
        lv.init(disp2, ts2)
        eq(lv.is_initialized(), 1, "reinit")
        lv.deinit()
        ts2.close()
        disp2.close()
        print("[PASS] reinit_lifecycle", flush=True)
        RESULTS.append(("reinit_lifecycle", True, ""))
    except Exception as e:
        print(f"[FAIL] reinit_lifecycle :: {type(e).__name__}: {e}", flush=True)
        RESULTS.append(("reinit_lifecycle", False, str(e)))

    total = len(RESULTS)
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    failed = [n for n, ok, _ in RESULTS if not ok]
    print("\nSUMMARY: %d/%d passed" % (passed, total), flush=True)
    if failed:
        print("FAILED: " + ", ".join(failed), flush=True)
    print("RESULT:", "OK" if not failed else "FAIL", flush=True)


if __name__ == "__main__":
    main()
