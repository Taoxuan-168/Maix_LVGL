"""Diagnose specific binding behaviours seen in suite_core failures."""
import array
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

print("driver size:", driver.width, driver.height)
d = lv.display_get_default()
print("lvgl display:", d.get_horizontal_resolution(), d.get_vertical_resolution())

# enum availability
names = [n for n in dir(lv) if n.isupper() or n.startswith("ANIM") or n.startswith("INDEV")]
print("upper names:", " ".join(sorted(names)))

print("version_info:", repr(lv.version_info()))

# anim timeline
a = lv.anim_t()
a.init()
a.set_custom_exec_cb(lambda a, v: None)
a.set_values(0, 10)
a.set_time(50)
print("anim time after set:", a.get_time(), "duration field:", a.duration)
tl = lv.anim_timeline_create()
tl.add(0, a)
print("timeline playtime:", tl.get_playtime())
tl.delete()

# grid with array
cont = lv.obj(scr)
cont.set_size(300, 200)
col = array.array("i", [lv.grid_fr(1), lv.grid_fr(1), 0x1FFFFFFF])
row = array.array("i", [lv.grid_fr(1), 0x1FFFFFFF])
try:
    cont.set_grid_dsc_array(col, row)
    print("grid array OK")
except Exception as e:
    print("grid array FAIL:", type(e).__name__, e)
cont.delete()

# obj as void*
o = lv.obj(scr)
for label, fn in [
    ("set_user_data(obj)", lambda: o.set_user_data(o)),
    ("anim.set_var(obj)", lambda: (lambda x: (x.init(), x.set_var(o)))(lv.anim_t())),
    ("subject.init_pointer(obj)", lambda: lv.subject_t().init_pointer(o)),
]:
    try:
        fn()
        print(label, "OK")
    except Exception as e:
        print(label, "FAIL:", type(e).__name__, e)

# timer user_data obj
fired = []
tm = lv.timer_create(lambda t: (fired.append(1), t.ready()), 20, None)
pump(60)
print("timer fired:", len(fired))
try:
    tm.set_user_data(o)
    print("timer.set_user_data(obj) OK")
except Exception as e:
    print("timer.set_user_data(obj) FAIL:", type(e).__name__, e)
tm.delete()

# events default count
o2 = lv.obj(scr)
print("fresh obj event count:", o2.get_event_count())
for i in range(o2.get_event_count()):
    print("  dsc", i, o2.get_event_dsc(i))
o2.delete()

# set_pos + update_layout
o3 = lv.obj(scr)
o3.set_pos(10, 20)
print("get_x before layout:", o3.get_x(), "after update_layout:", end=" ")
o3.update_layout()
print(o3.get_x(), o3.get_y())
o3.delete()

# bubble with flag on child
p = lv.obj(scr)
c = lv.obj(p)
c.add_flag(lv.OBJ_FLAG.EVENT_BUBBLE)
got = []
p.add_event_cb(lambda e: got.append(e.get_code()), lv.EVENT.CLICKED, None)
c.send_event(lv.EVENT.CLICKED, None)
print("bubble child-flag got:", got)
p.delete()

# mem
m = lv.mem_monitor_t()
m.monitor()
print("mem total/free/used_pct:", m.total_size, m.free_size, m.used_pct)

# subject observer target before remove
s = lv.subject_t()
s.init_int(1)
seen = []
ob = s.add_observer(lambda obs, subj: seen.append(1), None)
s.set_int(2)
print("observer target before remove:", ob.get_target(), "target_obj:", ob.get_target_obj())
ob.remove()

# obj identity
a1 = lv.obj(scr)
a2 = lv.obj(a1)
print("child identity eq:", a2 == a1.get_child(0), "index:", a1.get_child(0).get_index())
a1.delete()

# anim.set_exec_cb raw check: field after set
aa = lv.anim_t()
aa.init()
aa.set_exec_cb(lambda a, v: None)
print("anim exec_cb field after set:", aa.exec_cb)

lv.deinit()
ts.close()
disp.close()
print("DONE")
