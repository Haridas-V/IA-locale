"""Point d'entrée de l'application IA Locale."""

import argparse
import sys

from PySide6.QtWidgets import QApplication

from . import NOM_APPLICATION, __version__
from .etat import EtatApplication
from .theme import appliquer_theme
from .ui.fenetre import FenetrePrincipale


def analyser_arguments(argv=None):
    parser = argparse.ArgumentParser(
        prog="ia-locale",
        description=f"{NOM_APPLICATION} {__version__} — utilisez des modèles d'IA locaux (GGUF, Transformers) sans navigateur.",
    )
    parser.add_argument("--dossier-modeles", help="Dossier models/ à utiliser (sinon détection automatique).")
    parser.add_argument("--mock", action="store_true", help="Moteur de démonstration (tests, aucun vrai modèle requis).")
    parser.add_argument("--auto-test", action="store_true", help="Affiche la fenêtre puis quitte après 3 s (vérification de démarrage).")
    parser.add_argument("--diagnostic", action="store_true", help="Affiche Python, moteurs disponibles et modèles détectés, puis quitte.")
    parser.add_argument("--version", action="version", version=f"{NOM_APPLICATION} {__version__}")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = analyser_arguments(argv)
    if args.mock:
        import os
        os.environ["IA_LOCALE_MOCK"] = "1"

    etat = EtatApplication()
    if args.diagnostic:
        import importlib
        print(f"{NOM_APPLICATION} {__version__} — diagnostic")
        print("Python utilisé :", sys.executable)
        print("Version Python :", sys.version.split()[0])
        for label, module in (("llama-cpp-python (GGUF)", "llama_cpp"),
                              ("transformers", "transformers"),
                              ("torch", "torch"),
                              ("accelerate", "accelerate")):
            try:
                mod = importlib.import_module(module)
                print(f"  {label} : OK ({getattr(mod, '__version__', '?')})")
            except ImportError:
                print(f"  {label} : ABSENT → {sys.executable} -m pip install {module.replace('_', '-') if module == 'llama_cpp' else module}")
        print("Dossier des modèles :", etat.dossier_modeles)
        if etat.modeles:
            for m in etat.modeles:
                print("  -", m.nom, "|", m.resume())
        else:
            print("  (aucun modèle détecté)")
        return 0

    app = QApplication(sys.argv)
    app.setApplicationName("ia-locale")
    app.setOrganizationName("ia-locale")
    app.setApplicationDisplayName(NOM_APPLICATION)
    appliquer_theme(app)

    if args.dossier_modeles:
        etat.config["dossier_modeles"] = args.dossier_modeles
        etat.sauvegarder()
        etat.actualiser_modeles()

    fenetre = FenetrePrincipale(etat)
    fenetre.show()
    print(f"{NOM_APPLICATION} {__version__} démarré — dossier des modèles : {etat.dossier_modeles}", flush=True)
    print(f"{len(etat.modeles)} modèle(s) détecté(s).", flush=True)
    if args.auto_test:
        from PySide6.QtCore import QTimer
        QTimer.singleShot(3000, app.quit)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
