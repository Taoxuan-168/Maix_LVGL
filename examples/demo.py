"""Minimal MaixPy / desktop Linux LVGL demo.

Run on a MaixCAM2 (launcher stopped / development mode) or on desktop Linux:

    python demo.py

The LVGL API is re-exported by maix_lvgl, so widgets are created exactly like
in the MicroPython LVGL binding (``import lvgl as lv``).
"""
import time

import maix_lvgl as lv

from _common import deinit_lvgl, init_lvgl, need_exit


def main():
    driver, disp, ts = init_lvgl()
    try:
        scr = lv.screen_active()

        btn = lv.button(scr)
        btn.set_size(240, 120)
        btn.center()
        label = lv.label(btn)
        label.set_text("Click me")
        label.center()

        counter = [0]

        def on_clicked(event):
            counter[0] += 1
            label.set_text(f"Clicked {counter[0]}")

        btn.add_event_cb(on_clicked, lv.EVENT.CLICKED, None)

        while not need_exit():
            lv.timer_handler()
            time.sleep(0.005)
    finally:
        deinit_lvgl(driver, disp, ts)


if __name__ == "__main__":
    main()
