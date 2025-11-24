import requests
import sys


def test_backend():
    base_url = "http://127.0.0.1:5000"

    print("Testing /api/summary...")
    try:
        resp = requests.get(f"{base_url}/api/summary")
        if resp.status_code == 200:
            data = resp.json()
            print(f"SUCCESS: Retrieved {len(data)} accounts.")
            if len(data) > 0:
                first = data[0]
                print(f"Sample Account: {first['handle']} ({first['platform']})")

                # Test History
                print(f"Testing /api/history/{first['platform']}/{first['handle']}...")
                hist_resp = requests.get(
                    f"{base_url}/api/history/{first['platform']}/{first['handle']}"
                )
                if hist_resp.status_code == 200:
                    hist_data = hist_resp.json()
                    print(
                        f"SUCCESS: Retrieved history. {len(hist_data['dates'])} data points."
                    )
                else:
                    print(f"FAILURE: History endpoint returned {hist_resp.status_code}")
            else:
                print("WARNING: No accounts found to test history.")
        else:
            print(f"FAILURE: Summary endpoint returned {resp.status_code}")

    except requests.exceptions.ConnectionError:
        print("FAILURE: Could not connect to backend. Is it running?")


if __name__ == "__main__":
    test_backend()
