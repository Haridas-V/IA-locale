#!/bin/sh
# Lance l'AppImage IA Locale même sans FUSE (extraction puis exécution).
DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
APP="$DIR/dist/IA-Locale-x86_64.AppImage"
if [ ! -f "$APP" ]; then
    echo "AppImage introuvable : $APP"
    echo "Construisez-la d'abord avec : sh build_appimage.sh"
    exit 1
fi
chmod +x "$APP" 2>/dev/null || true
exec "$APP" --appimage-extract-and-run "$@"
