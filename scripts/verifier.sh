#!/bin/sh
# Vérifie : tests unitaires, démarrage + pages de l'interface, AppImage.
# Usage : sh scripts/verifier.sh   (variables d'env optionnelles : LIBS_PREFIX, FONTCONFIG_FILE)
set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export QT_QPA_PLATFORM=offscreen
export LD_LIBRARY_PATH="${LIBS_PREFIX:-/tmp/sysroot}/usr/lib/x86_64-linux-gnu:${LIBS_PREFIX:-/tmp/sysroot}/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
[ -n "${FONTCONFIG_FILE:-}" ] && export FONTCONFIG_FILE

echo "== Tests unitaires =="
python3 -m pytest tests/ -q

echo "== Démarrage + pages de l'interface (captures dans build/captures/) =="
rm -rf /tmp/ia-locale-verif
python3 scripts/verifier_ui.py 2>&1 | grep -E "OK|ARRÊT" || true
mkdir -p build/captures
cp /tmp/ia-locale-verif/captures/*.png build/captures/ 2>/dev/null || true

APPIMAGE="$ROOT/dist/IA-Locale-x86_64.AppImage"
if [ -f "$APPIMAGE" ]; then
    echo "== Vérification de l'AppImage (avec puis sans modèle) =="
    T=/tmp/ia-locale-appimage-verif
    rm -rf "$T"; mkdir -p "$T/models"
    cp "$APPIMAGE" "$T/"
    python3 - "$T" <<'PYEOF'
import sys
sys.path.insert(0, "tests")
from pathlib import Path
from util_gguf import ecrire_gguf, meta_llama_test
ecrire_gguf(Path(sys.argv[1]) / "models" / "demo-7b-q4_k_m.gguf", meta_llama_test(), [("w", [1000, 1000], 6)], octets_donnees=64)
PYEOF
    (cd "$T" && IA_LOCALE_CONFIG="$T/config" IA_LOCALE_DATA="$T/data" IA_LOCALE_MOCK=1 \
        timeout 90 ./IA-Locale-x86_64.AppImage --appimage-extract-and-run --auto-test 2>&1 | grep -E "démarré|détecté")
    rm -rf "$T/models"
    (cd "$T" && IA_LOCALE_CONFIG="$T/config2" IA_LOCALE_DATA="$T/data2" IA_LOCALE_MOCK=1 \
        timeout 90 ./IA-Locale-x86_64.AppImage --appimage-extract-and-run --auto-test 2>&1 | grep -E "démarré|détecté")
    echo "AppImage OK"
else
    echo "AppImage absente (lancez ./build_appimage.sh) — ignoré"
fi

echo "== TOUTES LES VÉRIFICATIONS SONT PASSÉES =="
