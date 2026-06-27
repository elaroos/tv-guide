import os, sys, json, time, hmac, hashlib, re
from datetime import datetime, timezone
from xml.sax.saxutils import escape as xml_escape
from concurrent.futures import ThreadPoolExecutor, as_completed

def env(key, default=None):
    return os.environ.get(key, default)

HMAC_SECRET = env("HMAC_SECRET", "SECURETV#HMAC@SECRET")
API_BASE = env("API_BASE", "https://verynewapimax.extreaming.xyz")
ACCESS_TOKEN = env("ACCESS_TOKEN")

HEADERS_TEMPLATE = {
    "Accept": "application/json",
    "Accept-Language": "en",
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "User-Agent": env("USER_AGENT", "MiTVPRO-OTT-Android"),
    "X-App-Code": env("APP_CODE", "5712"),
    "X-App-Version": env("APP_VERSION", "5.7.12"),
    "X-Requested-With": "XMLHttpRequest",
    "X-SecureTV-Id": env("SECURE_TV_ID", "com.mitvpro.android.ott"),
    "X-Client-Identifier": env("CLIENT_IDENTIFIER", "com.mitvpro.android.ott"),
    "X-Signature": "",
    "X-Platform": "OTT",
    "X-Content-ADULT": "false",
    "X-Tenant-ID": "",
}

def load_json(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def generate_hmac(method, path, timestamp_ms):
    return hmac.new(HMAC_SECRET.encode("utf-8"),
                    f"{method}{path}{timestamp_ms}".encode("utf-8"),
                    hashlib.sha256).hexdigest()

def get_stream_url(playback_data):
    if isinstance(playback_data, dict):
        data = playback_data.get("data", playback_data)
        if isinstance(data, dict):
            for key in ("channel_url", "url"):
                val = data.get(key)
                if val:
                    return val
            meta = data.get("meta", {})
            if isinstance(meta, dict):
                val = meta.get("deep_link_url")
                if val:
                    return val
        val = playback_data.get("channel_url")
        if val:
            return val
    return None

def get_logo(ch):
    for key in ("dark_logo_clipart", "logo_clipart"):
        val = ch.get(key)
        if val and str(val).startswith("uploads/"):
            return f"{API_BASE}/{val}"
    return ""

def iso_to_xmltv(iso):
    iso = iso.replace("Z", "").replace("T", " ").split(".")[0]
    parts = re.split(r"[- :]", iso)
    if len(parts) >= 5:
        return f"{parts[0]}{parts[1]}{parts[2]}{parts[3]}{parts[4]}00 +0000"
    return "20000101000000 +0000"

def fetch_one_playback(ch):
    import requests as req
    ch_id = ch["id"]
    ch_name = ch.get("channel_name", f"Channel {ch_id}")
    ch_num = ch.get("channel_number", 0)
    path = f"/api/v8/channel/{ch_id}/playback"
    ts = str(int(time.time() * 1000))
    sig = generate_hmac("GET", path, ts)
    hdrs = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "User-Agent": HEADERS_TEMPLATE["User-Agent"],
        "Accept": "application/json",
        "Accept-Language": "en",
        "X-App-Code": HEADERS_TEMPLATE["X-App-Code"],
        "X-App-Version": HEADERS_TEMPLATE["X-App-Version"],
        "X-Requested-With": "XMLHttpRequest",
        "X-SecureTV-Id": HEADERS_TEMPLATE["X-SecureTV-Id"],
        "X-Client-Identifier": HEADERS_TEMPLATE["X-Client-Identifier"],
        "X-Signature": "",
        "X-Platform": "OTT",
        "X-Content-ADULT": "false",
        "X-Tenant-ID": "",
        "X-Timestamp": ts,
        "X-API-Signature": sig,
    }
    try:
        resp = req.get(f"{API_BASE}{path}", headers=hdrs, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            url = get_stream_url(data)
            if url:
                return (ch_id, {
                    "name": ch_name, "number": ch_num,
                    "url": url, "logo": get_logo(ch),
                    "category_id": ch.get("category_id")
                })
        elif resp.status_code == 401:
            print(f"[FATAL] Token expired at channel {ch_id}")
            return ("TOKEN_EXPIRED", None)
    except Exception as e:
        print(f"  [{ch_num:>3}] {ch_name:<30} Error: {e}")
    return (ch_id, None)

def fetch_playbacks(channels, session=None):
    results = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_one_playback, ch): ch for ch in channels}
        for future in as_completed(futures):
            ch_id, result = future.result()
            if ch_id == "TOKEN_EXPIRED":
                return None
            if result:
                results[ch_id] = result
    return results

