"""Configuration et chemins de l'application IA Locale."""

import json
import os
from pathlib import Path


def dossier_config() -> Path:
    base = os.environ.get("IA_LOCALE_CONFIG")
    if base:
        return Path(base)
    xdg = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(xdg) / "ia-locale"


def dossier_donnees() -> Path:
    base = os.environ.get("IA_LOCALE_DATA")
    if base:
        return Path(base)
    xdg = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(xdg) / "ia-locale"


def racine_application() -> Path:
    """Racine de l'application (dossier contenant le code)."""
    return Path(__file__).resolve().parents[1]


def dossier_modeles_candidats(cfg: dict) -> list[Path]:
    """Dossiers models/ proposés, par ordre de priorité."""
    candidats: list[Path] = []
    if cfg.get("dossier_modeles"):
        candidats.append(Path(cfg["dossier_modeles"]))
    appimage = os.environ.get("APPIMAGE")
    if appimage:
        # En mode AppImage : models/ à côté du fichier .AppImage (persistant),
        # puis dossier de données utilisateur (jamais le montage lecture seule).
        candidats.append(Path(appimage).resolve().parent / "models")
    else:
        app_dir = os.environ.get("IA_LOCALE_APP_DIR")
        if app_dir:
            candidats.append(Path(app_dir) / "models")
        candidats.append(racine_application() / "models")
    candidats.append(dossier_donnees() / "models")
    return candidats


def dossier_modeles_effectif(cfg: dict) -> Path:
    for candidat in dossier_modeles_candidats(cfg):
        if candidat.is_dir():
            return candidat
    cible = dossier_donnees() / "models"
    cible.mkdir(parents=True, exist_ok=True)
    return cible


def _defaut_profil() -> dict:
    threads = max(1, (os.cpu_count() or 4) // 2)
    return {
        "mode_calcul": "auto",
        "budget_vram_go": 6.0,
        "budget_ram_go": 16.0,
        "offload_couches": -1,
        "threads_cpu": threads,
    }


def config_defaut() -> dict:
    return {
        "dossier_modeles": None,
        "dernier_modele": None,
        "generation": {
            "prereglage": "Neutre",
            "instruction_systeme": "Tu es un assistant utile, clair et concis. Réponds en français.",
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 512,
            "contexte": 4096,
        },
        "apprentissage": {
            "max_pages": 5,
            "max_caracteres_page": 20000,
            "max_total": 100000,
            "limite_resume": 4000,
            "delai_s": 15,
        },
        "profil_defaut": _defaut_profil(),
    }


def charger_config() -> dict:
    cfg = config_defaut()
    fichier = dossier_config() / "config.json"
    if fichier.is_file():
        try:
            with fichier.open("r", encoding="utf-8") as f:
                data = json.load(f)
            for cle, valeur in data.items():
                if isinstance(valeur, dict) and isinstance(cfg.get(cle), dict):
                    cfg[cle].update(valeur)
                else:
                    cfg[cle] = valeur
        except (OSError, json.JSONDecodeError):
            pass
    return cfg


def sauvegarder_config(cfg: dict) -> None:
    dossier = dossier_config()
    dossier.mkdir(parents=True, exist_ok=True)
    fichier = dossier / "config.json"
    tmp = fichier.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    tmp.replace(fichier)
