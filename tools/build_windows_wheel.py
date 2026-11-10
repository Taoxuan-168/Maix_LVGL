"""Build a Windows win_amd64 wheel from the cross-compiled extension.

The extension is compiled with mingw-w64 and links ``python313.dll`` and
``SDL2.dll``.  setuptools' bdist_wheel refuses win_amd64 on a Linux host, so the
wheel is assembled directly (METADATA/WHEEL/RECORD).
"""
import base64
import hashlib
import os
import re
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION = re.search(
    r'^__version__\s*=\s*"([^"]+)"',
    (ROOT / "maix_lvgl" / "__init__.py").read_text(encoding="utf-8"),
    re.M,
).group(1)
STAGE = ROOT / "windows" / "wheel"
PKG = STAGE / "maix_lvgl"
DIST = ROOT / "dist"
WHEEL_NAME = f"maix_lvgl-{VERSION}-cp313-cp313-win_amd64.whl"
PREFIX = f"maix_lvgl-{VERSION}.dist-info"
DIST_INFO = STAGE / PREFIX
PYD = ROOT / "windows" / "binding" / "lvgl.cp313-win_amd64.pyd"
SDL_DLL = Path(
    os.environ.get(
        "WIN_SDL_DLL",
        "/tmp/win_deps/sdl2/SDL2-2.32.10/x86_64-w64-mingw32/bin/SDL2.dll",
    )
)


def _readme_for_pypi() -> str:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    raw = "https://raw.githubusercontent.com/Taoxuan-168/Maix_LVGL/main"
    blob = "https://github.com/Taoxuan-168/Maix_LVGL/blob/main"
    text = re.sub(
        r"(!\[[^\]]*\]\()(docs|examples)/([^)]+)\)",
        lambda m: f"{m.group(1)}{raw}/{m.group(2)}/{m.group(3)})",
        text,
    )
    text = re.sub(
        r"(\[[^\]]*\]\()(docs|examples)/([^)]+)\)",
        lambda m: f"{m.group(1)}{blob}/{m.group(2)}/{m.group(3)})",
        text,
    )
    text = text.replace("](README_ZH.md)", f"]({blob}/README_ZH.md)")
    return text


def _metadata() -> str:
    return (
        "Metadata-Version: 2.4\n"
        "Name: maix-lvgl\n"
        f"Version: {VERSION}\n"
        "Summary: LVGL 9.1 bindings for MaixPy and desktop Linux (SDL window)\n"
        "Home-page: https://github.com/Taoxuan-168/Maix_LVGL\n"
        "Author: Sipeed\n"
        "License: MIT\n"
        "Project-URL: Homepage, https://github.com/Taoxuan-168/Maix_LVGL\n"
        "Project-URL: Documentation, https://github.com/Taoxuan-168/Maix_LVGL#readme\n"
        "Project-URL: Source, https://github.com/Taoxuan-168/Maix_LVGL\n"
        "Project-URL: Issues, https://github.com/Taoxuan-168/Maix_LVGL/issues\n"
        "Project-URL: Releases, https://github.com/Taoxuan-168/Maix_LVGL/releases\n"
        "Keywords: lvgl,maixpy,maixcam,maixcam2,sipeed,gui,embedded,microcontroller\n"
        "Classifier: Development Status :: 4 - Beta\n"
        "Classifier: Intended Audience :: Developers\n"
        "Classifier: Operating System :: POSIX :: Linux\n"
        "Classifier: Programming Language :: C\n"
        "Classifier: Programming Language :: Python :: 3\n"
        "Classifier: Programming Language :: Python :: 3.13\n"
        "Classifier: Topic :: Software Development :: Libraries\n"
        "Requires-Python: >=3.11\n"
        "Description-Content-Type: text/markdown\n"
        "License-File: LICENSE\n"
        "\n"
        + _readme_for_pypi()
    )


def main():
    if not PYD.is_file():
        raise SystemExit(f"missing {PYD}; compile the Windows extension first")
    if not SDL_DLL.is_file():
        raise SystemExit(f"missing {SDL_DLL}")

    if STAGE.exists():
        shutil.rmtree(STAGE)
    PKG.mkdir(parents=True)
    shutil.copy2(ROOT / "maix_lvgl" / "__init__.py", PKG / "__init__.py")
    shutil.copy2(ROOT / "maix_lvgl" / "linux_driver.py", PKG / "linux_driver.py")
    shutil.copy2(PYD, PKG / PYD.name)
    shutil.copy2(SDL_DLL, PKG / "SDL2.dll")

    dist_info = DIST_INFO
    dist_info.mkdir()
    (dist_info / "METADATA").write_text(_metadata(), encoding="utf-8")
    (dist_info / "WHEEL").write_text(
        "Wheel-Version: 1.0\n"
        "Generator: maix_lvgl build\n"
        "Root-Is-Purelib: false\n"
        "Tag: cp313-cp313-win_amd64\n",
        encoding="utf-8",
    )
    licenses = dist_info / "licenses"
    licenses.mkdir()
    shutil.copy2(ROOT / "LICENSE", licenses / "LICENSE")
    (dist_info / "top_level.txt").write_text("maix_lvgl\n", encoding="utf-8")

    DIST.mkdir(exist_ok=True)
    wheel_path = DIST / WHEEL_NAME
    members = []
    for path in sorted(STAGE.rglob("*")):
        if path.is_file() and path.name != "RECORD":
            members.append((path.relative_to(STAGE).as_posix(), path.read_bytes()))

    record_lines = []
    with zipfile.ZipFile(wheel_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in members:
            zf.writestr(name, data)
            digest = base64.urlsafe_b64encode(
                hashlib.sha256(data).digest()
            ).rstrip(b"=").decode("ascii")
            record_lines.append(f"{name},sha256={digest},{len(data)}")
        record_lines.append(f"{PREFIX}/RECORD,,")
        zf.writestr(f"{PREFIX}/RECORD", "\n".join(record_lines) + "\n")

    print(wheel_path)


if __name__ == "__main__":
    main()
