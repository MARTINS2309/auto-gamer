"""
Game Launcher - Start mGBA with the ROM.
"""

import subprocess
import time
import ctypes
from pathlib import Path
from typing import Optional

from logic.paths import BASE_DIR

user32 = ctypes.windll.user32

# Paths
MGBA_DIR = BASE_DIR / "mGBA"
MGBA_EXE = MGBA_DIR / "mGBA.exe"
LUA_SCRIPT = MGBA_DIR / "scripts" / "ai_control.lua"
ROM_DIR = BASE_DIR / "docs"  # ROMs stored in docs


def find_rom() -> Optional[Path]:
    """Find a GBA ROM file."""
    for pattern in ["*.gba", "*.GBA", "*.zip"]:
        roms = list(ROM_DIR.glob(pattern))
        if roms:
            return roms[0]
    # Also check mGBA directory
    for pattern in ["*.gba", "*.GBA"]:
        roms = list(MGBA_DIR.glob(pattern))
        if roms:
            return roms[0]
    return None


def find_mgba_window() -> Optional[int]:
    """Find mGBA window handle. Title must start with 'mGBA'."""
    result = []

    def callback(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd) + 1
            buf = ctypes.create_unicode_buffer(length)
            user32.GetWindowTextW(hwnd, buf, length)
            title = buf.value.strip()
            # mGBA window titles start with "mGBA" (e.g. "mGBA - Pokemon Red")
            if title.lower().startswith("mgba"):
                result.append((hwnd, title))
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    user32.EnumWindows(WNDENUMPROC(callback), 0)

    if result:
        # Prefer longer titles (more specific)
        result.sort(key=lambda x: len(x[1]), reverse=True)
        return result[0][0]
    return None


def is_mgba_running() -> bool:
    """Check if mGBA is already running."""
    return find_mgba_window() is not None


def launch_mgba(rom_path: Path = None, wait: bool = True, timeout: float = 10.0) -> Optional[int]:
    """
    Launch mGBA with the specified ROM.

    Returns window handle if successful, None otherwise.
    """
    if not MGBA_EXE.exists():
        print(f"mGBA not found at {MGBA_EXE}")
        return None

    # Check if already running
    hwnd = find_mgba_window()
    if hwnd:
        print("mGBA already running")
        return hwnd

    # Find ROM if not specified
    if rom_path is None:
        rom_path = find_rom()
        if rom_path is None:
            print("No ROM found")
            return None

    print(f"Launching mGBA with {rom_path.name}...")

    # Build command with Lua script if available
    cmd = [str(MGBA_EXE)]
    if LUA_SCRIPT.exists():
        cmd.extend(["--script", str(LUA_SCRIPT)])
    cmd.append(str(rom_path))

    # Launch
    try:
        subprocess.Popen(cmd, cwd=str(MGBA_DIR))
    except Exception as e:
        print(f"Failed to launch mGBA: {e}")
        return None

    if not wait:
        return None

    # Wait for window
    start = time.time()
    while time.time() - start < timeout:
        hwnd = find_mgba_window()
        if hwnd:
            print(f"mGBA ready (hwnd={hwnd})")
            time.sleep(0.5)  # Let it fully initialize
            return hwnd
        time.sleep(0.2)

    print("Timeout waiting for mGBA window")
    return None


class GameLauncher:
    """Manages game launching and window tracking."""

    def __init__(self):
        self.hwnd: Optional[int] = None
        self.process: Optional[subprocess.Popen] = None

    def launch(self, rom_path: Path = None) -> bool:
        """Launch the game. Returns True if successful."""
        self.hwnd = launch_mgba(rom_path)
        return self.hwnd is not None

    def ensure_running(self) -> bool:
        """Ensure mGBA is running, launch if needed."""
        if is_mgba_running():
            self.hwnd = find_mgba_window()
            return True
        return self.launch()

    @property
    def window_handle(self) -> Optional[int]:
        """Get current window handle."""
        if self.hwnd and user32.IsWindow(self.hwnd):
            return self.hwnd
        # Try to find it again
        self.hwnd = find_mgba_window()
        return self.hwnd
