"""LVGL SDL display driver for desktop Linux.

Used when MaixPy (``maix``) is not available, for example on a normal
x86_64 Linux desktop / WSL.  The window and mouse/keyboard input are provided
by LVGL's SDL driver.
"""
from __future__ import annotations

import lvgl as lv


class LinuxDriver:
    """Create an SDL window and pointer/keyboard input devices."""

    def __init__(self, width=640, height=480):
        self.width = int(width or 640)
        self.height = int(height or 480)
        self._disp = lv.sdl_window_create(self.width, self.height)
        self._disp.set_default()
        try:
            lv.sdl_window_set_title(self._disp, "maix_lvgl")
        except Exception:
            pass
        self._mouse = lv.sdl_mouse_create()
        self._keyboard = lv.sdl_keyboard_create()
        self._mousewheel = lv.sdl_mousewheel_create()
        # MaixPy's DisplayDriver exposes the frame buffer; the SDL driver owns
        # the window instead.  Keep the attribute for API compatibility.
        self._buffer = None

    def deinit(self):
        for name in ("_mousewheel", "_keyboard", "_mouse"):
            indev = getattr(self, name, None)
            if indev is not None:
                try:
                    indev.delete()
                except Exception:
                    pass
                setattr(self, name, None)
        if self._disp is not None:
            try:
                self._disp.delete()
            except Exception:
                pass
            self._disp = None
