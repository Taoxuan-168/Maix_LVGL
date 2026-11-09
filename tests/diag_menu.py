"""Locate the segfault in the menu widget path, one step at a time."""
import time

import maix_lvgl as lv
from maix import display, touchscreen


def pump(ms):
    end = time.monotonic() + ms / 1000.0
    while time.monotonic() < end:
        lv.timer_handler()
        time.sleep(0.002)


disp = display.Display()
ts = touchscreen.TouchScreen()
driver = lv.init(disp, ts)
scr = lv.screen_active()

print("step: menu", flush=True)
m = lv.menu(scr)
print("step: menu_page", flush=True)
page = lv.menu_page(m, "Page")
print("step: set_page", flush=True)
m.set_page(page)
print("step: get_cur_main_page", flush=True)
p = m.get_cur_main_page()
print("  page:", p, flush=True)
print("step: set_page_title", flush=True)
m.set_page_title("Title")
print("step: get_main_header", flush=True)
h = m.get_main_header()
print("  header:", h, flush=True)
print("step: menu_section", flush=True)
sec = lv.menu_section(page)
print("  section:", sec, flush=True)
print("step: menu_separator", flush=True)
sep = lv.menu_separator(page)
print("  separator:", sep, flush=True)
print("step: menu_cont", flush=True)
cont = lv.menu_cont(page)
print("  cont:", cont, flush=True)
print("step: set_mode_header", flush=True)
m.set_mode_header(lv.menu.HEADER.TOP_FIXED)
print("step: set_mode_root_back_button", flush=True)
m.set_mode_root_back_button(lv.menu.ROOT_BACK_BUTTON.ENABLED)
print("step: pump", flush=True)
pump(50)
print("step: delete", flush=True)
m.delete()
print("MENU DONE", flush=True)

lv.deinit()
ts.close()
disp.close()
print("DONE", flush=True)
