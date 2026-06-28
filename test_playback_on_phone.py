import sys, os, json, time, hmac, hashlib, requests

HMAC_SECRET = "SECURETV#HMAC@SECRET"
API_BASE = "https://verynewapimax.extreaming.xyz"
ACCESS_TOKEN = ""

def generate_hmac(method, path, timestamp_ms):
    return hmac.new(HMAC_SECRET.encode("utf-8"),
                    f"{method}{path}{timestamp_ms}".encode("utf-8"),
                    hashlib.sha256).hexdigest()

def test_playback(ch_id):
    path = f"/api/v8/channel/{ch_id}/playback"
    ts = str(int(time.time() * 1000))
    sig = generate_hmac("GET", path, ts)
    hdrs = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "User-Agent": "okhttp/4.9.0",
        "Accept": "application/json",
        "Accept-Language": "en",
        "X-App-Code": "5712",
        "X-App-Version": "5.7.12",
        "X-Requested-With": "XMLHttpRequest",
        "X-SecureTV-Id": "com.mitvpro.android.ott",
        "X-Client-Identifier": "RFCX90RGPTA",
        "X-Signature": "",
        "X-Platform": "OTT",
        "X-Content-ADULT": "false",
        "X-Tenant-ID": "",
        "X-Timestamp": ts,
        "X-API-Signature": sig,
    }
    resp = requests.get(f"{API_BASE}{path}", headers=hdrs, timeout=15)
    print(f"Status: {resp.status_code}")
    try:
        print(json.dumps(resp.json(), indent=2))
    except Exception as e:
        print(resp.text)

if __name__ == "__main__":
    # Load secrets
    script_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(script_dir, "secrets.sh"), "r") as f:
        for line in f:
            if "ACCESS_TOKEN=" in line:
                ACCESS_TOKEN = line.split('"')[1]
    test_playback(188) # ABC MIAMI
