"""
Main CLI Entry Point

Generic entry point for the game AI agent system.
Provides commands to check dependencies, run demos, and manage the system.
"""

import argparse
import sys
import subprocess


def check_python_packages() -> bool:
    """Check if all required Python packages are installed."""
    packages = [
        ("mss", "mss"),
        ("pyautogui", "pyautogui"),
        ("numpy", "numpy"),
        ("PIL", "pillow"),
        ("requests", "requests"),
        ("gymnasium", "gymnasium"),
        ("stable_baselines3", "stable-baselines3"),
    ]

    all_ok = True
    print("Checking Python packages...")

    for import_name, package_name in packages:
        try:
            __import__(import_name)
            print(f"  ✓ {package_name}")
        except ImportError:
            print(f"  ✗ {package_name} - run: pip install {package_name}")
            all_ok = False

    return all_ok


def check_ollama() -> bool:
    """Check if Ollama is running and accessible."""
    import requests

    print("\nChecking Ollama...")

    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        response.raise_for_status()
        models = response.json().get("models", [])
        model_names = [m.get("name", "") for m in models]

        print(f"  ✓ Ollama is running")
        print(f"  Available models: {', '.join(model_names) or 'none'}")

        # Check for vision models
        vision_models = [m for m in model_names if "llava" in m.lower() or "bakllava" in m.lower()]
        if vision_models:
            print(f"  ✓ Vision model available: {vision_models[0]}")
            return True
        else:
            print("  ⚠ No vision model found. Run: ollama pull llava:7b")
            return False

    except requests.exceptions.ConnectionError:
        print("  ✗ Ollama not running - start it with: ollama serve")
        return False
    except Exception as e:
        print(f"  ✗ Ollama error: {e}")
        return False


def check_screen_capture() -> bool:
    """Check if screen capture is working."""
    print("\nChecking screen capture...")

    try:
        import mss

        with mss.mss() as sct:
            monitors = sct.monitors
            print(f"  ✓ Found {len(monitors) - 1} monitor(s)")
            for i, mon in enumerate(monitors[1:], 1):
                print(f"    Monitor {i}: {mon['width']}x{mon['height']}")
        return True
    except Exception as e:
        print(f"  ✗ Screen capture error: {e}")
        return False


def check_gpu() -> bool:
    """Check GPU status (informational only)."""
    print("\nGPU Info (for reference):")

    try:
        # Try to get AMD GPU info on Windows
        result = subprocess.run(
            ["powershell", "-Command", "Get-WmiObject Win32_VideoController | Select-Object Name"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            lines = [l.strip() for l in result.stdout.strip().split("\n") if l.strip() and l.strip() != "Name" and l.strip() != "----"]
            for line in lines:
                if line:
                    print(f"  • {line}")
        return True
    except Exception:
        print("  Could not query GPU info")
        return True  # Not critical


def run_check():
    """Run all system checks."""
    print("=" * 50)
    print("Pokemon AI Agent - System Check")
    print("=" * 50)

    results = []
    results.append(("Python packages", check_python_packages()))
    results.append(("Ollama", check_ollama()))
    results.append(("Screen capture", check_screen_capture()))
    check_gpu()

    print("\n" + "=" * 50)
    print("Summary:")
    all_ok = True
    for name, ok in results:
        status = "✓ OK" if ok else "✗ FAILED"
        print(f"  {name}: {status}")
        if not ok:
            all_ok = False

    if all_ok:
        print("\n✓ All checks passed! Ready to run.")
    else:
        print("\n⚠ Some checks failed. See above for details.")

    return 0 if all_ok else 1


def run_vision_test():
    """Test the vision classifier."""
    print("Testing vision classifier...")
    print("Make sure your emulator is visible on screen.\n")

    try:
        from vision_classifier import VisionClassifier

        classifier = VisionClassifier(model="llava:7b")

        if not classifier.check_ollama_status():
            print("Error: Ollama not running or llava:7b not available")
            print("Run: ollama pull llava:7b")
            return 1

        print("Capturing screen...")
        img = classifier.capture_screen()
        print(f"Captured: {img.size}")

        print("\nQuerying VLM (this may take a few seconds)...")
        state = classifier.classify("Describe what you see in this image briefly.")

        print(f"\nResponse ({state.extra.get('inference_time', 0):.2f}s):")
        print(state.raw_response)
        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="Pokemon AI Agent - Main CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py check           Check all dependencies
  python main.py vision-test     Test the vision classifier

For Pokemon-specific commands, use:
  python pokemon_agent.py demo   Test vision on Pokemon game
  python pokemon_agent.py train  Train the RL agent
  python pokemon_agent.py play   Watch the trained agent play
""",
    )

    parser.add_argument(
        "command",
        nargs="?",
        default="check",
        choices=["check", "vision-test"],
        help="Command to run (default: check)",
    )

    args = parser.parse_args()

    if args.command == "check":
        return run_check()
    elif args.command == "vision-test":
        return run_vision_test()


if __name__ == "__main__":
    sys.exit(main())
