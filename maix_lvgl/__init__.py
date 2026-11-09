"""MaixPy + LVGL integration.

``maix_lvgl`` re-exports the generated LVGL bindings (``import lvgl as lv``)
and adds a thin MaixCAM2 backend:

.. code-block:: python

    from maix import app, display, touchscreen
    import maix_lvgl as lv

    lv.init(display.Display(), touchscreen.TouchScreen())

    scr = lv.screen_active()
    btn = lv.button(scr)
    btn.center()
    lv.label(btn).set_text("Hello MaixCAM2")

    while not app.need_exit():
        lv.timer_handler()
        time.sleep(0.005)

    lv.deinit()

The binding is generated from LVGL 9.1.0 (the version pinned by MaixCDK) with
the omnipython-lvgl generator. See README.md for build and regeneration notes.
"""
from __future__ import annotations

import ctypes
import os
import sys
import time

# The LVGL extension is built by MaixCDK's project.py and ships inside this
# package, together with the dynamic libraries MaixCDK's LVGL stack needs
# beyond the system ones (libdatachannel).
_pkg_dir = os.path.dirname(os.path.abspath(__file__))
_dl_dir = os.path.join(_pkg_dir, "dl_lib")
if os.path.isdir(_dl_dir):
    for _name in sorted(os.listdir(_dl_dir)):
        if ".so" in _name:
            try:
                ctypes.CDLL(os.path.join(_dl_dir, _name), mode=ctypes.RTLD_GLOBAL)
            except OSError:
                pass
if _pkg_dir not in sys.path:
    sys.path.insert(0, _pkg_dir)
try:
    import lvgl as _lvgl
finally:
    if _pkg_dir in sys.path:
        sys.path.remove(_pkg_dir)

from .driver import DisplayDriver, TouchDriver

__version__ = "0.1.0"

_display_driver = None
_touch_driver = None
_initialized = False
_last_tick = None


def init(display=None, touchscreen=None, width=None, height=None):
    """Initialize LVGL and attach MaixPy display/touchscreen.

    Args:
        display: a ``maix.display.Display`` instance. When omitted, a display
            is opened in ``FMT_BGRA8888`` using the panel size.
        touchscreen: a ``maix.touchscreen.TouchScreen`` instance. When omitted,
            a touchscreen is opened. Pass ``False`` to run without touch input.
        width/height: panel size used only when opening an internal display.

    Returns:
        The internal ``DisplayDriver``.
    """
    global _display_driver, _touch_driver, _initialized
    if _initialized:
        raise RuntimeError("maix_lvgl is already initialized")

    _lvgl.init()
    global _last_tick
    _last_tick = time.monotonic()
    _display_driver = DisplayDriver(display, width, height)
    if touchscreen is not False:
        _touch_driver = TouchDriver(touchscreen, _display_driver._disp)
    _initialized = True
    return _display_driver


def timer_handler():
    """Advance the LVGL tick and run one timer-handler pass.

    Use this instead of ``lvgl.timer_handler()``: the generated binding
    cannot keep the ``lv_tick_set_cb`` Python callback alive, so the tick is
    advanced here on the main thread.
    """
    global _last_tick
    now = time.monotonic()
    if _last_tick is None:
        _last_tick = now
    delta = int((now - _last_tick) * 1000)
    if delta > 0:
        _lvgl.tick_inc(delta)
        _last_tick = now
    return _lvgl.timer_handler()


def process():
    """Run one LVGL timer-handler pass and return its next delay (ms)."""
    return timer_handler()


def run(fps=60):
    """Run the LVGL loop until MaixPy asks the application to exit."""
    from maix import app

    period = 1.0 / fps
    while not app.need_exit():
        timer_handler()
        time.sleep(period)


def deinit():
    """Stop LVGL and release the display/touchscreen opened by :func:`init`."""
    global _display_driver, _touch_driver, _initialized
    if not _initialized:
        return
    if _touch_driver is not None:
        _touch_driver.deinit()
        _touch_driver = None
    if _display_driver is not None:
        _display_driver.deinit()
        _display_driver = None
    _lvgl.deinit()
    _last_tick = None
    _initialized = False


def anim_set_exec_cb(anim, cb):
    """Attach a Python callback to an animation.

    LVGL's ``lv_anim_set_exec_cb`` takes a bare function pointer without a
    user_data argument, so a Python callback cannot be associated with a
    specific animation (the generated binding used to drop it silently).
    This helper uses ``lv_anim_set_custom_exec_cb`` instead; the callback is
    invoked as ``cb(anim, value)``, where the first argument is the
    ``anim_t`` wrapper rather than the animation variable.
    """
    def _cb(a, value):
        return cb(a, value)

    anim.set_custom_exec_cb(_cb)


class SYMBOL:
    """LVGL built-in symbols (same names as lv.SYMBOL in MicroPython)."""

    BULLET = "\u2022"
    AUDIO = "\uf001"
    VIDEO = "\uf008"
    LIST = "\uf00b"
    OK = "\uf00c"
    CLOSE = "\uf00d"
    POWER = "\uf011"
    SETTINGS = "\uf013"
    HOME = "\uf015"
    DOWNLOAD = "\uf019"
    DRIVE = "\uf01c"
    REFRESH = "\uf021"
    MUTE = "\uf026"
    VOLUME_MID = "\uf027"
    VOLUME_MAX = "\uf028"
    IMAGE = "\uf03e"
    TINT = "\uf043"
    PREV = "\uf048"
    PLAY = "\uf04b"
    PAUSE = "\uf04c"
    STOP = "\uf04d"
    NEXT = "\uf051"
    EJECT = "\uf052"
    LEFT = "\uf053"
    RIGHT = "\uf054"
    PLUS = "\uf067"
    MINUS = "\uf068"
    EYE_OPEN = "\uf06e"
    EYE_CLOSE = "\uf070"
    WARNING = "\uf071"
    SHUFFLE = "\uf074"
    UP = "\uf077"
    DOWN = "\uf078"
    LOOP = "\uf079"
    DIRECTORY = "\uf07b"
    UPLOAD = "\uf093"
    CALL = "\uf095"
    CUT = "\uf0c4"
    COPY = "\uf0c5"
    SAVE = "\uf0c7"
    BARS = "\uf0c9"
    ENVELOPE = "\uf0e0"
    CHARGE = "\uf0e7"
    PASTE = "\uf0ea"
    BELL = "\uf0f3"
    KEYBOARD = "\uf11c"
    GPS = "\uf124"
    FILE = "\uf158"
    WIFI = "\uf1eb"
    BATTERY_FULL = "\uf240"
    BATTERY_3 = "\uf241"
    BATTERY_2 = "\uf242"
    BATTERY_1 = "\uf243"
    BATTERY_EMPTY = "\uf244"
    USB = "\uf287"
    BLUETOOTH = "\uf293"
    TRASH = "\uf2ed"
    EDIT = "\uf304"
    BACKSPACE = "\uf55a"
    SD_CARD = "\uf7c2"
    NEW_LINE = "\uf8a2"


# Re-export every LVGL binding name so ``import maix_lvgl as lv`` behaves like
# ``import lvgl as lv`` (MicroPython-style API).
def __getattr__(name):
    return getattr(_lvgl, name)


def __dir__():
    return sorted(set(globals()) | set(dir(_lvgl)))


__all__ = [n for n in dir(_lvgl) if not n.startswith("_")] + [
    "init",
    "deinit",
    "run",
    "process",
    "timer_handler",
    "anim_set_exec_cb",
    "SYMBOL",
]
