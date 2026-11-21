#!/bin/sh
# Construit l'AppImage Linux x86_64 « IA-Locale-x86_64.AppImage ».
#
# Contenu embarqué : un interpréteur Python 3.12 autonome (python-build-standalone)
# + PySide6/Qt. L'interface est 100 % native (aucun navigateur, aucun serveur local,
# donc aucun port réservé).
#
# Dépendances système requises sur la machine cible (présentes sur la plupart des
# distributions de bureau) : glibc >= 2.17, libGL.so.1, libEGL.so.1,
# libxkbcommon.so.0, libdbus-1.so.3, libfontconfig.so.1, libglib-2.0.so.0.
# Moteurs d'inférence optionnels (non embarqués, voir README.md) :
#   pip install llama-cpp-python            # GGUF, CPU
#   pip install transformers accelerate torch  # Transformers, CPU
#
set -eu

ROOT="$(cd "$(dirname "$0")" && pwd)"
BUILD="$ROOT/build"
APPDIR="$BUILD/AppDir"
DIST="$ROOT/dist"
TOOLS="$BUILD/tools"
SYSROOT="$BUILD/tools/sysroot"

mkdir -p "$APPDIR" "$DIST" "$TOOLS" "$SYSROOT"

echo "== 1/5 Téléchargement des outils (python-build-standalone, appimagetool, squashfs-tools) =="
python3 - "$TOOLS" "$SYSROOT" <<'PYEOF'
import json, os, re, shutil, struct, subprocess, sys, urllib.request, lzma
from pathlib import Path

tools = Path(sys.argv[1]); sysroot = Path(sys.argv[2])

def telecharger(url, dest):
    dest = Path(dest)
    if dest.exists() and dest.stat().st_size > 0:
        print("déjà présent :", dest.name); return dest
    print("téléchargement :", url)
    with urllib.request.urlopen(url, timeout=120) as r, open(dest, "wb") as f:
        f.write(r.read())
    return dest

# --- python-build-standalone (dernier release, CPython 3.12 x86_64) ---
api = "https://api.github.com/repos/astral-sh/python-build-standalone/releases/latest"
with urllib.request.urlopen(api, timeout=60) as r:
    release = json.load(r)
motif = re.compile(r"cpython-3\.12\.\d+\+\d+-x86_64-unknown-linux-gnu-install_only_stripped\.tar\.gz$")
asset = next(a for a in release["assets"] if motif.search(a["name"]))
archive = telecharger(asset["browser_download_url"], tools / asset["name"])
cible = tools / "python-standalone"
if not (cible / "bin" / "python3").exists():
    subprocess.run(["tar", "-xzf", str(archive), "-C", str(tools)], check=True)
    for d in list(tools.iterdir()):
        if d.is_dir() and (d / "bin" / "python3").exists():
            if d != cible:
                d.rename(cible)
            break
assert (cible / "bin" / "python3").exists(), "python3 introuvable après extraction"
print("python standalone prêt :", cible)

# --- appimagetool ---
appimagetool = telecharger(
    "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage",
    tools / "appimagetool-x86_64.AppImage")
os.chmod(appimagetool, 0o755)

# --- mksquashfs ---
# 1) on réutilise le mksquashfs du système s'il existe
# 2) sinon on télécharge les paquets Debian (sans root) dans /tmp et on les extrait
mks = tools / "bin" / "mksquashfs"
if not mks.exists() and shutil.which("mksquashfs"):
    (tools / "bin").mkdir(parents=True, exist_ok=True)
    os.symlink(shutil.which("mksquashfs"), mks)
