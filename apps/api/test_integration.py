import json
import sys
import urllib.request

BASE_URL = "http://localhost:8000/api"
ROOT_URL = "http://localhost:8000"


def check_server():
    """Check if server is running."""
    try:
        urllib.request.urlopen(f"{ROOT_URL}/", timeout=1)
        return True
    except Exception:
        return False


def test_roms():
    print("Testing /api/roms...")
    try:
        with urllib.request.urlopen(f"{BASE_URL}/roms") as response:
            data = json.loads(response.read())

        print(f"Found {len(data)} games.")

        playable = [g for g in data if g.get("playable")]
        print(f"Found {len(playable)} playable games.")

        if not playable:
            print("FAILURE: No playable games found via API.")
            return False

        # Check specific game details
        game = playable[0]
        game_id = game["id"]
        print(f"Testing details for {game_id}...")

        with urllib.request.urlopen(f"{BASE_URL}/roms/{game_id}") as response:
            details = json.loads(response.read())

        if "states" in details and len(details["states"]) > 0:
            print(f"SUCCESS: Retrieved details for {game_id} with {len(details['states'])} states.")
            return True
        else:
            print("FAILURE: States missing in details.")
            return False

    except Exception as e:
        print(f"FAILURE: {e}")
        return False


if __name__ == "__main__":
    if not check_server():
        print("Server not running. Attempting to start default server...")
        # Optional: could try to start it, but better to tell user
        print("Please run 'pnpm dev:api' or 'uvicorn src.main:app --reload' in another terminal.")
        sys.exit(1)

    success = test_roms()
    sys.exit(0 if success else 1)
