"""Choix du moteur adapté au format du modèle."""

import os

from ..modeles.modele import ModeleInfo
from .base import MoteurBase
from .gguf import MoteurGGUF
from .hf import MoteurTransformers
from .mock import MoteurMock


def mode_mock_actif() -> bool:
    return os.environ.get("IA_LOCALE_MOCK", "").lower() in ("1", "true", "oui", "yes")


def creer_moteur(modele: ModeleInfo) -> MoteurBase:
    if mode_mock_actif():
        return MoteurMock()
    if modele.format == "gguf":
        return MoteurGGUF()
    return MoteurTransformers()


def disponibilite(modele: ModeleInfo) -> tuple[bool, str]:
    """Indique si un moteur peut prendre en charge ce modèle, et comment l'installer."""
    if mode_mock_actif():
        return MoteurMock.disponible()
    if modele.format == "gguf":
        return MoteurGGUF.disponible()
    return MoteurTransformers.disponible()
