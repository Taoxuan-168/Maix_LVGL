"""Build maix_lvgl wheels through MaixCDK's project.py.

Standard MaixCDK project layout: ``main/`` is the entry component and
``components/lvgl_binding`` holds the LVGL CPython extension.

Usage::

    python3 setup.py bdist_wheel --board maixcam2   # default
    python3 setup.py bdist_wheel --board maixcam    # RISC-V, Python 3.11

``--board`` (or ``-b``, ``MAIX_BOARD``) selects the MaixCDK platform.  The
MaixCAM build requires a host Python 3.11 (``python3.11 setup.py ...``); the
MaixCAM2 build requires a host Python 3.13.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from setuptools import Distribution, setup
from setuptools.command.build_ext import build_ext

try:
    from setuptools.command.bdist_wheel import bdist_wheel as _bdist_wheel
except ImportError:  # older setuptools
    from wheel.bdist_wheel import bdist_wheel as _bdist_wheel

ROOT = Path(__file__).resolve().parent
GITHUB_URL = "https://github.com/Taoxuan-168/Maix_LVGL"
RAW_URL = "https://raw.githubusercontent.com/Taoxuan-168/Maix_LVGL/main"


def _read_version() -> str:
    """Read the version from the package so it has a single source."""
    text = (ROOT / "maix_lvgl" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'^__version__\s*=\s*"([^"]+)"', text, re.M)
    if not match:
        raise SystemExit("cannot find __version__ in maix_lvgl/__init__.py")
    return match.group(1)


def _readme_for_pypi() -> str:
    """Turn README-relative links into absolute ones for the PyPI page.

    PyPI renders the description outside the repository, so ``docs/...`` and
    ``examples/...`` links would be dead there.  Images must point at the raw
    files; other links point at the GitHub blob view.
    """
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    text = re.sub(
        r"(!\[[^\]]*\]\()(docs|examples)/([^)]+)\)",
        lambda m: f"{m.group(1)}{RAW_URL}/{m.group(2)}/{m.group(3)})",
        text,
    )
    text = re.sub(
        r"(\[[^\]]*\]\()(docs|examples)/([^)]+)\)",
        lambda m: f"{m.group(1)}{GITHUB_URL}/blob/main/{m.group(2)}/{m.group(3)})",
        text,
    )
    text = text.replace(
        "](README_ZH.md)", f"]({GITHUB_URL}/blob/main/README_ZH.md)"
    )
    return text


BOARD_INFO = {
    "maixcam": {
        "host_python": (3, 11),
        "python_tag": "cp311",
        "platform": "linux_riscv64",
        # Python 3.11 on musl accepts the generic .so suffix.
        "ext_name": "lvgl.so",
        "config": "configs/config_platform_maixcam.mk",
    },
    "maixcam2": {
        "host_python": (3, 13),
        "python_tag": "cp313",
        "platform": "manylinux2014_aarch64",
        "ext_name": "lvgl.cpython-313-aarch64-linux-gnu.so",
        "config": "configs/config_platform_maixcam2.mk",
    },
}


def _extract_board(argv: list[str]) -> str:
    """Consume --board/-b/--board= or a positional board from argv."""
    board = os.environ.get("MAIX_BOARD", "maixcam2")
    cleaned = []
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg in ("--board", "-b"):
            if index + 1 >= len(argv):
                raise SystemExit("--board requires maixcam or maixcam2")
            board = argv[index + 1]
            index += 2
            continue
        if arg.startswith("--board="):
            board = arg.split("=", 1)[1]
            index += 1
            continue
        if arg in BOARD_INFO:
            board = arg
            index += 1
            continue
        cleaned.append(arg)
        index += 1
    argv[:] = cleaned
    if board not in BOARD_INFO:
        raise SystemExit(
            f"unknown board '{board}', expected one of: {', '.join(BOARD_INFO)}"
        )
    return board


BOARD = _extract_board(sys.argv)
BOARD_CFG = BOARD_INFO[BOARD]
PY_TAG = BOARD_CFG["python_tag"]
PLATFORM = BOARD_CFG["platform"]
EXT_NAME = BOARD_CFG["ext_name"]
CONFIG_FILE = BOARD_CFG["config"]
HOST_PYTHON = BOARD_CFG["host_python"]
BUILT_LIB = ROOT / "build" / "lvgl_binding" / "liblvgl_binding.so"
BUILT_DL_LIB = ROOT / "build" / "dl_lib"
BUILD_MARKER = ROOT / "build" / ".maix_lvgl_board"


class BinaryDistribution(Distribution):
    def has_ext_modules(self):
        return True


def _check_host_python():
    required = HOST_PYTHON
    if sys.version_info[:2] != required:
        raise SystemExit(
            f"{BOARD} requires host Python {required[0]}.{required[1]} "
            f"(current: {sys.version_info.major}.{sys.version_info.minor}).\n"
            f"Run: python{required[0]}.{required[1]} setup.py bdist_wheel "
            f"--board {BOARD}"
        )


def _check_cmake():
    try:
        out = subprocess.check_output(["cmake", "--version"], text=True)
    except (OSError, subprocess.CalledProcessError):
        raise SystemExit("cmake is required (MaixCDK builds with CMake).")
    match = re.search(r"version (\d+)\.", out)
    if match and int(match.group(1)) >= 4:
        print(
            "-- NOTE: cmake 4.x is patched for freetype by "
            "tools/patch_maixcdk.py; cmake 3.x is also supported.",
            file=sys.stderr,
        )


def _check_pycparser():
    try:
        import pycparser  # noqa: F401
    except ImportError:
        raise SystemExit(
            "pycparser is required to generate the LVGL binding. "
            "Install it with: python3 -m pip install 'pycparser>=3.0'"
        )


def _ensure_build_dir(skip_build: bool):
    """Use one MaixCDK build directory per board; clean on board switch."""
    current = None
    if BUILD_MARKER.is_file():
        try:
            current = BUILD_MARKER.read_text(encoding="utf-8").strip()
        except OSError:
            current = None
    if current == BOARD:
        return
    if skip_build:
        raise SystemExit(
            f"build/ was produced for {current or 'another board'}, not {BOARD}. "
            "Run without --skip-build to rebuild."
        )
    if (ROOT / "build").exists():
        shutil.rmtree(ROOT / "build")
    BUILD_MARKER.parent.mkdir(parents=True, exist_ok=True)
    BUILD_MARKER.write_text(BOARD, encoding="utf-8")


class MaixCDKBuildExt(build_ext):
    """Build through MaixCDK, then stage the extension for the wheel."""

    def run(self):
        if "--skip-build" not in sys.argv:
            sdk = os.environ.get("MAIXCDK_PATH")
            if not sdk:
                raise SystemExit(
                    "Please set MAIXCDK_PATH to the MaixCDK checkout, e.g.\n"
                    "  export MAIXCDK_PATH=/path/to/MaixCDK"
                )
            _check_host_python()
            _check_cmake()
            _check_pycparser()
            _ensure_build_dir(False)

            # The repository does not track generated binding files; create
            # them (from MaixCDK's LVGL source) before CMake configures.
            gen = [
                sys.executable,
                str(ROOT / "tools" / "regenerate_binding.py"),
                "--sdk-path",
                sdk,
            ]
            print("-- generating LVGL binding from MaixCDK source")
            subprocess.check_call(gen, cwd=ROOT)

            docs = [
                sys.executable,
                str(ROOT / "tools" / "gen_api_docs.py"),
                "--pyi",
                str(ROOT / "binding" / "lvgl.pyi"),
                "--out",
                str(ROOT / "docs" / "api"),
            ]
            print("-- generating API documentation")
            subprocess.check_call(docs, cwd=ROOT)

            cmd = [
                sys.executable,
                "project.py",
                "build",
                "-p",
                BOARD,
                "--release",
                "--config-file",
                CONFIG_FILE,
            ]
            print("-- building with MaixCDK:", " ".join(cmd))
            subprocess.check_call(cmd, cwd=ROOT)
        else:
            _check_host_python()
            _ensure_build_dir(True)

        if not BUILT_LIB.is_file():
            raise SystemExit(
                f"MaixCDK build did not produce {BUILT_LIB}. "
                f"Run `python3 project.py build -p {BOARD} --release` to see why."
            )

        pkg_dir = Path(self.build_lib) / "maix_lvgl"
        pkg_dir.mkdir(parents=True, exist_ok=True)
        # MaixCDK's project.py build cleans build/, which removes build_py's
        # output; copy the Python sources again so the wheel is complete.
        for source in (ROOT / "maix_lvgl").glob("*.py"):
            shutil.copy2(source, pkg_dir / source.name)
        shutil.copy2(BUILT_LIB, pkg_dir / EXT_NAME)

        dl_dir = pkg_dir / "dl_lib"
        dl_dir.mkdir(exist_ok=True)
        datachannel = BUILT_DL_LIB / "libdatachannel.so"
        if datachannel.is_file():
            shutil.copy2(datachannel, dl_dir / "libdatachannel.so")


class MaixLvglWheel(_bdist_wheel):
    def finalize_options(self):
        super().finalize_options()
        if not getattr(self, "plat_name_supplied", False):
            self.plat_name = PLATFORM
            self.plat_name_supplied = True
        # bdist_wheel ignores python_tag/abi_tag for non-pure wheels and uses
        # the running interpreter instead.  Build each board with its own host
        # Python (maixcam: 3.11, maixcam2: 3.13); _check_host_python enforces it.

    def run(self):
        if self.skip_build:
            # bdist_wheel --skip-build skips the whole build command, including
            # build_py, which would produce a wheel without maix_lvgl/*.py.
            # Only MaixCDK's project.py build should be skipped, so build the
            # Python package and stage the prebuilt extension here.
            self.run_command("build_py")
            self.run_command("build_ext")
        super().run()


setup(
    name="maix-lvgl",
    version=_read_version(),
    description=(
        "LVGL bindings for MaixPy (MaixCAM / MaixCAM2), generated from "
        "MaixCDK's LVGL source with the omnipython-lvgl generator."
    ),
    long_description=_readme_for_pypi(),
    long_description_content_type="text/markdown",
    author="Sipeed",
    url=GITHUB_URL,
    license="MIT",
    license_files=["LICENSE"],
    keywords=[
        "lvgl",
        "maixpy",
        "maixcam",
        "maixcam2",
        "sipeed",
        "gui",
        "embedded",
        "microcontroller",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: C",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.13",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: User Interfaces",
    ],
    project_urls={
        "Homepage": GITHUB_URL,
        "Documentation": GITHUB_URL + "#readme",
        "Source": GITHUB_URL,
        "Issues": GITHUB_URL + "/issues",
        "Releases": GITHUB_URL + "/releases",
    },
    python_requires=">=3.11",
    packages=["maix_lvgl"],
    package_dir={"maix_lvgl": "maix_lvgl"},
    package_data={"maix_lvgl": ["*.so", "dl_lib/*.so*"]},
    include_package_data=True,
    # The extension is cross-compiled by MaixCDK and staged into the package
    # by MaixCDKBuildExt.  No setuptools Extension is declared here, so the
    # wheel metadata does not claim a top-level ``lvgl`` module; the
    # BinaryDistribution class still marks this as a platform wheel.
    ext_modules=[],
    cmdclass={"build_ext": MaixCDKBuildExt, "bdist_wheel": MaixLvglWheel},
    distclass=BinaryDistribution,
)
