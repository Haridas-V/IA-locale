"""Test de fumée de l'interface en mode offscreen avec le moteur de démonstration."""

import time

import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication  # noqa: E402

from ia_locale.ui.fenetre import FenetrePrincipale  # noqa: E402
from ia_locale.modeles.profil import existe_profil  # noqa: E402


@pytest.fixture
def app_qt():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def fenetre(app_qt, etat_tmp, monkeypatch):
    monkeypatch.setenv("IA_LOCALE_MOCK", "1")
    fenetre = FenetrePrincipale(etat_tmp)
    yield fenetre
    fenetre.close()
    fenetre.deleteLater()


def _pomper(app, predicate, delai_max=8.0):
    debut = time.time()
    while time.time() - debut < delai_max:
        app.processEvents()
        if predicate():
            return True
        time.sleep(0.03)
    return predicate()


def test_trois_pages_et_navigation_francaise(fenetre, app_qt):
    assert fenetre.pile.count() == 3
    textes = [b.text() for b in fenetre.boutons_nav]
    assert any("Discussion" in t for t in textes)
    assert any("Bibliothèque" in t for t in textes)
    assert any("Paramètres" in t for t in textes)
    fenetre._aller(1)
    assert fenetre.pile.currentWidget() is fenetre.page_biblio
    fenetre._aller(2)
    assert fenetre.pile.currentWidget() is fenetre.page_parametres
    fenetre._aller(0)
    assert fenetre.pile.currentWidget() is fenetre.page_discussion


def test_bibliotheque_liste_les_modeles(fenetre):
    arbre = fenetre.page_biblio.arbre
    assert arbre.topLevelItemCount() == 2
    formats = {arbre.topLevelItem(i).text(1) for i in range(2)}
    assert any("GGUF" in f for f in formats)
    assert any("TRANSFORMERS" in f for f in formats)


def test_etat_vide_sans_modele_charge(fenetre):
    page = fenetre.page_discussion
    assert not page.saisie.isEnabled()
    assert not page.bouton_envoyer.isEnabled()
    assert page._etat_vide.isVisible() or not page.etat.modele_est_charge()
    assert "Aucun modèle" in page.label_statut.text()


def test_charger_modele_et_discussion(fenetre, app_qt):
    page = fenetre.page_discussion
    id_gguf = next(m.id for m in fenetre.etat.modeles if m.format == "gguf")
    fenetre.etat.selectionner_modele(id_gguf, charger=False)
    page.rafraichir_liste_modeles()
    ok, message = fenetre.etat.charger_modele()
    assert ok, message
    page.maj_etat()
    assert page.saisie.isEnabled()
    assert "Modèle chargé" in page.label_statut.text()

    page.saisie.setPlainText("Bonjour le monde")
    page._on_envoyer()
    assert _pomper(app_qt, lambda: any(m["role"] == "assistant" for m in page.historique))
    reponse = next(m["content"] for m in page.historique if m["role"] == "assistant")
    assert "Bonjour le monde" in reponse

    page.nouvelle_conversation()
    assert page.historique == []


def test_profil_materiel_enregistre_depuis_parametres(fenetre, app_qt):
    page = fenetre.page_discussion
    id_gguf = next(m.id for m in fenetre.etat.modeles if m.format == "gguf")
    fenetre.etat.selectionner_modele(id_gguf, charger=False)
    params = fenetre.page_parametres
    params.maj_profil_modele()
    params.combo_mode.setCurrentIndex(params.combo_mode.findData("hybride"))
    params.spin_vram.setValue(9.5)
    params.spin_threads.setValue(3)
    params.enregistrer_profil()
    assert existe_profil(fenetre.etat.modele_courant)
    assert "enregistré" in params.label_profil.text()
    params.recharger_profil()
    assert params.spin_vram.value() == 9.5
    assert params.combo_mode.currentData() == "hybride"


def test_reglages_generation_sauvegardes(fenetre):
    params = fenetre.page_parametres
    params.combo_prereglage.setCurrentText("Technique")
    g = fenetre.etat.config["generation"]
    assert g["prereglage"] == "Technique"
    assert g["temperature"] == pytest.approx(0.3)
    params.spin_max_tokens.setValue(128)
    assert fenetre.etat.config["generation"]["max_tokens"] == 128


def test_apprentissage_dialogue_s_ouvre(fenetre):
    from ia_locale.ui.dialogue_apprentissage import DialogueApprentissage
    d = DialogueApprentissage(fenetre.etat, fenetre)
    assert d.windowTitle() == "Mode apprentissage (learn)"
    d.deleteLater()
