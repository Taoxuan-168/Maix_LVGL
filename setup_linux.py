"""Build a desktop Linux (SDL) wheel from the prebuilt extension.

This does not build LVGL; run ``tools/regenerate_linux_binding.py`` and compile
``linux/build_lvgl/liblvgl.so`` + ``linux/binding/lvgl*.so`` first (see
``docs/README.md``).  The prebuilt files are staged in ``linux/wheel/``.
"""
from pathlib import Path
import re

from setuptools import Distribution, setup
from setuptools.command.build_ext import build_ext

try:
    from setuptools.command.bdist_wheel import bdist_wheel as _bdist_wheel
except ImportError:  # older setuptools
    from wheel.bdist_wheel import bdist_wheel as _bdist_wheel

ROOT = Path(__file__).resolve().parent
WHEEL_PKG = ROOT / "linux" / "wheel" / "maix_lvgl"


def _version() -> str:
    text = (ROOT / "maix_lvgl" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'^__version__\s*=\s*"([^"]+)"', text, re.M)
    if not match:
        raise SystemExit("cannot find __version__ in maix_lvgl/__init__.py")
    return match.group(1)


class BinaryDistribution(Distribution):
    def has_ext_modules(self):
        return True


class NoopBuildExt(build_ext):
    """The extension is prebuilt and staged in linux/wheel/maix_lvgl."""

    def run(self):
        if not list(WHEEL_PKG.glob("lvgl*.so")):
            raise SystemExit(
                "prebuilt Linux extension missing; build it first (see docs/README.md)"
            )


class LinuxWheel(_bdist_wheel):
    def finalize_options(self):
        super().finalize_options()
        self.plat_name = "linux_x86_64"
        self.plat_name_supplied = True


setup(
    name="maix-lvgl",
    version=_version(),
    description=(
        "LVGL 9.1 bindings for MaixPy and desktop Linux (SDL window)"
    ),
    long_description=(ROOT / "README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    author="Sipeed",
    license="MIT",
    license_files=["LICENSE"],
    python_requires=">=3.11",
    packages=["maix_lvgl"],
    package_dir={"maix_lvgl": "linux/wheel/maix_lvgl"},
    package_data={"maix_lvgl": ["*.so", "dl_lib/*.so*"]},
    include_package_data=True,
    ext_modules=[],
    cmdclass={"build_ext": NoopBuildExt, "bdist_wheel": LinuxWheel},
    distclass=BinaryDistribution,
)
