"""Shared helpers for running the examples on MaixPy or desktop Linux."""
from __future__ import annotations

try:
    from maix import app, display, image, touchscreen

    HAS_MAIX = True
except ImportError:
    app = None
    display = None
    image = None
    touchscreen = None
    HAS_MAIX = False

import maix_lvgl as lv


def init_lvgl(width=640, height=480, touch=True):
    """Return ``(driver, display_obj, touchscreen_obj)``.

    On MaixPy, opens the device display and touchscreen.  On desktop Linux,
    creates an SDL window of ``width x height``; ``touch`` is ignored there.
    """
    if HAS_MAIX:
        disp = display.Display()
        ts = touchscreen.TouchScreen() if touch else False
        driver = lv.init(disp, ts)
        return driver, disp, (None if ts is False else ts)
    return lv.init(width, height), None, None


def deinit_lvgl(driver, disp, ts):
    try:
        lv.deinit()
    finally:
        if ts is not None:
            try:
                ts.close()
            except Exception:
                pass
        if disp is not None:
            try:
                disp.close()
            except Exception:
                pass


def need_exit():
    return app.need_exit() if HAS_MAIX else False


def save_screenshot(driver, path):
    """Save a PNG of the LVGL frame if the backend exposes a pixel buffer."""
    buffer = getattr(driver, "_buffer", None)
    if image is None or buffer is None:
        return False
    img = image.from_bytes(
        driver.width,
        driver.height,
        image.Format.FMT_BGRA8888,
        bytes(buffer),
        True,
    )
    img.save(path)
    return True
