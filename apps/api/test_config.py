import urllib.request
import json
import urllib.error

BASE_URL = "http://localhost:8000/api"

def test_config():
    print("Testing Config API...")
    try:
        # Get Config
        with urllib.request.urlopen(f"{BASE_URL}/config") as response:
            config = json.loads(response.read())
            print(f"Current Config: {json.dumps(config, indent=2)}")
            
        # Update Config
        new_config = config.copy()
        new_config["default_algorithm"] = "DQN"
        new_config["roms_path"] = "/tmp/roms"
        
        req = urllib.request.Request(
            f"{BASE_URL}/config", 
            data=json.dumps(new_config).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='PUT'
        )
        with urllib.request.urlopen(req) as response:
            updated = json.loads(response.read())
            print(f"Updated: {updated['default_algorithm']}")
            assert updated["default_algorithm"] == "DQN"
            
        # Reset
        req = urllib.request.Request(
            f"{BASE_URL}/config/reset", 
            data=b"",
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req) as response:
            reset = json.loads(response.read())
            print(f"Reset: {reset['default_algorithm']}")
            assert reset["default_algorithm"] == "PPO"
            
        print("SUCCESS: Config API works.")
    except Exception as e:
        print(f"FAILURE: {e}")

if __name__ == "__main__":
    test_config()
