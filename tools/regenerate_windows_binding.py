"""Regenerate the CPython binding for the Windows (SDL) build.

Uses the same LVGL 9.1.0 source as the other builds, but generates against
``windows/lv_conf.h`` (SDL enabled, FreeType/RLottie disabled, OS none).
Output goes to ``windows/binding/``.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import maixcdk_lvgl as mk
import regenerate_binding as rb

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WINDOWS_DIR = PROJECT_ROOT / "windows"
BINDING_DIR = WINDOWS_DIR / "binding"
CONF = WINDOWS_DIR / "lv_conf.h"


def main():
    sdk = mk.find_maixcdk()
    version = mk.lvgl_version(sdk)
    lvgl_dir = mk.ensure_lvgl_source(sdk, version)

    import patch_lvgl

    patch_lvgl.apply(lvgl_dir, lambda msg: print(msg, flush=True))

    rb._generate(
        lvgl_dir,
        CONF,
        {"windows": True, "lvgl": version},
        out_dir=BINDING_DIR,
        stamp_file=None,
    )


if __name__ == "__main__":
    main()
