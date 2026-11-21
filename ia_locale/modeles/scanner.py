"""Détection des modèles locaux (GGUF et Transformers) dans le dossier models/."""

import json
import re
import struct
from pathlib import Path

from .gguf_meta import ErreurGGUF, lire_entete_gguf
from .modele import ModeleInfo

REGEX_QUANT = re.compile(r"(q\d[_a-z0-9]*|f16|f32|bf16|i-?quant|iq\d[_a-z0-9]*)", re.IGNORECASE)


def _params_depuis_octets(octets: int) -> int:
    """Estimation grossière : ~2 octets par paramètre en fp16."""
    return int(octets / 2) if octets else 0


def scanner_gguf(fichier: Path, racine: Path) -> ModeleInfo:
    meta: dict = {}
    try:
        meta = lire_entete_gguf(fichier)
    except (ErreurGGUF, OSError, struct.error) as e:
        meta = {"erreur_lecture": str(e)}
    quant = None
    m = REGEX_QUANT.search(fichier.stem.lower())
    if m:
        quant = m.group(1).upper().replace("-", "_")
    taille = fichier.stat().st_size
    params = meta.get("parametres_declares") or _params_depuis_octets(meta.get("octets_tensors") or taille)
    nom = meta.get("nom") or fichier.stem
    return ModeleInfo(
        id=str(fichier.relative_to(racine)),
        nom=nom,
        chemin=fichier,
        format="gguf",
        taille_octets=taille,
        params=params or None,
        params_estimes=not meta.get("parametres_declares"),
        quantisation=quant,
        meta=meta,
    )


def scanner_transformers(dossier: Path, racine: Path) -> ModeleInfo | None:
    fichier_config = dossier / "config.json"
    if not fichier_config.is_file():
        return None
    try:
        with fichier_config.open("r", encoding="utf-8") as f:
            config = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    taille = 0
    for motif in ("*.safetensors", "*.bin", "*.pt", "*.pth"):
        for poids in dossier.rglob(motif):
            if poids.is_file():
                taille += poids.stat().st_size
    params = None
    index = dossier / "model.safetensors.index.json"
    if index.is_file():
        try:
            with index.open("r", encoding="utf-8") as f:
                donnees = json.load(f)
            taille = sum(int(v.get("size", 0)) for v in donnees.get("weight_map", {}).values())
        except (OSError, json.JSONDecodeError):
            pass
    if params is None and taille:
        params = _params_depuis_octets(taille)
    archs = config.get("architectures") or []
    return ModeleInfo(
        id=str(dossier.relative_to(racine)),
        nom=dossier.name,
        chemin=dossier,
        format="transformers",
        taille_octets=taille,
        params=params,
        params_estimes=True,
        quantisation=None,
        meta={
            "type_modele": config.get("model_type", "?"),
            "architectures": archs,
            "config": config,
        },
    )


def scanner_modeles(racine: Path) -> list[ModeleInfo]:
    """Scanne le dossier models/ et retourne la liste des modèles trouvés."""
    racine = Path(racine)
    if not racine.is_dir():
        return []
    trouves: list[ModeleInfo] = []
    for fichier in sorted(racine.rglob("*.gguf")):
        if fichier.is_file() and not fichier.name.startswith("."):
            try:
                trouves.append(scanner_gguf(fichier, racine))
            except OSError:
                continue
    for dossier in sorted(p for p in racine.rglob("*") if p.is_dir()):
        if dossier.name.startswith(".") or dossier.name == "apprentissages":
            continue
        if (dossier / "config.json").is_file():
            modele = scanner_transformers(dossier, racine)
            if modele:
                trouves.append(modele)
    trouves.sort(key=lambda m: m.nom.lower())
    return trouves


def trouver_modele(modeles: list[ModeleInfo], id_modele: str | None) -> ModeleInfo | None:
    if not id_modele:
        return None
    for m in modeles:
        if m.id == id_modele:
            return m
    return None
