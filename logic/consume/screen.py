"""
Screen Capture - Get screenshots from mGBA.

Two modes:
1. Socket (preferred): Uses emulator's screenshot command - works minimized, pixel-perfect
2. MSS fallback: Window capture - requires visible window
"""

import ctypes
import tempfile
import os
from ctypes import wintypes
from typing import Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass
from pathlib import Path

import mss
from PIL import Image

if TYPE_CHECKING:
    from logic.act.input import InputSender


user32 = ctypes.windll.user32


@dataclass
class CaptureRegion:
    left: int
    top: int
    width: int
    height: int

    def as_mss_dict(self) -> dict:
        return {"left": self.left, "top": self.top, "width": self.width, "height": self.height}


class ScreenCapture:
    """
    Captures game screen from mGBA.

    Prefers socket-based capture (emulator screenshot command) when available.
    Falls back to window capture via mss if socket not connected.
    """

    CHROME_TOP = 75  # Title bar + menu
    CHROME_BORDER = 1

    def __init__(self):
        self._sct: Optional[mss.mss] = None
        self.hwnd: Optional[int] = None
        self._sender: Optional['InputSender'] = None
        self._temp_dir = Path(tempfile.gettempdir()) / "auto-gamer"
        self._temp_dir.mkdir(exist_ok=True)
        self._frame_count = 0

    def set_sender(self, sender: 'InputSender'):
        """Set the input sender for socket-based capture."""
        self._sender = sender

    @property
    def sct(self) -> mss.mss:
        if self._sct is None:
            self._sct = mss.mss()
        return self._sct

    @property
    def use_socket(self) -> bool:
        """Check if socket capture is available."""
        return self._sender is not None and self._sender.use_socket

    def find_window(self, title: str = "mGBA") -> Optional[int]:
        """Find mGBA window. Title must start with 'mGBA' to avoid false matches."""
        results = []

        def callback(hwnd, _):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd) + 1
                buf = ctypes.create_unicode_buffer(length)
                user32.GetWindowTextW(hwnd, buf, length)
                window_title = buf.value.strip()
                # mGBA window titles start with "mGBA" (e.g. "mGBA - Pokemon Red")
                if window_title.lower().startswith(title.lower()):
                    results.append((hwnd, window_title))
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        user32.EnumWindows(WNDENUMPROC(callback), 0)

        if results:
            # Prefer longer titles (more specific matches)
            results.sort(key=lambda x: len(x[1]), reverse=True)
            self.hwnd = results[0][0]
            return self.hwnd
        self.hwnd = None
        return None

    def is_window_valid(self, hwnd: Optional[int] = None) -> bool:
        """Check if a window handle is still valid and visible."""
        hwnd = hwnd or self.hwnd
        if not hwnd:
            return False
        return bool(user32.IsWindow(hwnd) and user32.IsWindowVisible(hwnd))

    def get_region(self) -> Optional[CaptureRegion]:
        """Get capture region excluding window chrome."""
        if not self.hwnd:
            self.find_window()
        if not self.hwnd:
            return None

        rect = wintypes.RECT()
        if not user32.GetWindowRect(self.hwnd, ctypes.byref(rect)):
            return None

        return CaptureRegion(
            left=rect.left + self.CHROME_BORDER,
            top=rect.top + self.CHROME_TOP,
            width=rect.right - rect.left - self.CHROME_BORDER * 2,
            height=rect.bottom - rect.top - self.CHROME_TOP - self.CHROME_BORDER
        )

    def capture(self) -> Optional[Image.Image]:
        """
        Capture game screen as PIL Image.

        Uses socket screenshot if available (works minimized, pixel-perfect).
        Falls back to window capture via mss.
        """
        # Try socket-based capture first (preferred)
        if self.use_socket:
            img = self._capture_via_socket()
            if img:
                return img

        # Fallback to window capture
        return self._capture_via_mss()

    def _capture_via_socket(self) -> Optional[Image.Image]:
        """Capture using emulator's screenshot command."""
        if not self._sender:
            return None

        try:
            # Use a rotating temp file to avoid file locking issues
            self._frame_count = (self._frame_count + 1) % 10
            temp_path = self._temp_dir / f"frame_{self._frame_count}.png"

            # Request screenshot from emulator
            result_path = self._sender.screenshot(str(temp_path))
            if result_path and os.path.exists(result_path):
                img = Image.open(result_path)
                img.load()  # Force load to release file handle
                return img.copy()  # Return copy to allow file deletion
        except Exception as e:
            pass  # Fall through to return None

        return None

    def _capture_via_mss(self) -> Optional[Image.Image]:
        """Capture using mss window grab (fallback)."""
        region = self.get_region()
        if not region:
            return None

        try:
            shot = self.sct.grab(region.as_mss_dict())
            return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        except Exception:
            return None

    def cleanup(self):
        """Clean up temporary files."""
        try:
            for f in self._temp_dir.glob("frame_*.png"):
                f.unlink(missing_ok=True)
        except Exception:
            pass
