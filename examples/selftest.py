"""Render one LVGL frame and save it as a PNG, or show the SDL window.

On MaixPy the PNG is written to /tmp/maix_lvgl_selftest.png.  On desktop Linux
the SDL backend has no CPU frame buffer, so the window is shown for a couple of
seconds instead.

    python selftest.py
"""
import time

import maix_lvgl as lv

from _common import deinit_lvgl, init_lvgl, save_screenshot

OUTPUT = "/tmp/maix_lvgl_selftest.png"


def main():
    driver, disp, ts = init_lvgl()
    try:
        scr = lv.screen_active()
        btn = lv.button(scr)
        btn.center()
        label = lv.label(btn)
        label.set_text("maix_lvgl 9.1.0")

        lv.timer_handler()
        lv.refr_now(driver._disp)

        if save_screenshot(driver, OUTPUT):
            print("saved:", OUTPUT, driver.width, driver.height)
        else:
            print("no CPU frame buffer in this backend; showing SDL window")
            time.sleep(2.0)
    finally:
        deinit_lvgl(driver, disp, ts)


if __name__ == "__main__":
    main()
