"""Regenerate the CPython binding for the desktop Linux (SDL) build.

Uses the same LVGL 9.1.0 source tree as the device build, but generates the
binding against ``linux/lv_conf.h`` (SDL enabled, FreeType/RLottie disabled).
Output goes to ``linux/binding/`` so it does not disturb the MaixCAM binding.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import maixcdk_lvgl as mk
import regenerate_binding as rb

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LINUX_DIR = PROJECT_ROOT / "linux"
BINDING_DIR = LINUX_DIR / "binding"
CONF = LINUX_DIR / "lv_conf.h"


def main():
    sdk = mk.find_maixcdk()
    version = mk.lvgl_version(sdk)
    lvgl_dir = mk.ensure_lvgl_source(sdk, version)

    # Same LVGL 9.1 fixes as the device build (observer/canvas).
    import patch_lvgl

    patch_lvgl.apply(lvgl_dir, lambda msg: print(msg, flush=True))

    rb._generate(
        lvgl_dir,
        CONF,
        {"linux": True, "lvgl": version},
        out_dir=BINDING_DIR,
        stamp_file=None,
    )


if __name__ == "__main__":
    main()
