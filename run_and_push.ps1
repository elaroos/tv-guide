$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$logFile = Join-Path $scriptDir "last_run.log"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

function Log($msg) {
    $line = "[$timestamp] $msg"
    Write-Output $line
    Add-Content -Path $logFile -Value $line
}

Log "=== Inicio ==="

# GitHub token from external file (never in repo)
$ghTokenFile = "C:\Users\elaroos\opencode\telegramdownload\gh_token.txt"
if (Test-Path $ghTokenFile) {
    $env:GH_TOKEN = (Get-Content $ghTokenFile -Raw).Trim()
    Log "GH_TOKEN loaded from file"
} elseif (![string]::IsNullOrEmpty($env:GH_TOKEN)) {
    Log "GH_TOKEN from environment"
} else {
    Log "[ERROR] GH_TOKEN not found in $ghTokenFile or environment"
    exit 1
}

# API token
$secretFile = "C:\Users\elaroos\opencode\telegramdownload\ACCESS_TOKEN_SECRET.txt"
if (!(Test-Path $secretFile)) {
    Log "[ERROR] ACCESS_TOKEN_SECRET.txt not found"
    exit 1
}

$token = (Get-Content $secretFile -Raw).Trim()
if ([string]::IsNullOrEmpty($token)) {
    Log "[ERROR] Token is empty"
    exit 1
}

# Set environment variables for the Python script
$env:ACCESS_TOKEN = $token
$env:HMAC_SECRET = "SECURETV#HMAC@SECRET"
$env:API_BASE = "https://verynewapimax.extreaming.xyz"
$env:APP_CODE = "com.mitvpro.android.ott"
$env:APP_VERSION = "1.0.1994"
$env:USER_AGENT = "okhttp/4.9.0"
$env:SECURE_TV_ID = "com.mitvpro.android.ott"
$env:CLIENT_IDENTIFIER = "RFCX90RGPTA"

Log "Running playlist_generator.py..."
try {
    Set-Location $scriptDir
    $output = py playlist_generator.py 2>&1
    $output | ForEach-Object { Log $_ }
} catch {
    Log "[ERROR] Python script failed: $_"
    exit 1
}

$m3uPath = Join-Path $scriptDir "playlist.m3u"
$epgPath = Join-Path $scriptDir "epg.xml"

$hasM3u = Test-Path $m3uPath
$hasEpg = Test-Path $epgPath

if (!$hasM3u -and !$hasEpg) {
    Log "[ERROR] No files were generated"
    exit 1
}

Log "Files generated: M3U=$hasM3u EPG=$hasEpg"

# Configure git
$env:GIT_AUTHOR_NAME = "tv-guide-bot"
$env:GIT_AUTHOR_EMAIL = "bot@tv-guide.local"
$env:GIT_COMMITTER_NAME = "tv-guide-bot"
$env:GIT_COMMITTER_EMAIL = "bot@tv-guide.local"
$git = "C:\Program Files\Git\cmd\git.exe"

Log "Committing to GitHub..."
try {
    & $git -C $scriptDir add playlist.m3u epg.xml
    $changed = & $git -C $scriptDir status --porcelain
    if ([string]::IsNullOrEmpty($changed)) {
        Log "No changes to commit"
    } else {
        & $git -C $scriptDir commit -m "auto: update playlist + epg [skip ci]"
        & $git -C $scriptDir push
        Log "Push completed"
    }
} catch {
    Log "[ERROR] Git operation failed: $_"
    exit 1
}

# Calculate sizes
if ($hasM3u) {
    $m3uSize = (Get-Item $m3uPath).Length
    $m3uUrls = (& $git -C $scriptDir grep -c "^https://" HEAD -- playlist.m3u 2>$null) -replace ".*:",""
    if ([string]::IsNullOrEmpty($m3uUrls)) { $m3uUrls = (Select-String -Path $m3uPath -Pattern "^https://").Count }
    Log "playlist.m3u: $m3uSize bytes, $m3uUrls channels"
}
if ($hasEpg) {
    $epgSize = (Get-Item $epgPath).Length
    $epgProgs = (Select-String -Path $epgPath -Pattern "<programme ").Count
    Log "epg.xml: $epgSize bytes, $epgProgs programs"
}

Log "=== Fin ==="
