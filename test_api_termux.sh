#!/data/data/com.termux/files/usr/bin/bash
export PATH="/data/data/com.termux/files/usr/bin:$PATH"
DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$DIR/secrets.sh" ]; then
    source "$DIR/secrets.sh"
fi

echo "Testing API with Tor SOCKS proxy..."
curl -s -i --socks5-hostname 127.0.0.1:9050 \
  -H "User-Agent: okhttp/4.9.0" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  "https://verynewapimax.extreaming.xyz/api/v8/channels" | head -n 25
LO MISMO 