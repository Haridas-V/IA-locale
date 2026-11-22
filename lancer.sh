#!/bin/sh
# Lance l'AppImage IA Locale.
# - si une extraction permanente "squashfs-root/" existe à côté (utile pour y
#   installer les moteurs d'inférence en pip), on l'utilise ;
# - sinon on lance l'AppImage avec --appimage-extract-and-run (fonctionne sans FUSE).
DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
APP="$DIR/dist/IA-Locale-x86_64.AppImage"
if [ ! -f "$APP" ]; then
    echo "AppImage introuvable : $APP"
    echo "Construisez-la d'abord avec : sh build_appimage.sh"
    exit 1
fi
chmod +x "$APP" 2>/dev/null || true
if [ -x "$DIR/squashfs-root/AppRun" ]; then
    exec "$DIR/squashfs-root/AppRun" "$@"
fi
exec "$APP" --appimage-extract-and-run "$@"
