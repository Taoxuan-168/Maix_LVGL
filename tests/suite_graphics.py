"""LVGL graphics API test suite for maix_lvgl on MaixCAM2.

Covers draw buffers, canvas buffers, image descriptors, decoders, software
rotation/blending helpers, fonts, allocation helpers and layer handles.
Direct lv_draw_* primitives need a real layer_t from the render pipeline;
they are exercised indirectly through widget rendering in suite_widgets.py.
"""
import time
import traceback

import maix_lvgl as lv
from maix import display, touchscreen

RESULTS = []
KEEP = []

SYM_OK = "\xef\x80\x81"


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


def t_draw_buf_basics():
    stride = lv.draw_buf_width_to_stride(64, lv.COLOR_FORMAT.ARGB8888)
    if stride <= 0:
        raise AssertionError("stride")
    buf = lv.draw_buf_create(64, 32, lv.COLOR_FORMAT.ARGB8888, stride)
    if buf is None:
        raise AssertionError("draw_buf_create")
    eq(buf.header.w, 64)
    eq(buf.header.h, 32)
    eq(buf.data_size, stride * 32)
    if buf.goto_xy(0, 0) is None:
        raise AssertionError("goto_xy")
    buf.clear(area(0, 0, 63, 31))
    if buf.has_flag(lv.image.FLAGS.MODIFIABLE) not in (0, 1):
        raise AssertionError("MODIFIABLE flag value")
    buf.set_flag(lv.image.FLAGS.USER1)
    eq(buf.has_flag(lv.image.FLAGS.USER1), 1)
    buf.clear_flag(lv.image.FLAGS.USER1)
    eq(buf.has_flag(lv.image.FLAGS.USER1), 0)
    buf.set_palette(0, lv.color32_make(1, 2, 3, 4))
    img = lv.image_dsc_t()
    buf.to_image(img)
    eq(img.header.w, 64)
    eq(img.header.h, 32)
    if img.data is None:
        raise AssertionError("image data")
    buf2 = buf.dup()
    if buf2 is None:
        raise AssertionError("dup")
    buf2.destroy()
    buf.destroy()


def t_draw_buf_reshape():
    stride = lv.draw_buf_width_to_stride(32, lv.COLOR_FORMAT.RGB565)
    buf = lv.draw_buf_create(32, 32, lv.COLOR_FORMAT.RGB565, stride)
    new_stride = buf.adjust_stride(stride)
    if new_stride < 0:
        raise AssertionError("adjust_stride")
    b2 = buf.reshape(lv.COLOR_FORMAT.RGB565, 16, 16, new_stride)
    if b2 is None:
        raise AssertionError("reshape")
    eq(b2.header.w, 16)
    buf.destroy()


def t_draw_buf_handlers():
    h = lv.draw_buf_get_handlers()
    if h is None:
        raise AssertionError("draw_buf_get_handlers")


def t_draw_buf_align():
    buf = bytearray(64 * 4)
    KEEP.append(buf)
    p = lv.draw_buf_align(buf, lv.COLOR_FORMAT.ARGB8888)
    if p is None:
        raise AssertionError("draw_buf_align")


def t_canvas_draw_buf():
    print("    canvas: create", flush=True)
    cv = lv.canvas(scr)
    cv.set_size(32, 32)
    data = bytearray(32 * 32 * 4)
    KEEP.append(data)
    print("    canvas: set_buffer", flush=True)
    cv.set_buffer(data, 32, 32, lv.COLOR_FORMAT.ARGB8888)
    print("    canvas: fill_bg", flush=True)
    cv.fill_bg(lv.color_make(0, 255, 0), lv.OPA.COVER)
    print("    canvas: get_draw_buf", flush=True)
    db = cv.get_draw_buf()
    if db is None:
        raise AssertionError("canvas draw_buf")
    eq(db.header.w, 32)
    eq(db.header.h, 32)
    print("    canvas: get_image", flush=True)
    img = cv.get_image()
    if img is None:
        raise AssertionError("canvas image")
    print("    canvas: delete", flush=True)
    cv.delete()


