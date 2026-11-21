"""Moteur de démonstration (écho) utilisé pour les tests sans modèle réel."""

from .base import ErreurMoteur, MoteurBase, ParametresGeneration


class MoteurMock(MoteurBase):
    nom = "Démonstration (écho)"

    def __init__(self):
        self._charge = False
        self._modele = None

    @staticmethod
    def disponible() -> tuple[bool, str]:
        return True, "Moteur de démonstration (variable IA_LOCALE_MOCK=1)."

    def charger(self, modele, profil, contexte: int) -> None:
        self._charge = True
        self._modele = modele

    def decharger(self) -> None:
        self._charge = False
        self._modele = None

    def est_charge(self) -> bool:
        return self._charge

    def repondre(self, messages, params: ParametresGeneration, on_token=None) -> str:
        if not self._charge:
            raise ErreurMoteur("Aucun modèle chargé.")
        dernier = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                dernier = m.get("content", "")
                break
        reponse = (f"[Mode démonstration — aucun vrai modèle chargé] "
                   f"Vous avez écrit : « {dernier} » "
                   f"(température={params.temperature}, max_tokens={params.max_tokens}).")
        if on_token is not None:
            moitie = max(1, len(reponse) // 2)
            on_token(reponse[:moitie])
            on_token(reponse[moitie:])
        return reponse
