import argparse
import json
import os
import sys
import time

import stable_retro as retro

# Config button name -> retro button name(s)
# Some buttons map to multiple retro names (aliases used by different systems)
BUTTON_MAP: dict[str, list[str]] = {
    "up": ["UP"],
    "down": ["DOWN"],
    "left": ["LEFT"],
    "right": ["RIGHT"],
    "a": ["A", "BUTTON"],  # "BUTTON" for single-button systems (Atari)
    "b": ["B"],
    "c": ["C"],
    "x": ["X"],
    "y": ["Y"],
    "z_btn": ["Z"],
    "l": ["L"],
    "r": ["R"],
    "start": ["START", "RESET"],  # Some systems use RESET
    "select": ["SELECT", "MODE"],  # Genesis uses MODE
}

# Default joystick button index → retro button name(s)
# Nintendo physical layout (bottom=B, right=A) matching retro consoles
DEFAULT_JOYSTICK_MAP: dict[int, list[str]] = {
    0: ["B"],               # A/Cross (bottom face)
    1: ["A", "BUTTON"],     # B/Circle (right face)
    2: ["Y"],               # X/Square (left face)
    3: ["X"],               # Y/Triangle (top face)
    4: ["L"],               # Left bumper
    5: ["R"],               # Right bumper
    6: ["SELECT", "MODE"],  # Back/Select
    7: ["START", "RESET"],  # Start
}

STICK_DEADZONE = 0.5


def _build_joystick_map(controller_config: dict | None) -> dict[int, list[str]]:
    """Build joystick button map from controller config or use defaults."""
    if not controller_config:
        return DEFAULT_JOYSTICK_MAP.copy()

    result: dict[int, list[str]] = {}

    # Map config field name → retro button names
    field_to_retro: dict[str, list[str]] = {
        "a_button": ["A", "BUTTON"],
        "b_button": ["B"],
        "x_button": ["X"],
        "y_button": ["Y"],
        "l_button": ["L"],
        "r_button": ["R"],
        "start_button": ["START", "RESET"],
        "select_button": ["SELECT", "MODE"],
        "c_button": ["C"],
        "z_button": ["Z"],
    }

    for field, retro_names in field_to_retro.items():
        btn_idx = controller_config.get(field)
        if btn_idx is not None and isinstance(btn_idx, int):
            if btn_idx not in result:
                result[btn_idx] = []
            result[btn_idx].extend(retro_names)

    return result if result else DEFAULT_JOYSTICK_MAP.copy()


def _build_pygame_key_lookup(pygame) -> dict[str, int]:
    """Map uppercase key names to pygame key constants."""
    lookup: dict[str, int] = {}
    for code in range(max(pygame.K_LAST if hasattr(pygame, "K_LAST") else 512, 512)):
        name = pygame.key.name(code).upper()
        if name and name != "UNKNOWN" and name != "":
            lookup[name] = code
    # Aliases: ENTER ↔ RETURN
    if "RETURN" in lookup:
        lookup.setdefault("ENTER", lookup["RETURN"])
    if "ENTER" in lookup:
        lookup.setdefault("RETURN", lookup["ENTER"])
    return lookup


