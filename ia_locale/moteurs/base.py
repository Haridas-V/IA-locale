"""Interface commune des moteurs d'inférence locaux."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


class ErreurMoteur(Exception):
    pass


@dataclass
class ParametresGeneration:
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 512
    contexte: int = 4096
    instruction_systeme: str = ""
    connaissances: str | None = None

    def message_systeme(self) -> str:
        texte = self.instruction_systeme or "Tu es un assistant utile."
        if self.connaissances:
            texte += "\n\n# Connaissances apprises localement (mode apprentissage)\n" + self.connaissances
        return texte


class MoteurBase(ABC):
    nom = "base"

    @staticmethod
    @abstractmethod
    def disponible() -> tuple[bool, str]:
        """Retourne (disponible, message explicatif en français)."""

    @abstractmethod
    def charger(self, modele, profil, contexte: int) -> None:
        """Charge le modèle en mémoire selon le profil matériel."""

    @abstractmethod
    def decharger(self) -> None:
        pass

    @abstractmethod
    def repondre(self, messages: list[dict], params: ParametresGeneration, on_token=None) -> str:
        """messages : liste {"role": ..., "content": ...}. Retourne la réponse complète."""

    def est_charge(self) -> bool:
        return False
