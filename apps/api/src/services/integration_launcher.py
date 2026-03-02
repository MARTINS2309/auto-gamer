"""
Integration Tool Launcher — manages the native gym-retro-integration Qt5
subprocess for building connectors (memory search, scenario editing, save states).

Only one instance at a time.
"""

import configparser
import logging
import os
import shutil
import signal
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# Project root: auto-gamer/
# __file__ = apps/api/src/services/integration_launcher.py → parents[4] = auto-gamer/
PROJECT_ROOT = Path(__file__).resolve().parents[4]
DATA_DIR = PROJECT_ROOT / "data"
CUSTOM_INTEGRATIONS_DIR = DATA_DIR / "custom_integrations"
STDERR_LOG = DATA_DIR / "integration_tool.log"

# Non-canonical → canonical ROM extension mapping.
# The integration tool only recognises the canonical extensions from core JSON files.
_EXT_ALIASES: dict[str, str] = {
    ".smc": ".sfc",   # SNES
    ".bin": ".md",    # Genesis (ambiguous, but .bin is common for Genesis)
    ".gen": ".md",    # Genesis
}


class IntegrationLauncher:
    def __init__(self) -> None:
        self._process: subprocess.Popen | None = None
        self._stderr_file = None
        self._symlink: Path | None = None

    # ------------------------------------------------------------------
    # Binary discovery
    # ------------------------------------------------------------------

    def find_binary(self) -> str | None:
        """Return path to gym-retro-integration binary, or None."""
        # 1. Check packages/stable-retro/build/
        candidate = PROJECT_ROOT / "packages" / "stable-retro" / "build" / "gym-retro-integration"
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)

        # 2. Check PATH
        found = shutil.which("gym-retro-integration")
        if found:
            return found

        return None

    # ------------------------------------------------------------------
    # QSettings pre-configuration
    # ------------------------------------------------------------------

    def _write_qsettings(self) -> None:
        """Write QSettings config so the integration tool uses our data dir."""
        CUSTOM_INTEGRATIONS_DIR.mkdir(parents=True, exist_ok=True)

        conf_path = Path.home() / ".config" / "OpenAI" / "gym-retro-integration.conf"
        conf_path.parent.mkdir(parents=True, exist_ok=True)

        config = configparser.ConfigParser()
        # Preserve existing settings if file exists
        if conf_path.exists():
            config.read(str(conf_path))

        if "paths" not in config:
            config["paths"] = {}
        config["paths"]["data"] = str(CUSTOM_INTEGRATIONS_DIR)

        with open(conf_path, "w") as f:
            config.write(f)

        logger.info("Wrote QSettings: %s (data=%s)", conf_path, CUSTOM_INTEGRATIONS_DIR)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def launch(self, rom_path: str | None = None) -> dict:
        """Start the integration tool, optionally loading a ROM file."""
        if self.is_running():
            return {"status": "already_running", "pid": self._process.pid}

        binary = self.find_binary()
        if not binary:
            return {"status": "binary_not_found", "message": "gym-retro-integration not found. Build it with: cd packages/stable-retro && mkdir -p build && cd build && cmake .. -DBUILD_UI=ON -DBUILD_TESTS=OFF && make gym-retro-integration -j$(nproc)"}

        self._write_qsettings()

        # Build a clean environment for the Qt subprocess
        env = os.environ.copy()

        # Ensure display env vars are present (important on WSL2/WSLg)
        for var in ("DISPLAY", "WAYLAND_DISPLAY", "XDG_RUNTIME_DIR"):
            if var not in env:
                defaults = {
                    "DISPLAY": ":0",
                    "WAYLAND_DISPLAY": "wayland-0",
                    "XDG_RUNTIME_DIR": f"/run/user/{os.getuid()}",
                }
                env[var] = defaults[var]

        # Force system Qt5 plugins — OpenCV (cv2) bundles its own incompatible
        # Qt plugins that cause "Could not load the Qt platform plugin xcb" crashes.
        # QT_QPA_PLATFORM_PLUGIN_PATH takes highest precedence for platform plugins.
        env["QT_PLUGIN_PATH"] = "/usr/lib/x86_64-linux-gnu/qt5/plugins"
        env["QT_QPA_PLATFORM_PLUGIN_PATH"] = "/usr/lib/x86_64-linux-gnu/qt5/plugins/platforms"
        # Remove any venv paths from LD_LIBRARY_PATH to prevent cv2 contamination
        if "LD_LIBRARY_PATH" in env:
            env["LD_LIBRARY_PATH"] = ":".join(
                p for p in env["LD_LIBRARY_PATH"].split(":")
                if ".venv" not in p
            )

        # If the ROM extension isn't canonical, create a temp symlink so the
        # integration tool can identify the correct core.
        self._cleanup_symlink()
        if rom_path:
            ext = Path(rom_path).suffix.lower()
            canonical = _EXT_ALIASES.get(ext)
            if canonical:
                link = DATA_DIR / f"_integration_rom{canonical}"
                link.unlink(missing_ok=True)
                link.symlink_to(rom_path)
                self._symlink = link
                rom_path = str(link)
                logger.info("Created symlink %s -> %s", link, rom_path)

        try:
            # Use DEVNULL for stdout; log stderr to file.
            # PIPE must NOT be used for long-running GUI processes — the buffer
            # fills up and causes the child to block/SIGABRT.
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            self._stderr_file = open(STDERR_LOG, "w")
            cmd = [binary]
            if rom_path:
                cmd.append(rom_path)
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=self._stderr_file,
                env=env,
                start_new_session=True,
            )
            logger.info("Launched gym-retro-integration (pid=%d)", self._process.pid)
            return {"status": "launched", "pid": self._process.pid}
        except Exception as e:
            logger.error("Failed to launch integration tool: %s", e)
            if self._stderr_file:
                self._stderr_file.close()
                self._stderr_file = None
            return {"status": "error", "message": str(e)}

    def status(self) -> dict:
        """Poll the process and return status."""
        if self._process is None:
            return {"running": False}

        retcode = self._process.poll()
        if retcode is None:
            return {"running": True, "pid": self._process.pid}

        # Process has exited — clean up
        self._cleanup_stderr()
        self._cleanup_symlink()
        stderr_output = ""
        if STDERR_LOG.exists():
            try:
                stderr_output = STDERR_LOG.read_text(errors="replace").strip()
            except Exception:
                pass
        if stderr_output:
            logger.warning("gym-retro-integration stderr: %s", stderr_output[:500])

        self._process = None
        result: dict = {"running": False, "exit_code": retcode}
        if stderr_output:
            result["error"] = stderr_output[:500]
        return result

    def stop(self) -> dict:
        """Send SIGTERM to the process."""
        if not self.is_running():
            return {"status": "not_running"}

        try:
            self._process.send_signal(signal.SIGTERM)
            logger.info("Sent SIGTERM to integration tool (pid=%d)", self._process.pid)
            return {"status": "stopping", "pid": self._process.pid}
        except Exception as e:
            logger.error("Failed to stop integration tool: %s", e)
            return {"status": "error", "message": str(e)}

    def is_running(self) -> bool:
        """Quick alive check."""
        if self._process is None:
            return False
        if self._process.poll() is not None:
            self._cleanup_stderr()
            self._cleanup_symlink()
            self._process = None
            return False
        return True

    def _cleanup_stderr(self) -> None:
        if self._stderr_file:
            try:
                self._stderr_file.close()
            except Exception:
                pass
            self._stderr_file = None

    def _cleanup_symlink(self) -> None:
        if self._symlink:
            try:
                self._symlink.unlink(missing_ok=True)
            except Exception:
                pass
            self._symlink = None


launcher = IntegrationLauncher()