def run_headless(args):
    """Headless mode: no pygame, stream raw RGB frames to stdout at 60fps."""
    import fcntl
    import struct
    import threading

    # All prints go to stderr so stdout is clean for frame protocol
    def log(msg):
        print(msg, file=sys.stderr, flush=True)

    log(f"[headless] Starting {args.game} (state={args.state})")

    inttype = retro.data.Integrations.STABLE | retro.data.Integrations.CUSTOM_ONLY
    record = args.record if args.record else False
    env = retro.make(
        game=args.game,
        state=args.state,
        scenario=args.scenario,
        record=record,
        render_mode="rgb_array",
        inttype=inttype,
        players=args.players,
    )
    buttons = env.buttons
    obs, _ = env.reset()

    # Non-blocking stdin for input (written by play_manager via pipe)
    stdin_fd = sys.stdin.buffer.fileno()
    fl = fcntl.fcntl(stdin_fd, fcntl.F_GETFL)
    fcntl.fcntl(stdin_fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
    stdin_buf = b""

    # Binary stdout for raw frame data
    stdout_bin = sys.stdout.buffer

    # Background frame writer — sends raw RGB pixels with a 4-byte header
    # Protocol: [u16 LE width][u16 LE height][width*height*3 bytes RGB]
    frame_slot: list = [None]  # latest frame, overwritten each tick
    frame_ready = threading.Event()

    def frame_writer():
        while True:
            frame_ready.wait()
            frame_ready.clear()
            rgb = frame_slot[0]
            if rgb is None:
                break
            h, w = rgb.shape[:2]
            header = struct.pack("<HH", w, h)
            try:
                stdout_bin.write(header)
                stdout_bin.write(rgb.tobytes())
                stdout_bin.flush()
            except (BrokenPipeError, OSError):
                break

    writer = threading.Thread(target=frame_writer, daemon=True)
    writer.start()

    frame_interval = 1.0 / 60.0
    gp_debug_count = 0
    held_buttons: list[str] = []  # persists across frames until new input arrives

    log("[headless] Entering game loop (raw RGB streaming)")
    try:
        while True:
            t0 = time.monotonic()

            # Drain stdin, update held_buttons with the latest complete message
            try:
                chunk = os.read(stdin_fd, 65536)
                if chunk:
                    stdin_buf += chunk
            except BlockingIOError:
                pass
            if b"\n" in stdin_buf:
                *lines, stdin_buf = stdin_buf.split(b"\n")
                last_line = lines[-1].strip() if lines else b""
                if last_line:
                    try:
                        parsed = json.loads(last_line)
                        if isinstance(parsed, list):
                            held_buttons = parsed
                            if held_buttons and gp_debug_count < 10:
                                gp_debug_count += 1
                                log(f"[headless] Input: {held_buttons}")
                    except json.JSONDecodeError:
                        pass

            # Step — held_buttons persists until the browser sends a new state
            action = [b is not None and b in held_buttons for b in buttons]
            obs, rew, terminated, truncated, info = env.step(action)
            if terminated or truncated:
                obs, _ = env.reset()

            # Hand frame to background writer (copy so env can reuse the buffer)
            frame_slot[0] = env.render().copy()
            frame_ready.set()

            # Maintain 60fps
            elapsed = time.monotonic() - t0
            remaining = frame_interval - elapsed
            if remaining > 0:
                time.sleep(remaining)
    except KeyboardInterrupt:
        pass
    finally:
        # Signal writer to exit
        frame_slot[0] = None
        frame_ready.set()
        writer.join(timeout=1)
        env.close()
        log("[headless] Done")


def main():
    parser = argparse.ArgumentParser(description="Interactive retro game player")
    parser.add_argument("--game", required=True)
    parser.add_argument("--state", default=None)
    parser.add_argument("--scenario", default=None)
    parser.add_argument("--players", type=int, default=1)
    parser.add_argument("--record", default=None)
    args = parser.parse_args()

    # Headless streaming mode — no pygame, frames to stdout
    if os.environ.get("AUTOGAMER_STREAM_FRAMES") == "1":
        run_headless(args)
        return

    import numpy as np
    import pygame

    # Load custom keybinds from environment
    custom_keybinds: dict[str, str] | None = None
    raw = os.environ.get("AUTOGAMER_KEYBINDS")
    if raw:
        try:
            custom_keybinds = json.loads(raw)
            print(f"[pygame] Loaded keybinds: {list(custom_keybinds.keys())}")
        except json.JSONDecodeError as e:
            print(f"[pygame] Bad AUTOGAMER_KEYBINDS JSON: {e}")

    # Load controller config from environment
    controller_config: dict | None = None
    raw_ctrl = os.environ.get("AUTOGAMER_CONTROLLER")
    if raw_ctrl:
        try:
            controller_config = json.loads(raw_ctrl)
            print("[pygame] Loaded controller config")
        except json.JSONDecodeError as e:
            print(f"[pygame] Bad AUTOGAMER_CONTROLLER JSON: {e}")

    joystick_map = _build_joystick_map(controller_config)
    deadzone = controller_config.get("deadzone", STICK_DEADZONE) if controller_config else STICK_DEADZONE

    # Create retro environment
    inttype = retro.data.Integrations.STABLE | retro.data.Integrations.CUSTOM_ONLY
    record = args.record if args.record else False
    env = retro.make(
        game=args.game,
        state=args.state,
        scenario=args.scenario,
        record=record,
        render_mode="rgb_array",
        inttype=inttype,
        players=args.players,
    )
    buttons = env.buttons  # e.g. ['B', None, 'SELECT', 'START', 'UP', 'DOWN', 'LEFT', 'RIGHT', 'A', ...]

    # Init pygame
    pygame.init()
    obs, _ = env.reset()
    frame = env.render()
    h, w = frame.shape[:2]
    scale = 3
    screen = pygame.display.set_mode((w * scale, h * scale), pygame.RESIZABLE)
    pygame.display.set_caption(args.game)
    clock = pygame.time.Clock()

    # Build key name → pygame key constant lookup
    key_lookup = _build_pygame_key_lookup(pygame)

    # Pre-compute keybind → (pygame_key_code, retro_button_names) pairs
    keybind_actions: list[tuple[int, list[str]]] = []
    if custom_keybinds:
        for config_btn, retro_btns in BUTTON_MAP.items():
            key_name = custom_keybinds.get(config_btn)
            if key_name:
                code = key_lookup.get(key_name.upper())
                if code is not None:
                    keybind_actions.append((code, retro_btns))
    else:
        # Default keyboard mappings (matches stable-retro upstream layout)
        defaults: dict[str, str] = {
            "UP": "UP",
            "DOWN": "DOWN",
            "LEFT": "LEFT",
            "RIGHT": "RIGHT",
            "Z": "A,BUTTON",
            "X": "B",
            "A": "X",
            "S": "Y",
            "Q": "L",
            "W": "R",
            "C": "C",
            "D": "Z",
            "RETURN": "START,RESET",
            "TAB": "SELECT,MODE",
        }
        for key_name, btn_str in defaults.items():
            code = key_lookup.get(key_name.upper())
            if code is not None:
                keybind_actions.append((code, btn_str.split(",")))

    # Init joystick
    pygame.joystick.init()
    joystick: pygame.joystick.JoystickType | None = None
    if pygame.joystick.get_count() > 0:
        joystick = pygame.joystick.Joystick(0)
        joystick.init()
        print(f"[pygame] Controller: {joystick.get_name()}")
    else:
        print("[pygame] No controller found")

    # Browser gamepad forwarding (file-based IPC)
    gamepad_file = os.environ.get("AUTOGAMER_GAMEPAD_FILE")
    if gamepad_file:
        print(f"[pygame] Gamepad file: {gamepad_file}")
    else:
        print("[pygame] No AUTOGAMER_GAMEPAD_FILE set")
    gp_debug_count = 0

    # Game loop
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        if not running:
            break

        # --- Collect input ---
        retro_pressed: set[str] = set()

        # Keyboard
        keys = pygame.key.get_pressed()
        for code, retro_btns in keybind_actions:
            if keys[code]:
                retro_pressed.update(retro_btns)

        # Browser gamepad (file-based — written by WS endpoint)
        if gamepad_file:
            try:
                with open(gamepad_file) as f:
                    gp_buttons = json.load(f)
                if isinstance(gp_buttons, list):
                    if gp_buttons and gp_debug_count < 20:
                        gp_debug_count += 1
                        print(f"[pygame] Gamepad buttons from file: {gp_buttons}")
                    retro_pressed.update(gp_buttons)
            except FileNotFoundError:
                pass  # File not created yet, normal
            except (json.JSONDecodeError, OSError) as e:
                if gp_debug_count < 5:
                    gp_debug_count += 1
                    print(f"[pygame] Gamepad file read error: {e}")

        # Joystick
        if joystick:
            # Face buttons
            for btn_idx, retro_btns in joystick_map.items():
                if btn_idx < joystick.get_numbuttons() and joystick.get_button(btn_idx):
                    retro_pressed.update(retro_btns)

            # D-pad hat (returns (x, y) tuple)
            if joystick.get_numhats() > 0:
                hat = joystick.get_hat(0)
                if hat[0] < 0:
                    retro_pressed.add("LEFT")
                if hat[0] > 0:
                    retro_pressed.add("RIGHT")
                if hat[1] > 0:
                    retro_pressed.add("UP")
                if hat[1] < 0:
                    retro_pressed.add("DOWN")

            # Left stick as d-pad
            if joystick.get_numaxes() >= 2:
                if joystick.get_axis(0) < -deadzone:
                    retro_pressed.add("LEFT")
                if joystick.get_axis(0) > deadzone:
                    retro_pressed.add("RIGHT")
                if joystick.get_axis(1) < -deadzone:
                    retro_pressed.add("UP")
                if joystick.get_axis(1) > deadzone:
                    retro_pressed.add("DOWN")

        # Build action array (None buttons → False)
        action = [b is not None and b in retro_pressed for b in buttons]

        # Step environment
        obs, rew, terminated, truncated, info = env.step(action)
        if terminated or truncated:
            obs, _ = env.reset()

        # Render
        frame = env.render()
        surf = pygame.surfarray.make_surface(np.transpose(frame, (1, 0, 2)))
        surf = pygame.transform.scale(surf, screen.get_size())
        screen.blit(surf, (0, 0))
        pygame.display.flip()

        clock.tick(60)

    env.close()
    pygame.quit()


if __name__ == "__main__":
    main()
