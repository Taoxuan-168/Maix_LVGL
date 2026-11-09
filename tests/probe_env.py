"""Probe the device environment for maix_lvgl testing."""
import os
import sys

print("python:", sys.version)
print("platform:", sys.platform)

import maix
print("maix version:", getattr(maix, "__version__", "unknown"))

try:
    import maix_lvgl as lv
    print("maix_lvgl version:", lv.__version__)
    print("maix_lvgl file:", lv.__file__)
except Exception as e:
    print("maix_lvgl import FAILED:", repr(e))
    raise

import lvgl
print("lvgl module:", lvgl.__file__)
print("lvgl version macro:", lvgl.version_info() if hasattr(lvgl, "version_info") else "n/a")

for name in ("init", "deinit", "timer_handler", "run", "process",
             "obj", "label", "button", "style_t", "timer_create", "anim_t",
             "screen_active", "display_create", "indev_create", "group_create",
             "fs_stdio_init", "canvas", "chart", "table", "image", "font_default"):
    print("has", name, ":", hasattr(lv, name))

# Count exported names
names = [n for n in dir(lv) if not n.startswith("_")]
print("exported names:", len(names))

# Check a few enum values
print("EVENT.CLICKED:", int(lv.EVENT.CLICKED))
print("COLOR_FORMAT.ARGB8888:", int(lv.COLOR_FORMAT.ARGB8888))
print("OBJ_FLAG.HIDDEN:", int(lv.OBJ_FLAG.HIDDEN))

# memory info
# mem monitor needs lv_init
