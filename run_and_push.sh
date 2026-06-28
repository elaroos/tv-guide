#!/data/data/com.termux/files/usr/bin/bash
set -e
export PATH="/data/data/com.termux/files/usr/bin:$PATH"

DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$DIR/last_run.log"
TS=$(date '+%Y-%m-%d %H:%M:%S')

log() { echo "[$TS] $1" | tee -a "$LOG"; }

log "=== Inicio ==="

# Cargar secrets si existe
if [ -f "$DIR/secrets.sh" ]; then
    source "$DIR/secrets.sh"
    log "Secrets cargados"
fi

# Validar tokens
if [ -z "$ACCESS_TOKEN" ]; then
    log "[ERROR] ACCESS_TOKEN no definido"
    exit 1
fi
if [ -z "$GH_TOKEN" ]; then
    log "[ERROR] GH_TOKEN no definido"
    exit 1
fi

export ACCESS_TOKEN
export HMAC_SECRET="SECURETV#HMAC@SECRET"
export API_BASE="https://verynewapimax.extreaming.xyz"
export APP_CODE="com.mitvpro.android.ott"
export APP_VERSION="1.0.1994"
export USER_AGENT="okhttp/4.9.0"
export SECURE_TV_ID="com.mitvpro.android.ott"
export CLIENT_IDENTIFIER="RFCX90RGPTA"

log "Instalando dependencias..."
/data/data/com.termux/files/usr/bin/pip install requests -q 2>>"$LOG"

log "Ejecutando playlist_generator.py..."
cd "$DIR"
python playlist_generator.py --kodi 2>&1 | tee -a "$LOG"

if [ ! -f "playlist.m3u" ] && [ ! -f "epg.xml" ]; then
    log "[ERROR] No se generaron archivos"
    exit 1
fi

# Si no hay playlist.m3u (epg-only), salir sin push
if [ ! -f "playlist.m3u" ]; then
    log "Solo EPG, sin playlist para push"
fi

log "Configurando git..."
git config user.name "tv-guide-bot"
git config user.email "bot@tv-guide.local"

# Configurar remote con token para auth
REPO_URL="https://elaroos:${GH_TOKEN}@github.com/elaroos/tv-guide.git"
git remote set-url origin "$REPO_URL" 2>/dev/null || \
    git remote add origin "$REPO_URL"

log "Haciendo commit y push..."
git pull --rebase origin main 2>&1 | tee -a "$LOG"
for f in playlist.m3u epg.xml; do
    [ -f "$f" ] && git add -f "$f"
done
if git diff --cached --quiet; then
    log "Sin cambios para commit"
else
    git commit -m "auto: update playlist + epg [skip ci]"
    git push origin main 2>&1 | tee -a "$LOG"
    log "Push completado"
fi

# Estadísticas
[ -f playlist.m3u ] && log "playlist.m3u: $(wc -c < playlist.m3u) bytes, $(grep -c '^https://' playlist.m3u) canales"
[ -f epg.xml ] && log "epg.xml: $(wc -c < epg.xml) bytes, $(grep -c '<programme ' epg.xml) programas"

log "=== Fin ==="
