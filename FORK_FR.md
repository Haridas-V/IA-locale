# IA Locale — fork de Jan (Apache-2.0)

Ce fork part du projet open source **[Jan](https://github.com/janhq/jan)** (licence Apache-2.0, © Menlo Research)
et y ajoute les fonctionnalités demandées pour « IA Locale » :

## Modifications apportées

1. **Interface 100 % française par défaut**
   - `web-app/src/i18n/setup.ts` : langue par défaut `fr` (au lieu de `en`), repli `fr`.
   - `web-app/src/locales/fr/*.json` : les **844 clés manquantes** traduites en français (tous namespaces : common, settings, chat, providers, extensions, setup…). Vérification : 0 clé EN sans équivalent FR.
2. **Thème sombre par défaut** : `web-app/src/hooks/useTheme.ts` → `activeTheme: 'dark'`.
3. **Dossier `models/` local (GGUF + Transformers)**
   - Nouveau crate Rust `tools/gguf-meta/` : lecture d'en-tête GGUF (v1–v3, pur std) + **estimation VRAM avec marge pour le contexte** + répartition auto/CPU/GPU/hybride. Tests : `cargo test` (3 tests OK).
   - Nouvelles commandes Tauri (`src-tauri/src/local_models.rs`) : `default_models_dir` (dossier `models/` à côté de l'exécutable, sinon `<app_data>/models`), `scan_models_dir` (détection `.gguf` insensible à la casse + dossiers `config.json`, métadonnées, taille, paramètres, VRAM), `resolve_hardware_profile`, `apply_hardware_profile` (écrit `n_gpu_layers`, `ctx_size`, `threads` dans le `model.yml` du modèle).
   - UI : `web-app/src/containers/LocalModelsPanel.tsx` intégré à la page **Hub** : liste des modèles détectés, et **éditeur de profil matériel par modèle** (mode Auto/CPU/GPU/Hybride, budget VRAM, offload de couches, threads CPU, contexte) avec enregistrement persistant (`plugin-store`, `ia-locale-profils.json`) et application dans le `model.yml`.
4. **Mode apprentissage (learn)**
   - `web-app/src/lib/learn.ts` : recherche multi-moteurs (DuckDuckGo html/lite + Bing, avec extraction des redirections `uddg=`), téléchargement des pages via `plugin-http` (pas de CORS), **limites strictes** (pages max, caractères/page, total) puis **résumé tronqué à une limite de paramètres fixée**, stockage local (`ia-locale-apprentissages.json`).
   - UI : `web-app/src/containers/LearnPanel.tsx` dans **Paramètres → Général** ; les connaissances apprises sont proposées pour la discussion via `stores/learn-store.ts`.
   - Tests vitest : `web-app/src/lib/__tests__/learn.test.ts` (8 tests OK : extraction HTML, URLs uddg, limites, troncature).
5. Badges « ? » avec infobulle au survol sur les nouveaux réglages.

## Vérifications effectuées dans le bac à sable

- `cargo test` (gguf-meta) : 3/3 OK.
- `yarn install` puis `yarn vitest run src/lib/__tests__/learn.test.ts` : 8/8 OK.
- `yarn tsc --noEmit -p web-app/tsconfig.json` : **0 erreur**.
- Locale FR : 0 clé manquante par rapport à EN.

## Build de l'AppImage Linux x86_64

Jan fournit déjà la config Tauri AppImage (`src-tauri/tauri.linux.conf.json`). Sur une machine Linux x86_64 :

```sh
# Ubuntu 24.04 : libwebkit2gtk-4.1-dev ; Ubuntu 22.04 : libwebkit2gtk-4.0-dev à la place
sudo apt install -y wget git curl pkg-config build-essential librsvg2-dev \
  libwebkit2gtk-4.1-dev libgtk-3-dev libsoup-3.0-dev libjavascriptcoregtk-4.1-dev

# outillage : yarn 4.5.3 (épinglé via packageManager) + Rust 1.98 (rust-toolchain.toml)
corepack enable                                   # PAS le yarn 0.x du système
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source "$HOME/.cargo/env"                         # + l'ajouter à ~/.bashrc

yarn install                                      # ~1-2 min
yarn build:tauri                                  # 10-20 min (cargo) — plusieurs Go de RAM/disk
# AppImage : src-tauri/target/release/bundle/appimage/Jan-*.AppImage
```

Pièges vérifiés dans le code : `wget` requis (shim linuxdeploy), `corepack enable` obligatoire,
rustup obligatoire (le cargo apt 1.75 est trop vieux), `src-tauri/icons/icon.png` désormais poussé,
`APPIMAGE_EXTRACT_AND_RUN=1` est déjà géré par les scripts (pas besoin de FUSE), la sortie finale
s'appelle `Jan-*.AppImage` (repackagée par `build-utils/buildAppImage.sh` après `download:bin`).

Dépendances runtime de l'AppImage : glibc ≥ 2.28, webkit2gtk-4.1, gtk3, libsoup-3.0 (présents sur la plupart des distros de bureau). L'AppImage s'ouvre **sans modèle** (état vide prévu).

## Moteurs d'inférence

GGUF via l'extension `llamacpp-extension` de Jan (llama.cpp). **Le GPU nécessite un backend compilé adapté** (CUDA / Vulkan / ROCm) — voir Paramètres → Matériel dans l'app. Transformers : dossiers détectés dans `models/` (métadonnées affichées) ; le chargement HF dépend de l'extension disponible sur la plateforme.

## Limites connues de ce fork

- L'injection des connaissances "learn" dans le prompt système d'une discussion passe par le store `learn-store` (bouton « Utiliser ces connaissances ») ; le câblage direct dans le pipeline d'envoi de messages de Jan est à brancher selon la version exacte du fork.
- La compilation complète Tauri (webkit2gtk) n'a pas été faite dans le bac à sable ; elle est documentée ci-dessus et peut tourner en CI.
