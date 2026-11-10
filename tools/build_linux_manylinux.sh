#!/usr/bin/env bash
# Build the Linux wheel inside a manylinux_2_28 container.
#
# Run on the host:
#   docker run --rm -v "$PWD/..:/src" -w /src/maix_lvgl \
#       quay.io/pypa/manylinux_2_28_x86_64 \
#       bash tools/build_linux_manylinux.sh
#
# Output: dist/manylinux/maix_lvgl-*-manylinux_2_28_x86_64.whl
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
ROOT="$(pwd)"
PY=/opt/python/cp313-cp313/bin/python
PYINC="$($PY -c 'import sysconfig; print(sysconfig.get_paths()["include"])')"
EXT="$($PY -c 'import sysconfig; print(sysconfig.get_config_var("EXT_SUFFIX"))')"
LVGL="${LVGL_SOURCE:-/src/MaixCDK/dl/extracted/lvgl_srcs/lvgl}"

echo "== installing SDL2 development files"
dnf install -y SDL2-devel >/tmp/dnf_sdl2.log 2>&1
sdl2-config --version

SDL_CFLAGS="$(sdl2-config --cflags)"
SDL_LIBS="$(sdl2-config --libs)"

echo "== compiling LVGL"
rm -rf linux/build_lvgl
mkdir -p linux/build_lvgl
gcc -shared -fPIC -O2 -DLV_CONF_INCLUDE_SIMPLE \
    -I linux/binding -I "$LVGL" $SDL_CFLAGS \
    $(find "$LVGL/src" -name '*.c' ! -path '*/neon/*') \
    -o linux/build_lvgl/liblvgl.so \
    $SDL_LIBS -lpthread -lm -ldl

echo "== compiling CPython extension"
gcc -shared -fPIC -O2 -Wno-incompatible-pointer-types \
    -DLV_CONF_INCLUDE_SIMPLE -DLV_CPYTHON_BUILD \
    -I linux/binding -I runtime -I "$(dirname "$LVGL")" -I "$PYINC" \
    $SDL_CFLAGS \
    linux/binding/lvgl_python.c runtime/lvpy_runtime.c \
    -L linux/build_lvgl -llvgl \
    $SDL_LIBS -lpthread -lm -ldl \
    -Wl,-rpath,'$ORIGIN/dl_lib' \
    -o "linux/binding/lvgl${EXT}"

echo "== staging"
rm -rf linux/wheel
mkdir -p linux/wheel/maix_lvgl/dl_lib
cp maix_lvgl/__init__.py maix_lvgl/linux_driver.py linux/wheel/maix_lvgl/
cp linux/binding/lvgl*.so linux/wheel/maix_lvgl/
cp linux/build_lvgl/liblvgl.so linux/wheel/maix_lvgl/dl_lib/

echo "== building linux_x86_64 wheel"
$PY -m pip install -q auditwheel setuptools wheel
$PY setup_linux.py bdist_wheel

echo "== repairing to manylinux_2_28"
rm -rf dist/manylinux
mkdir -p dist/manylinux
export LD_LIBRARY_PATH="$ROOT/linux/build_lvgl:${LD_LIBRARY_PATH:-}"
$PY -m auditwheel repair dist/maix_lvgl-*-linux_x86_64.whl -w dist/manylinux

echo
ls -lh dist/manylinux/*.whl
