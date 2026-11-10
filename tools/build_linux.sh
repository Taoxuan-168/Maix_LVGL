#!/usr/bin/env bash
# Build the desktop Linux (SDL) wheel for x86_64.
#
# Requirements: gcc, pkg-config, libsdl2-dev, Python headers, MaixCDK with the
# LVGL source tree.  Run from the repository root:
#
#   tools/build_linux.sh
#
# Output: dist/maix_lvgl-<version>-cp3xx-cp3xx-linux_x86_64.whl
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

if ! pkg-config --exists sdl2; then
    echo "error: SDL2 development files not found (apt install libsdl2-dev)" >&2
    exit 1
fi

ext_suffix="$(python3 -c 'import sysconfig; print(sysconfig.get_config_var("EXT_SUFFIX"))')"
python_include="$(python3 -c 'import sysconfig; print(sysconfig.get_paths()["include"])')"

lvgl="$(python3 - <<'PY'
import sys
sys.path.insert(0, "tools")
import maixcdk_lvgl as mk
sdk = mk.find_maixcdk()
print(mk.ensure_lvgl_source(sdk, mk.lvgl_version(sdk)))
PY
)"
lvgl_parent="$(dirname "$lvgl")"

if [ ! -f linux/binding/lvgl_python.c ]; then
    echo "== generating Linux binding"
    python3 tools/regenerate_linux_binding.py
fi

if [ ! -f linux/build_lvgl/liblvgl.so ]; then
    echo "== building LVGL shared library"
    mkdir -p linux/build_lvgl
    gcc -shared -fPIC -O2 -DLV_CONF_INCLUDE_SIMPLE \
        -I linux/binding -I "$lvgl" \
        $(pkg-config --cflags sdl2) \
        $(find "$lvgl/src" -name '*.c' ! -path '*/neon/*') \
        -o linux/build_lvgl/liblvgl.so \
        $(pkg-config --libs sdl2) -lpthread -lm -ldl
fi

echo "== building CPython extension"
gcc -shared -fPIC -O2 -Wno-incompatible-pointer-types \
    -DLV_CONF_INCLUDE_SIMPLE -DLV_CPYTHON_BUILD \
    -I linux/binding -I runtime -I "$lvgl_parent" -I "$python_include" \
    $(pkg-config --cflags sdl2) \
    linux/binding/lvgl_python.c runtime/lvpy_runtime.c \
    -L linux/build_lvgl -llvgl \
    $(pkg-config --libs sdl2) -lpthread -lm -ldl \
    -Wl,-rpath,'$ORIGIN/dl_lib' \
    -o "linux/binding/lvgl${ext_suffix}"

echo "== staging wheel files"
rm -rf linux/wheel
mkdir -p linux/wheel/maix_lvgl/dl_lib
cp maix_lvgl/__init__.py maix_lvgl/linux_driver.py linux/wheel/maix_lvgl/
cp linux/binding/lvgl*.so linux/wheel/maix_lvgl/
cp linux/build_lvgl/liblvgl.so linux/wheel/maix_lvgl/dl_lib/

echo "== building wheel"
python3 setup_linux.py bdist_wheel

echo
echo "wheel:"
ls -1 dist/maix_lvgl-*-linux_x86_64.whl
