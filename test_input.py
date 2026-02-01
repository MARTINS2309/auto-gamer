"""
Input Testing Utility

Tests keyboard input to emulators to verify key mappings are correct.
Run this with the emulator window focused to test button presses.
"""

import argparse
import time
import sys

import pyautogui


# Disable pyautogui failsafe
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.1


EMULATOR_KEYS = {
    "mgba": {
        "a": "x",
        "b": "z",
        "start": "enter",
        "select": "backspace",
        "up": "up",
        "down": "down",
        "left": "left",
        "right": "right",
        "l": "a",
        "r": "s",
    },
    "vba": {
        "a": "z",
        "b": "x",
        "start": "enter",
        "select": "backspace",
        "up": "up",
        "down": "down",
        "left": "left",
        "right": "right",
        "l": "a",
        "r": "s",
    },
}


def countdown(seconds: int = 5):
    """Countdown before starting tests."""
    print(f"\nClick on the emulator window NOW!")
    for i in range(seconds, 0, -1):
        print(f"  Starting in {i}...")
        time.sleep(1)
    print("  GO!\n")


def test_all_buttons(emulator: str):
    """Test all button mappings."""
    keys = EMULATOR_KEYS.get(emulator, EMULATOR_KEYS["mgba"])

    print(f"Testing all buttons for {emulator.upper()}")
    countdown()

    for button, key in keys.items():
        print(f"  Pressing {button.upper()} (key: {key})...")
        pyautogui.press(key)
        time.sleep(0.5)

    print("\nDone! Did all buttons register correctly?")


def test_movement(emulator: str):
    """Test directional movement."""
    keys = EMULATOR_KEYS.get(emulator, EMULATOR_KEYS["mgba"])

    print(f"Testing movement for {emulator.upper()}")
    countdown()

    # Movement pattern
    movements = ["up", "right", "down", "left"] * 2

    for direction in movements:
        key = keys[direction]
        print(f"  Moving {direction.upper()}...")
        pyautogui.press(key)
        time.sleep(0.3)

    print("\nDone! Character should have moved in a square pattern.")


def test_battle_actions(emulator: str):
    """Test typical battle button sequence."""
    keys = EMULATOR_KEYS.get(emulator, EMULATOR_KEYS["mgba"])

    print(f"Testing battle actions for {emulator.upper()}")
    print("Note: Start this test when in a battle at the move selection menu!")
    countdown()

    # Typical battle sequence: select first move
    sequence = [
        ("a", "Select Fight/First option"),
        ("a", "Confirm move"),
    ]

    for key_name, description in sequence:
        print(f"  {description} ({key_name.upper()})...")
        pyautogui.press(keys[key_name])
        time.sleep(0.5)

    print("\nDone! Check if the action was executed.")


def interactive_test(emulator: str):
    """Interactive mode - press buttons as you type them."""
    keys = EMULATOR_KEYS.get(emulator, EMULATOR_KEYS["mgba"])

    print(f"\nInteractive Test Mode for {emulator.upper()}")
    print("Type button names to press them. Type 'quit' to exit.")
    print(f"Available buttons: {', '.join(keys.keys())}\n")

    countdown(3)

    while True:
        try:
            button = input("Button> ").strip().lower()

            if button in ("quit", "exit", "q"):
                print("Exiting interactive mode.")
                break

            if button in keys:
                key = keys[button]
                print(f"  Pressing {button.upper()} (key: {key})")
                pyautogui.press(key)
            else:
                print(f"  Unknown button: {button}")
                print(f"  Available: {', '.join(keys.keys())}")

        except KeyboardInterrupt:
            print("\nExiting.")
            break


def main():
    parser = argparse.ArgumentParser(
        description="Test emulator keyboard input",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_input.py mgba           Interactive menu for mGBA
  python test_input.py vba            Interactive menu for VBA
""",
    )

    parser.add_argument(
        "emulator",
        nargs="?",
        default="mgba",
        choices=["mgba", "vba"],
        help="Emulator to test (default: mgba)",
    )

    args = parser.parse_args()

    print("=" * 50)
    print(f"Emulator Input Test - {args.emulator.upper()}")
    print("=" * 50)
    print(f"\nKey mappings for {args.emulator.upper()}:")
    for button, key in EMULATOR_KEYS[args.emulator].items():
        print(f"  {button:8} → {key}")

    print("\nSelect a test:")
    print("  1. Test all buttons")
    print("  2. Test movement (D-pad)")
    print("  3. Test battle actions")
    print("  4. Interactive mode")
    print("  5. Exit")

    try:
        choice = input("\nChoice (1-5): ").strip()

        if choice == "1":
            test_all_buttons(args.emulator)
        elif choice == "2":
            test_movement(args.emulator)
        elif choice == "3":
            test_battle_actions(args.emulator)
        elif choice == "4":
            interactive_test(args.emulator)
        elif choice == "5":
            print("Exiting.")
        else:
            print("Invalid choice.")

    except KeyboardInterrupt:
        print("\nExiting.")


if __name__ == "__main__":
    main()
