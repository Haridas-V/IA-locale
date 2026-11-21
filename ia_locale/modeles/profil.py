"""Profils matériels enregistrés par modèle (JSON à côté du modèle)."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .modele import ModeleInfo

NOM_FICHIER_PROFIL = "profil_materiel.json"

MODES_CALCUL = ("auto", "cpu", "gpu", "hybride")


@dataclass
class ProfilMateriel:
    mode_calcul: str = "auto"
    budget_vram_go: float = 6.0
    budget_ram_go: float = 16.0
    offload_couches: int = -1  # -1 = toutes les couches
    threads_cpu: int = 4

    def vers_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def depuis_dict(data: dict) -> "ProfilMateriel":
        defaut = ProfilMateriel()
        champs = set(ProfilMateriel.__dataclass_fields__)
        nettoye = {k: v for k, v in (data or {}).items() if k in champs}
        profil = ProfilMateriel(**nettoye)
        if profil.mode_calcul not in MODES_CALCUL:
            profil.mode_calcul = defaut.mode_calcul
        for champ in ("budget_vram_go", "budget_ram_go"):
            try:
                setattr(profil, champ, float(getattr(profil, champ)))
            except (TypeError, ValueError):
                setattr(profil, champ, getattr(defaut, champ))
        for champ in ("offload_couches", "threads_cpu"):
            try:
                setattr(profil, champ, int(getattr(profil, champ)))
            except (TypeError, ValueError):
                setattr(profil, champ, getattr(defaut, champ))
        profil.threads_cpu = max(1, profil.threads_cpu)
        return profil

    def resume(self) -> str:
        mode = {"auto": "Auto", "cpu": "CPU", "gpu": "GPU", "hybride": "Hybride"}[self.mode_calcul]
        return (f"{mode} · VRAM {self.budget_vram_go:.1f} Gio · "
                f"RAM {self.budget_ram_go:.1f} Gio · "
                f"couches {'toutes' if self.offload_couches < 0 else self.offload_couches} · "
                f"{self.threads_cpu} fils CPU")


def chemin_profil(modele: ModeleInfo) -> Path:
    if modele.chemin.is_dir():
        return modele.chemin / NOM_FICHIER_PROFIL
    return modele.chemin.parent / f"{modele.chemin.name}.{NOM_FICHIER_PROFIL}"


def existe_profil(modele: ModeleInfo) -> bool:
    return chemin_profil(modele).is_file()


def charger_profil(modele: ModeleInfo, defaut: dict | ProfilMateriel | None = None) -> ProfilMateriel:
    if isinstance(defaut, ProfilMateriel):
        profil = ProfilMateriel(**asdict(defaut))
    else:
        profil = ProfilMateriel.depuis_dict(defaut or {})
    fichier = chemin_profil(modele)
    if fichier.is_file():
        try:
            with fichier.open("r", encoding="utf-8") as f:
                profil = ProfilMateriel.depuis_dict(json.load(f))
        except (OSError, json.JSONDecodeError):
            pass
    return profil


def sauvegarder_profil(modele: ModeleInfo, profil: ProfilMateriel) -> Path:
    fichier = chemin_profil(modele)
    if modele.chemin.is_dir():
        modele.chemin.mkdir(parents=True, exist_ok=True)
    else:
        fichier.parent.mkdir(parents=True, exist_ok=True)
    tmp = fichier.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(profil.vers_dict(), f, ensure_ascii=False, indent=2)
    tmp.replace(fichier)
    return fichier


def supprimer_profil(modele: ModeleInfo) -> bool:
    fichier = chemin_profil(modele)
    if fichier.is_file():
        fichier.unlink()
        return True
    return False