def t_canvas_copy_buf():
    cv = lv.canvas(scr)
    cv.set_size(32, 32)
    data = bytearray(32 * 32 * 4)
    KEEP.append(data)
    cv.set_buffer(data, 32, 32, lv.COLOR_FORMAT.ARGB8888)
    cv.fill_bg(lv.color_make(0, 0, 255), lv.OPA.COVER)
    db2 = lv.draw_buf_create(
        16, 16, lv.COLOR_FORMAT.ARGB8888,
        lv.draw_buf_width_to_stride(16, lv.COLOR_FORMAT.ARGB8888),
    )
    cv.copy_buf(area(0, 0, 15, 15), db2, area(0, 0, 15, 15))
    db2.destroy()
    cv.delete()


def t_image_src_type():
    KEEP.append(SYM_OK)
    t = lv.image_src_get_type(SYM_OK)
    eq(t, lv.image.SRC.SYMBOL)
    t2 = lv.image_src_get_type("A:/tmp/none.png")
    eq(t2, lv.image.SRC.FILE)


def t_image_decoder_create():
    dec = lv.image_decoder_create()
    if dec is None:
        raise AssertionError("decoder_create")
    dec.delete()


def t_decoders_init():
    lv.lodepng_init()
    lv.bin_decoder_init()
    lv.lodepng_deinit()


def t_draw_sw_rotate():
    src = bytearray(16 * 16 * 4)
    dest = bytearray(16 * 16 * 4)
    KEEP.extend([src, dest])
    lv.draw_sw_rotate(src, dest, 16, 16, 16 * 4, 16 * 4,
                      lv.DISPLAY_ROTATION._90, lv.COLOR_FORMAT.ARGB8888)


def t_draw_sw_rgb565_swap():
    buf = bytearray(16 * 2)
    KEEP.append(buf)
    lv.draw_sw_rgb565_swap(buf, 16)


def t_draw_arc_get_area():
    a = lv.area_t()
    lv.draw_arc_get_area(0, 0, 50, 0, 180, 4, 1, a)
    if a.get_width() <= 0 or a.get_height() <= 0:
        raise AssertionError(f"arc area {a.get_width()}x{a.get_height()}")


def t_font_glyph():
    f = lv.font_default()
    w = f.get_glyph_width(ord("A"), 0)
    if w <= 0:
        raise AssertionError("glyph width")
    # NOTE: f.set_kerning() is not called: lv_font_set_kerning writes into
    # the font struct, and the built-in Montserrat fonts live in read-only
    # data, so the call segfaults. Reported as a dangerous API.


def t_layers():
    for fn in (lv.layer_top, lv.layer_bottom, lv.layer_sys):
        o = fn()
        if o is None:
            raise AssertionError(f"{fn.__name__} returned None")


def t_malloc_free():
    p = lv.malloc(32)
    if p is None:
        raise AssertionError("malloc")
    lv.free(p)


def t_fs_drv():
    lv.fs_stdio_init()
    d = lv.fs_get_drv(ord("A"))
    if d is None:
        raise AssertionError("fs_get_drv")


def t_image_cache():
    lv.image_cache_resize(0, 1)
    lv.image_header_cache_resize(0, 1)
    KEEP.append(SYM_OK)
    lv.image_cache_drop(SYM_OK)


def t_version_info():
    # LVGL_VERSION_INFO is empty in this build; the function must still be
    # callable and return a str.
    info = lv.version_info()
    if not isinstance(info, str):
        raise AssertionError("version_info type")


def main():
    global scr
    disp = display.Display()
    ts = touchscreen.TouchScreen()
    lv.init(disp, ts)
    scr = lv.screen_active()

    tests = [
        ("draw_buf_basics", t_draw_buf_basics),
        ("draw_buf_reshape", t_draw_buf_reshape),
        ("draw_buf_handlers", t_draw_buf_handlers),
        ("draw_buf_align", t_draw_buf_align),
        ("canvas_draw_buf", t_canvas_draw_buf),
        ("canvas_copy_buf", t_canvas_copy_buf),
        ("image_src_type", t_image_src_type),
        ("image_decoder_create", t_image_decoder_create),
        ("decoders_init", t_decoders_init),
        ("draw_sw_rotate", t_draw_sw_rotate),
        ("draw_sw_rgb565_swap", t_draw_sw_rgb565_swap),
        ("draw_arc_get_area", t_draw_arc_get_area),
        ("font_glyph", t_font_glyph),
        ("layers", t_layers),
        ("malloc_free", t_malloc_free),
        ("fs_drv", t_fs_drv),
        ("image_cache", t_image_cache),
        ("version_info", t_version_info),
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
