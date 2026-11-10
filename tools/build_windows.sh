#!/usr/bin/env bash
# Cross-compile the Windows x86_64 wheel on Linux with mingw-w64.
#
# Prerequisites:
#   - x86_64-w64-mingw32-gcc (apt install mingw-w64)
#   - Python 3.13 for Windows headers/libs (WIN_PY_DIR)
#   - SDL2 MinGW x86_64 development package (WIN_SDL_DIR)
#
# Example:
#   WIN_PY_DIR=/opt/win-python/tools \
#   WIN_SDL_DIR=/opt/SDL2/x86_64-w64-mingw32 \
#   tools/build_windows.sh
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

WIN_PY_DIR="${WIN_PY_DIR:-/tmp/win_deps/python/tools}"
WIN_SDL_DIR="${WIN_SDL_DIR:-/tmp/win_deps/sdl2/SDL2-2.32.10/x86_64-w64-mingw32}"
export WIN_SDL_DLL="$WIN_SDL_DIR/bin/SDL2.dll"

for f in "$WIN_PY_DIR/include/Python.h" "$WIN_PY_DIR/libs/python313.lib" \
         "$WIN_SDL_DIR/include/SDL2/SDL.h" "$WIN_SDL_DIR/lib/libSDL2.dll.a" \
         "$WIN_SDL_DLL"; do
    if [ ! -f "$f" ]; then
        echo "error: missing $f" >&2
        exit 1
    fi
done

lvgl="$(python3 - <<'PY'
import sys
sys.path.insert(0, "tools")
import maixcdk_lvgl as mk
sdk = mk.find_maixcdk()
print(mk.ensure_lvgl_source(sdk, mk.lvgl_version(sdk)))
PY
)"
lvgl_parent="$(dirname "$lvgl")"

if [ ! -f windows/binding/lvgl_python.c ]; then
    echo "== generating Windows binding"
    python3 tools/regenerate_windows_binding.py
fi

echo "== compiling Windows extension"
mkdir -p windows/build
x86_64-w64-mingw32-gcc -shared -O2 -Wno-incompatible-pointer-types \
    -o windows/binding/lvgl.cp313-win_amd64.pyd \
    -DLV_CONF_INCLUDE_SIMPLE -DLV_CPYTHON_BUILD \
    -I windows/binding -I runtime -I "$lvgl_parent" \
    -I "$WIN_PY_DIR/include" -I "$WIN_SDL_DIR/include" \
    windows/binding/lvgl_python.c runtime/lvpy_runtime.c \
    $(find "$lvgl/src" -name '*.c' ! -path '*/neon/*') \
    -L "$WIN_SDL_DIR/lib" -lSDL2 \
    -L "$WIN_PY_DIR/libs" -lpython313 \
    -static-libgcc -lmingw32 -luser32 -lgdi32 -lwinmm -lole32 \
    -loleaut32 -luuid -lversion -lsetupapi -lhid \
    -Wl,--enable-auto-import

echo "== building wheel"
python3 tools/build_windows_wheel.py

echo
ls -lh dist/maix_lvgl-*-win_amd64.whl
