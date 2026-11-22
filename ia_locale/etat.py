"""État partagé de l'application (config, modèles, moteur courant)."""

import os
from pathlib import Path

from . import config as cfg_module
from .modeles.modele import ModeleInfo
from .modeles.profil import ProfilMateriel, charger_profil, sauvegarder_profil, existe_profil
from .modeles.scanner import scanner_modeles, trouver_modele
from .moteurs.base import ErreurMoteur
from .moteurs.registre import creer_moteur, disponibilite


class EtatApplication:
    def __init__(self, racine: Path | None = None):
        self.racine = racine or cfg_module.racine_application()
        self.config = cfg_module.charger_config()
        self.dossier_modeles = cfg_module.dossier_modeles_effectif(self.config)
        self.modeles: list[ModeleInfo] = []
        self.modele_courant: ModeleInfo | None = None
        self.profil_courant: ProfilMateriel = ProfilMateriel.depuis_dict(self.config.get("profil_defaut", {}))
        self.moteur = None
        self.connaissances: str | None = None
        self.dernier_message_erreur: str | None = None
        self.actualiser_modeles()

    def actualiser_modeles(self) -> list[ModeleInfo]:
        self.dossier_modeles = cfg_module.dossier_modeles_effectif(self.config)
        self.dossier_modeles.mkdir(parents=True, exist_ok=True)
        self.modeles = scanner_modeles(self.dossier_modeles)
        courant = trouver_modele(self.modeles, self.modele_courant.id if self.modele_courant else None)
        if courant is None:
            courant = trouver_modele(self.modeles, self.config.get("dernier_modele"))
        if courant is not None and self.modele_courant is None:
            self.selectionner_modele(courant.id, charger=False)
        return self.modeles

    def selectionner_modele(self, id_modele: str | None, charger: bool = False) -> tuple[bool, str]:
        modele = trouver_modele(self.modeles, id_modele)
        if modele is None:
            self.modele_courant = None
            return False, "Aucun modèle sélectionné."
        self.modele_courant = modele
        self.profil_courant = charger_profil(modele, self.config.get("profil_defaut", {}))
        self.config["dernier_modele"] = modele.id
        cfg_module.sauvegarder_config(self.config)
        if charger:
            return self.charger_modele()
        return True, f"Modèle sélectionné : {modele.nom}"

    def charger_modele(self) -> tuple[bool, str]:
        if self.modele_courant is None:
            return False, "Sélectionnez d'abord un modèle dans la Bibliothèque."
        if self.moteur is not None and self.moteur.est_charge():
            self.moteur.decharger()
            self.moteur = None
        ok, message = disponibilite(self.modele_courant)
        if not ok:
            self.dernier_message_erreur = message
            return False, message
        moteur = creer_moteur(self.modele_courant)
        contexte = int(self.config.get("generation", {}).get("contexte", 4096))
        try:
            moteur.charger(self.modele_courant, self.profil_courant, contexte)
        except ErreurMoteur as e:
            self.dernier_message_erreur = str(e)
            return False, str(e)
        except Exception as e:  # erreur de chargement du poids
            self.dernier_message_erreur = str(e)
            return False, f"Échec du chargement du modèle : {e}"
        self.moteur = moteur
        self.dernier_message_erreur = None
        return True, f"Modèle chargé : {self.modele_courant.nom} ({self.modele_courant.resume()})"

    def decharger_modele(self) -> None:
        if self.moteur is not None:
            self.moteur.decharger()
            self.moteur = None

    def modele_est_charge(self) -> bool:
        return self.moteur is not None and self.moteur.est_charge()

    def enregistrer_profil_courant(self) -> Path:
        if self.modele_courant is None:
            raise ErreurMoteur("Aucun modèle sélectionné.")
        return sauvegarder_profil(self.modele_courant, self.profil_courant)

    def profil_existe(self) -> bool:
        return self.modele_courant is not None and existe_profil(self.modele_courant)

    def parametres_generation(self):
        from .moteurs.base import ParametresGeneration
        g = self.config.get("generation", {})
        return ParametresGeneration(
            temperature=float(g.get("temperature", 0.7)),
            top_p=float(g.get("top_p", 0.9)),
            max_tokens=int(g.get("max_tokens", 512)),
            contexte=int(g.get("contexte", 4096)),
            instruction_systeme=g.get("instruction_systeme", ""),
            connaissances=self.connaissances,
        )

    def sauvegarder(self) -> None:
        cfg_module.sauvegarder_config(self.config)


def dossier_apprentissages() -> Path:
    return cfg_module.dossier_donnees() / "apprentissages"