if not mks.exists():
    lists = Path("/tmp/apt/lists")
    try:
        (lists / "partial").mkdir(parents=True, exist_ok=True)
        if not any(lists.glob("*Packages*")):
            print("mise à jour des listes apt locales (sans root)...")
            subprocess.run(["apt-get", "-o", f"Dir::State::Lists={lists}", "-o", "APT::Get::ListCleanup=0",
                            "-o", "Debug::NoLocking=1", "update"], check=True, capture_output=True)
        subprocess.run(["apt-get", "-o", f"Dir::State::Lists={lists}", "-o", "Debug::NoLocking=1",
                        "download", "squashfs-tools", "liblz4-1", "liblzo2-2", "libzstd1", "zlib1g",
                        "libgcc-s1"], cwd=str(tools), check=True, capture_output=True)
        for deb in tools.glob("*.deb"):
            subprocess.run(["dpkg-deb", "-x", str(deb), str(sysroot)], check=True)
        bin_src = sysroot / "usr/bin/mksquashfs"
        (tools / "bin").mkdir(parents=True, exist_ok=True)
        os.symlink(bin_src, mks)
        (tools / "lib").mkdir(exist_ok=True)
        for so in (sysroot / "usr/lib/x86_64-linux-gnu").glob("*.so*"):
            lien = tools / "lib" / so.name
            if not lien.exists():
                os.symlink(so, lien)
    except Exception as e:
        raise SystemExit(
            "Impossible d'obtenir mksquashfs automatiquement.\n"
            "Installez-le via votre gestionnaire de paquets, par ex. :\n"
            "  sudo apt install squashfs-tools        (Debian/Ubuntu)\n"
            "  sudo dnf install squashfs-tools        (Fedora)\n"
            "  sudo pacman -S squashfs-tools          (Arch)\n"
            f"Détail de l'erreur : {e}")
print("mksquashfs prêt")
PYEOF

export PATH="$TOOLS/bin:$PATH"
export LD_LIBRARY_PATH="$TOOLS/lib:$SYSROOT/usr/lib/x86_64-linux-gnu:$SYSROOT/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
mksquashfs -version >/dev/null 2>&1 && echo "mksquashfs OK"

echo "== 2/5 Interpréteur Python embarqué + PySide6 =="
PY="$TOOLS/python-standalone/bin/python3"
"$PY" -m ensurepip -q 2>/dev/null || true
rm -rf "$APPDIR/usr"
mkdir -p "$APPDIR/usr/lib/ia-locale" "$APPDIR/usr/lib/ia-locale-deps"
cp -r "$TOOLS/python-standalone" "$APPDIR/usr/python"
"$PY" -m pip install --quiet --target "$APPDIR/usr/lib/ia-locale-deps" --no-compile "PySide6>=6.6,<7"
cp -r "$ROOT/ia_locale" "$APPDIR/usr/lib/ia-locale/ia_locale"

echo "== 3/5 Fichiers de l'AppDir (AppRun, desktop, icônes) =="
install -m 755 "$ROOT/packaging/AppRun" "$APPDIR/AppRun"
install -m 644 "$ROOT/packaging/ia-locale.desktop" "$APPDIR/ia-locale.desktop"
install -m 644 "$ROOT/packaging/ia-locale-512.png" "$APPDIR/ia-locale.png"
mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps" "$APPDIR/usr/share/icons/hicolor/512x512/apps" "$APPDIR/usr/share/applications"
install -m 644 "$ROOT/packaging/ia-locale-256.png" "$APPDIR/usr/share/icons/hicolor/256x256/apps/ia-locale.png"
install -m 644 "$ROOT/packaging/ia-locale-512.png" "$APPDIR/usr/share/icons/hicolor/512x512/apps/ia-locale.png"
install -m 644 "$ROOT/packaging/ia-locale.desktop" "$APPDIR/usr/share/applications/ia-locale.desktop"

echo "== 4/5 Construction de l'AppImage =="
SORTIE="$DIST/IA-Locale-x86_64.AppImage"
rm -f "$SORTIE"
ARCH=x86_64 "$TOOLS/appimagetool-x86_64.AppImage" --appimage-extract-and-run "$APPDIR" "$SORTIE"

echo "== 5/5 Terminé =="
ls -la "$SORTIE"
echo "AppImage prête : $SORTIE"
