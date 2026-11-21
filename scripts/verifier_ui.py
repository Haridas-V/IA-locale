"""Vérification de démarrage : lance l'app offscreen, parcourt les 3 pages, capture des PNG."""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TMP = Path("/tmp/ia-locale-verif")
TMP.mkdir(parents=True, exist_ok=True)
os.environ["IA_LOCALE_CONFIG"] = str(TMP / "config")
os.environ["IA_LOCALE_DATA"] = str(TMP / "donnees")
os.environ["IA_LOCALE_MOCK"] = "1"
os.environ["QT_QPA_PLATFORM"] = "offscreen"

sys.path.insert(0, str(ROOT / "tests"))
from util_gguf import ecrire_gguf, meta_llama_test  # noqa: E402

models = TMP / "models"
models.mkdir(exist_ok=True)
if not (models / "demo-7b-q4_k_m.gguf").exists():
    ecrire_gguf(models / "demo-7b-q4_k_m.gguf", meta_llama_test(), [("w", [1000, 1000], 6)], octets_donnees=128)
hf = models / "demo-transformers"
hf.mkdir(exist_ok=True)
(hf / "config.json").write_text(json.dumps({"model_type": "llama", "architectures": ["LlamaForCausalLM"]}), encoding="utf-8")
(hf / "model.safetensors").write_bytes(b"\x00" * 1024)

from PySide6.QtCore import Qt, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from ia_locale.etat import EtatApplication  # noqa: E402
from ia_locale.theme import appliquer_theme  # noqa: E402
from ia_locale.ui.fenetre import FenetrePrincipale  # noqa: E402

app = QApplication(sys.argv)
appliquer_theme(app)
etat = EtatApplication()
etat.config["dossier_modeles"] = str(models)
etat.sauvegarder()
etat.actualiser_modeles()
fenetre = FenetrePrincipale(etat)
fenetre.resize(1100, 720)
fenetre.setMinimumSize(1100, 720)
app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
fenetre.show()
print(f"DÉMARRAGE OK — modèles détectés : {len(etat.modeles)} — dossier : {etat.dossier_modeles}", flush=True)

captures = TMP / "captures"
captures.mkdir(exist_ok=True)

etapes = [
    ("01-discussion-vide", 0, None),
    ("02-bibliotheque", 1, None),
    ("03-parametres", 2, None),
]


def charger_et_discuter():
    id_gguf = next(m.id for m in etat.modeles if m.format == "gguf")
    etat.selectionner_modele(id_gguf, charger=True)
    fenetre.rafraichir_modeles()
    page = fenetre.page_discussion
    page.saisie.setPlainText("Bonjour, présente-toi en une phrase.")
    page._on_envoyer()


def attendre_reponse():
    def fini():
        return any(m["role"] == "assistant" for m in fenetre.page_discussion.historique)
    debut = __import__("time").time()
    while __import__("time").time() - debut < 8:
        app.processEvents()
        if fini():
            break
        __import__("time").sleep(0.03)
    app.processEvents()
    fenetre._aller(0)
    fenetre.page_discussion.grab().save(str(captures / "04-discussion-chargee.png"))
    # enregistrer un profil matériel depuis la page Paramètres
    fenetre._aller(2)
    p = fenetre.page_parametres
    p.maj_profil_modele()
    p.combo_mode.setCurrentIndex(p.combo_mode.findData("hybride"))
    p.spin_vram.setValue(7.5)
    p.enregistrer_profil()
    fenetre.page_parametres.grab().save(str(captures / "05-parametres-profil.png"))
    print("PROFIL OK —", p.label_profil.text(), flush=True)
    fenetre._aller(0)


index = [0]


def etape_suivante():
    if index[0] < len(etapes):
        nom, page, _ = etapes[index[0]]
        fenetre._aller(page)
        app.processEvents()
        fenetre.grab().save(str(captures / f"{nom}.png"))
        print(f"PAGE OK — {nom}", flush=True)
        index[0] += 1
        if index[0] == len(etapes):
            charger_et_discuter()
            QTimer.singleShot(300, attendre_reponse)
            QTimer.singleShot(3500, app.quit)
        else:
            QTimer.singleShot(250, etape_suivante)
    else:
        app.quit()


QTimer.singleShot(400, etape_suivante)
code = app.exec()
print("ARRÊT PROPRE, code =", code, flush=True)
sys.exit(0 if code == 0 else 1)
