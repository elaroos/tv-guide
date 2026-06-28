#!/data/data/com.termux/files/usr/bin/bash
export PATH=/data/data/com.termux/files/usr/bin:$PATH
for i in 1 2 3 4 5; do
    echo "Attempt $i..."
    resp=$(curl -s --socks5-hostname 127.0.0.1:9050 --connect-timeout 15 --max-time 30 "https://check.torproject.org/api/ip" 2>&1)
    echo "Response: $resp"
    if echo "$resp" | grep -q "IsTor"; then
        echo "TOR_READY"
        break
    fi
    sleep 15
done