def generate_m3u(results, categories):
    cat_names = {}
    if categories and isinstance(categories, list):
        for c in categories:
            cat_names[c["id"]] = c.get("local_genre", c.get("name", f"Cat {c['id']}"))
    sorted_channels = sorted(results.values(), key=lambda x: (x["number"] if x["number"] else 9999))
    lines = ['#EXTM3U tvg-url="epg.xml"']
    for cd in sorted_channels:
        cat_name = cat_names.get(cd.get("category_id"), "")
        logo = cd.get("logo", "")
        lines.append(f'#EXTINF:-1 tvg-id="{cd.get("channel_id", "")}" tvg-name="{cd["name"]}" tvg-logo="{logo}" group-title="{cat_name}",{cd["name"]}')
        lines.append(cd["url"])
    return "\n".join(lines)

def generate_epg(channels, token, session):
    import requests as req
    path = "/api/v8/channel-guide/mini"
    ts = str(int(time.time() * 1000))
    sig = generate_hmac("GET", path, ts)
    headers = {
        "User-Agent": HEADERS_TEMPLATE["User-Agent"],
        "Authorization": f"Bearer {token}",
        "X-Timestamp": ts,
        "X-API-Signature": sig,
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json",
        "X-App-Code": HEADERS_TEMPLATE["X-App-Code"],
        "X-App-Version": HEADERS_TEMPLATE["X-App-Version"],
        "X-SecureTV-Id": HEADERS_TEMPLATE["X-SecureTV-Id"],
        "X-Client-Identifier": HEADERS_TEMPLATE["X-Client-Identifier"],
        "X-Platform": "OTT",
    }
    now = datetime.now(timezone.utc)
    resp = session.get(f"{API_BASE}{path}?from={now.strftime('%Y-%m-%dT00:00:00.000')}Z", headers=headers, timeout=30)
    if resp.status_code != 200:
        print(f"[WARN] EPG fetch failed: HTTP {resp.status_code}")
        return None
    epg_data = resp.json()
    print(f"EPG items: {len(epg_data)}")
    ch_map = {c["id"]: c for c in channels}
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<tv>"]
    seen = set()
    for item in epg_data:
        cid = item["channel_id"]
        if cid not in seen:
            seen.add(cid)
            ch = ch_map.get(cid)
            name = ch["channel_name"] if ch else f"Channel {cid}"
            lines.append(f'  <channel id="{cid}">')
            lines.append(f'    <display-name>{xml_escape(name)}</display-name>')
            lines.append("  </channel>")
    for item in epg_data:
        cid = item["channel_id"]
        start = iso_to_xmltv(item["start_at"])
        stop = iso_to_xmltv(item["stop_at"])
        title = xml_escape(item.get("title") or "")
        desc = xml_escape(item.get("content") or "")
        icon = xml_escape(item.get("icon") or "")
        cat = xml_escape(item.get("category") or "")
        lines.append(f'  <programme start="{start}" stop="{stop}" channel="{cid}">')
        lines.append(f'    <title>{title}</title>')
        if desc:
            lines.append(f'    <desc>{desc}</desc>')
        if cat and cat != "None":
            lines.append(f'    <category>{cat}</category>')
        if icon.startswith("http"):
            lines.append(f'    <icon src="{icon}" />')
        lines.append("  </programme>")
    lines.append("</tv>")
    return "\n".join(lines)

def main():
    epg_only = "--epg-only" in sys.argv
    if not ACCESS_TOKEN:
        print("[ERROR] ACCESS_TOKEN environment variable not set")
        sys.exit(1)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    channels = load_json(os.path.join(script_dir, "channels_response.json"))
    if not channels:
        print("[ERROR] channels_response.json not found")
        sys.exit(1)
    print(f"Channels: {len(channels)}")
    categories = load_json(os.path.join(script_dir, "categories_response.json"))
    if categories:
        print(f"Categories: {len(categories)}")
    import requests as req
    session = req.Session()
    if not epg_only:
        print("Fetching playbacks...")
        results = fetch_playbacks(channels, session)
        if results is None:
            sys.exit(1)
        print(f"OK: {len(results)} channels with URLs")
        m3u = generate_m3u(results, categories)
        m3u_path = os.path.join(script_dir, "playlist.m3u")
        with open(m3u_path, "w", encoding="utf-8") as f:
            f.write(m3u)
        print(f"M3U: {m3u_path} ({len(m3u)} bytes)")
    else:
        print("--epg-only: skipping playback fetch")
    print("Fetching EPG...")
    time.sleep(2)
    epg_xml = generate_epg(channels, ACCESS_TOKEN, session)
    if not epg_xml:
        print("Retrying EPG in 5s...")
        time.sleep(5)
        epg_xml = generate_epg(channels, ACCESS_TOKEN, session)
    if epg_xml:
        epg_path = os.path.join(script_dir, "epg.xml")
        with open(epg_path, "w", encoding="utf-8") as f:
            f.write(epg_xml)
        prog_count = len(re.findall(r'<programme ', epg_xml))
        print(f"EPG: {epg_path} ({len(epg_xml)} bytes, {prog_count} programs)")

if __name__ == "__main__":
    main()
