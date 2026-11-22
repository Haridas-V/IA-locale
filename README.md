# IA Locale

Application de bureau **Linux x86_64** pour utiliser des modèles d'IA **locaux**, inspirée de l'expérience de LM Studio Bionic :
interface **sombre, soignée et entièrement en français**, **sans navigateur** (interface native Qt — aucun serveur local, donc **aucun port réservé**).

Déposez le dossier d'un modèle dans un dossier `models/`, sélectionnez-le dans la **Bibliothèque**, cliquez sur **Charger**, puis discutez dans l'onglet **Discussion**.

## Contenu de l'interface

- **Discussion** : zone de saisie (Entrée = envoyer, Maj+Entrée = saut de ligne), historique de conversation en bulles, bouton **Nouvelle conversation**, bouton **Mode apprentissage…**, sélecteur de modèle avec **Charger / Décharger**, et un **état vide explicite** quand aucun modèle n'est chargé (saisie désactivée, message invitant à aller dans la Bibliothèque).
- **Bibliothèque** : détecte automatiquement les modèles locaux dans `models/` —
  - fichiers **`.gguf`** (métadonnées lues dans l'en-tête GGUF : architecture, blocs, têtes KV, paramètres) ;
  - dossiers **Transformers** (présence de `config.json` + poids `.safetensors`/`.bin`).
  - Pour chaque modèle : détails, **estimation de la VRAM** (poids + cache KV du contexte + marge) et **profil matériel** associé.
- **Paramètres** :
  - *Réglages de génération* : instruction système, **préréglages de style** (Neutre, Créatif, Technique, Pédagogique, Concis), **température**, **top-p**, **nombre maximal de tokens**, **contexte** ;
  - *Matériel et calcul* : **mode de calcul Auto / CPU / GPU / Hybride**, **budget mémoire GPU (Gio)**, **offload des couches** pour GGUF, **threads CPU**, limites mémoire GPU/CPU pour Transformers, et **enregistrement d'un profil matériel propre à chaque modèle** (fichier `profil_materiel.json` à côté du modèle) ;
  - *Dossier des modèles* : chemin personnalisable ;
  - *Mode apprentissage* : limites par défaut du learn.

## Dossier `models/`

Ordre de recherche du dossier des modèles :

1. le chemin précisé dans **Paramètres → Dossier des modèles** ;
2. `models/` **à côté du fichier `.AppImage`** (mode portable) ;
3. en développement : `models/` à la racine du projet ;
4. sinon `~/.local/share/ia-locale/models/` (créé automatiquement).

Déposez-y par exemple `models/mon-modele-7b-q4_k_m.gguf` ou `models/mon-modele-hf/` (contenant `config.json` et les poids).

## Modes de calcul et profils matériels

- **Auto** : GPU si la VRAM estimée (marge pour le contexte incluse) tient dans le budget, sinon **hybride** (autant de couches que possible sur GPU), sinon **CPU**.
- **GPU** : toutes les couches sur la carte graphique ; si le budget est insuffisant, l'application avertit et réduit le nombre de couches.
- **Hybride** : le modèle est **réparti entre GPU et CPU** selon le budget VRAM (GGUF : nombre de couches déchargées ; Transformers : `device_map="auto"` + `max_memory` GPU/CPU).
- **CPU** : tout sur le processeur, `threads CPU` réglables.

Pour **GGUF**, l'estimation VRAM = poids des couches GPU + cache KV (`2 × contexte × têtes KV × dimension de tête × 2 octets` par couche) + **marge** (12 % + 256 Mio). Pour **Transformers**, la carte des appareils est `auto` avec des limites mémoire explicites GPU (`budget VRAM`) et CPU (`mémoire CPU max`).

Le profil matériel de chaque modèle est enregistré via **Paramètres → Enregistrer comme profil du modèle** et rechargé automatiquement à la sélection du modèle.

## Mode apprentissage (« learn »)

Bouton **Mode apprentissage…** dans Discussion (et section dédiée dans Paramètres) :

- l'IA va chercher des pages sur Internet (recherche automatique DuckDuckGo sur un sujet, ou **URLs fournies une par ligne**) ;
- le texte de chaque page est extrait (HTML nettoyé) puis **tronqué selon des limites réglables** : nombre maximal de pages, caractères max par page, caractères max au total ;
- à la fin du learn, un **résumé est produit avec une limite de paramètres fixée** (caractères max du résumé) ;
- tout est **stocké localement** (`~/.local/share/ia-locale/apprentissages/`) — seules des requêtes de lecture sont envoyées ; aucune donnée n'est renvoyée ailleurs ;
- les connaissances apprises peuvent être injectées dans le contexte de la discussion (sélecteur « Connaissances »).

⚠️ Ce mode **nécessite une connexion Internet** côté client. L'application reste utilisable hors ligne pour discuter avec un modèle local.

## L'AppImage

`dist/IA-Locale-x86_64.AppImage` (générée par `./build_appimage.sh`) embarque un **interpréteur Python 3.12 autonome + Qt/PySide6** : elle **s'ouvre sans aucun modèle** (états vides prévus partout).

Lancement : `chmod +x IA-Locale-x86_64.AppImage && ./IA-Locale-x86_64.AppImage`

### Dépendances système nécessaires (déjà présentes sur la plupart des distributions de bureau)

- glibc ≥ 2.17 (Ubuntu 18.04+, Debian 10+, etc.) ;
- `libGL.so.1`, `libEGL.so.1` (mesa), `libxkbcommon.so.0`, `libdbus-1.so.3`, `libfontconfig.so.1`, `libglib-2.0.so.0` ;
- les libs X de curseur (`libxcb-cursor0` et dépendances) sont **embarquées** dans l'AppImage ; si votre distribution les fournit déjà, tant mieux.

Exemples : `sudo apt install libgl1 libegl1 libxkbcommon0 libdbus-1-3 libfontconfig1 libglib2.0-0` (Debian/Ubuntu).

### Limites matérielles et moteurs d'inférence

L'AppImage embarque **l'interface** mais **pas les moteurs d'inférence** (trop lourds et dépendants du GPU). Sans moteur, le chargement d'un modèle affiche un message clair indiquant la commande d'installation. Les moteurs s'installent dans l'environnement Python embarqué, par exemple via l'interpréteur de l'AppImage extrait :

```sh
./IA-Locale-x86_64.AppImage --appimage-extract   # extrait dans squashfs-root/ (dossier courant)
PY="$PWD/squashfs-root/usr/python/bin/python3"
$PY -m pip install llama-cpp-python               # GGUF, CPU
# si « No module named pip » : curl -sS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py && $PY /tmp/get-pip.py
# puis lancez toujours via : ./squashfs-root/AppRun --dossier-modeles "$PWD/models"
# (le lancement via l'AppImage montée ne voit pas les paquets installés dans squashfs-root/)
```

| Usage | Commande d'installation du moteur |
|---|---|
| GGUF, CPU | `pip install llama-cpp-python` |
| GGUF, GPU **NVIDIA (CUDA)** | `pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu124` |
| GGUF, GPU **Vulkan** (AMD/Intel/NVIDIA) | `CMAKE_ARGS="-DGGML_VULKAN=ON" pip install llama-cpp-python --no-binary :all:` |
| GGUF, GPU **AMD (ROCm)** | `CMAKE_ARGS="-DGGML_HIP=ON" pip install llama-cpp-python --no-binary :all:` |
| Transformers, CPU | `pip install transformers accelerate torch` |
| Transformers, GPU NVIDIA | `pip install torch --index-url https://download.pytorch.org/whl/cu124` puis `pip install transformers accelerate` |

**Règle importante** : l'utilisation du **GPU nécessite un moteur compilé avec le backend adapté à la carte graphique** (CUDA, ROCm, Vulkan…). Un moteur CPU-only fera tout le calcul en CPU même en mode GPU/Hybride.

**RAM/VRAM** : prévoir au moins la taille du modèle en RAM (CPU) ou VRAM (GPU), **plus le cache du contexte** (ex. contexte 4096 ≈ quelques centaines de Mio selon le modèle) — l'estimation s'affiche dans la Bibliothèque.

## Développement

```sh
pip install -r requirements.txt pytest
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -q     # tests (scanner, VRAM, profils, learn, UI)
python3 scripts/verifier_ui.py                            # démarrage + captures des 3 pages
./build_appimage.sh                                       # construit dist/IA-Locale-x86_64.AppImage
```

`scripts/verifier.sh` enchaîne tests + vérification de l'interface + vérification de l'AppImage.

Prérequis pour `./build_appimage.sh` : machine Linux x86_64, `python3`, Internet, ~1,5 Go libres. `mksquashfs` est récupéré automatiquement (système, ou paquets Debian téléchargés sans root) ; sur une autre distribution, installez `squashfs-tools` via votre gestionnaire de paquets.

## Vérifications effectuées

- démarrage de l'AppImage **avec et sans modèle** (`--auto-test`) : OK ;
- les trois pages (Discussion, Bibliothèque, Paramètres) : navigation et contenus vérifiés (captures dans `build/captures/`) ;
- profil matériel enregistré/rechargé par modèle : OK ;
- détection GGUF (en-tête relu) et Transformers (`config.json`) : OK ;
- estimation VRAM avec marge de contexte et répartition hybride GPU/CPU : OK (tests unitaires) ;
- mode learn avec limites (pages, caractères, résumé) via serveur local : OK.

## Structure

```
ia_locale/
  config.py            chemins, configuration JSON
  etat.py              état partagé (modèles, moteur, profil courant)
  theme.py             thème sombre (QSS)
  apprentissage.py    mode learn (téléchargement + limites + stockage local)
  modeles/             scanner GGUF/Transformers, métadonnées GGUF, VRAM, profils matériels
  moteurs/             GGUF (llama-cpp-python), Transformers (HF), mock de test
  ui/                  fenêtre + pages Discussion / Bibliothèque / Paramètres + dialogue learn
models/                déposez vos modèles ici (voir models/README.md)
packaging/             AppRun, .desktop, icônes
build_appimage.sh      construit dist/IA-Locale-x86_64.AppImage
tests/                 tests unitaires + fumée UI (offscreen)
scripts/               vérification UI et génération d'icônes
```
