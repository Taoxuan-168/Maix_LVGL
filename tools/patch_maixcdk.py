"""Enable LVGL FreeType inside MaixCDK (idempotent).

The MaixCDK LVGL component ships FreeType support disabled.  The maix_lvgl
binding needs it to load device fonts such as
``/maixapp/share/font/SourceHanSansCN-Regular.otf``.  This patch is applied by
``regenerate_binding.ensure_binding`` before CMake configures the build, so a
fresh MaixCDK checkout gets the same configuration.
"""
from __future__ import annotations

from pathlib import Path


def enable_freetype(sdk, log=print) -> int:
    sdk = Path(sdk)
    changed = 0

    conf = sdk / "components" / "3rd_party" / "lvgl" / "conf" / "lv_conf.h"
    text = conf.read_text(encoding="utf-8")
    disabled = "#define LV_USE_FREETYPE 0"
    enabled = "#define LV_USE_FREETYPE 1"
    if disabled in text:
        conf.write_text(text.replace(disabled, enabled, 1), encoding="utf-8")
        log("MaixCDK: enabled LV_USE_FREETYPE")
        changed += 1
    elif enabled not in text:
        raise RuntimeError(f"LV_USE_FREETYPE not found in {conf}")

    # freetype 2.13.2 declares cmake_minimum_required(VERSION 2.8.12),
    # which CMake 4 rejects outright.  Allow the policy fallback.
    freetype_cmake = (
        sdk / "components" / "3rd_party" / "freetype" / "CMakeLists.txt"
    )
    text = freetype_cmake.read_text(encoding="utf-8")
    policy = "-DCMAKE_POLICY_VERSION_MINIMUM=3.5"
    if policy not in text:
        needle = "cmake -DCMAKE_POSITION_INDEPENDENT_CODE=ON"
        if needle not in text:
            raise RuntimeError(
                f"freetype CMake command not found in {freetype_cmake}"
            )
        text = text.replace(
            needle, "cmake " + policy + " -DCMAKE_POSITION_INDEPENDENT_CODE=ON", 1
        )
        freetype_cmake.write_text(text, encoding="utf-8")
        log("MaixCDK: freetype CMake policy compatibility for CMake 4")
        changed += 1

    cmake = sdk / "components" / "3rd_party" / "lvgl" / "CMakeLists.txt"
    text = cmake.read_text(encoding="utf-8")
    requirement = "list(APPEND ADD_REQUIREMENTS freetype)"
    if requirement not in text:
        anchor = "list(APPEND ADD_REQUIREMENTS rlottie)"
        if anchor not in text:
            raise RuntimeError(f"LVGL requirement anchor not found in {cmake}")
        text = text.replace(anchor, anchor + "\n" + requirement, 1)
        cmake.write_text(text, encoding="utf-8")
        log("MaixCDK: linked freetype into the LVGL component")
        changed += 1

    return changed


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("usage: patch_maixcdk.py <path-to-MaixCDK>")
    print("changes:", enable_freetype(sys.argv[1]))
