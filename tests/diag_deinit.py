"""Minimal deinit crash repro: subject add_observer_obj + remove."""
import time

import maix_lvgl as lv
from maix import display, touchscreen

disp = display.Display()
ts = touchscreen.TouchScreen()
lv.init(disp, ts)
scr = lv.screen_active()

print("step: subject", flush=True)
s = lv.subject_t()
s.init_int(1)
seen = []


def cb(obs, subj):
    seen.append(subj.get_int())


print("step: add_observer_obj", flush=True)
o = lv.obj(scr)
ob = s.add_observer_obj(cb, o, None)
s.set_int(2)
print("  seen:", seen, flush=True)
print("step: remove", flush=True)
ob.remove()
print("step: deinit", flush=True)
lv.deinit()
print("step: close", flush=True)
ts.close()
disp.close()
print("DONE", flush=True)
