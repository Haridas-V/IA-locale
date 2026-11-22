#!/bin/sh
# Construit un paquet Debian .deb de IA Locale (x86_64).
# Réutilise l'AppDir produit par build_appimage.sh (le lance d'abord si besoin).
set -eu
ROOT="$(cd "$(dirname "$0")" && pwd)"
APPDIR="$ROOT/build/AppDir"
DIST="$ROOT/dist"

if [ ! -x "$APPDIR/AppRun" ]; then
    echo "AppDir absent : lancement de build_appimage.sh d'abord..."
    sh "$ROOT/build_appimage.sh"
fi

mkdir -p "$DIST"
DEBROOT="$ROOT/build/deb-root"
rm -rf "$DEBROOT"
mkdir -p "$DEBROOT/DEBIAN" "$DEBROOT/opt/ia-locale" "$DEBROOT/usr/bin" \
         "$DEBROOT/usr/share/applications" "$DEBROOT/usr/share/icons/hicolor/256x256/apps" \
         "$DEBROOT/usr/share/icons/hicolor/512x512/apps"

cp -a "$ROOT/packaging/deb/DEBIAN/control" "$ROOT/packaging/deb/DEBIAN/postinst" "$DEBROOT/DEBIAN/"
chmod 755 "$DEBROOT/DEBIAN/postinst"
cp -a "$APPDIR/." "$DEBROOT/opt/ia-locale/"

cat > "$DEBROOT/usr/bin/ia-locale" <<'EOF'
#!/bin/sh
exec /opt/ia-locale/AppRun "$@"
EOF
chmod 755 "$DEBROOT/usr/bin/ia-locale"

install -m 644 "$ROOT/packaging/ia-locale.desktop" "$DEBROOT/usr/share/applications/ia-locale.desktop"
install -m 644 "$ROOT/packaging/ia-locale-256.png" "$DEBROOT/usr/share/icons/hicolor/256x256/apps/ia-locale.png"
install -m 644 "$ROOT/packaging/ia-locale-512.png" "$DEBROOT/usr/share/icons/hicolor/512x512/apps/ia-locale.png"

OUT="$DIST/ia-locale_1.0.0_amd64.deb"
rm -f "$OUT"
dpkg-deb --root-owner-group --build "$DEBROOT" "$OUT"
echo "Paquet prêt : $OUT"
ls -la "$OUT"
