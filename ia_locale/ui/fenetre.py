"""Fenêtre principale : navigation Discussion / Bibliothèque / Paramètres."""

from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QMainWindow, QPushButton, QSplitter,
    QStackedWidget, QVBoxLayout, QWidget,
)

from .. import NOM_APPLICATION
from .page_biblio import PageBibliotheque
from .page_discussion import PageDiscussion
from .page_parametres import PageParametres


class FenetrePrincipale(QMainWindow):
    def __init__(self, etat, parent=None):
        super().__init__(parent)
        self.etat = etat
        self.setWindowTitle(f"{NOM_APPLICATION} — modèles d'IA locaux")
        self.resize(1080, 700)
        self._construire()
        self.rafraichir_modeles()
        self._aller(0)

    def _construire(self):
        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.barre_laterale = QWidget()
        self.barre_laterale.setObjectName("barre_laterale")
        self.barre_laterale.setFixedWidth(210)
        bl = QVBoxLayout(self.barre_laterale)
        bl.setContentsMargins(10, 10, 10, 10)
        bl.setSpacing(6)
        titre = QLabel(f"✦ {NOM_APPLICATION}")
        titre.setObjectName("titre_app")
        bl.addWidget(titre)
        self.boutons_nav = []
        for texte in ("💬  Discussion", "📚  Bibliothèque", "⚙  Paramètres"):
            b = QPushButton(texte)
            b.setObjectName("bouton_nav")
            b.setCheckable(True)
            bl.addWidget(b)
            self.boutons_nav.append(b)
        self.boutons_nav[0].clicked.connect(lambda: self._aller(0))
        self.boutons_nav[1].clicked.connect(lambda: self._aller(1))
        self.boutons_nav[2].clicked.connect(lambda: self._aller(2))
        bl.addStretch(1)
        self.label_etat = QLabel("Aucun modèle chargé")
        self.label_etat.setObjectName("etat_modele")
        self.label_etat.setWordWrap(True)
        bl.addWidget(self.label_etat)
        layout.addWidget(self.barre_laterale)

        self.pile = QStackedWidget()
        self.page_discussion = PageDiscussion(self.etat)
        self.page_biblio = PageBibliotheque(self.etat, self._apres_chargement)
        self.page_parametres = PageParametres(self.etat)
        self.pile.addWidget(self.page_discussion)
        self.pile.addWidget(self.page_biblio)
        self.pile.addWidget(self.page_parametres)
        layout.addWidget(self.pile, stretch=1)
        self.setCentralWidget(central)

        self.barre_etat = self.statusBar()
        self.barre_etat.showMessage(f"Dossier des modèles : {self.etat.dossier_modeles}")

    def _aller(self, index: int):
        self.pile.setCurrentIndex(index)
        for i, b in enumerate(self.boutons_nav):
            b.setChecked(i == index)
        if index == 1:
            self.page_biblio.rafraichir()
            self.rafraichir_modeles()
        if index == 2:
            self.page_parametres.maj_profil_modele()
        self.maj_etat_bas()

    def rafraichir_modeles(self):
        self.etat.actualiser_modeles()
        self.page_discussion.rafraichir_liste_modeles()
        self.page_biblio.rafraichir()
        self.maj_etat_bas()

    def _apres_chargement(self, ok: bool, message: str):
        self.page_discussion.maj_etat()
        self.page_discussion.rafraichir_liste_modeles()
        self.page_parametres.maj_profil_modele()
        self.barre_etat.showMessage(message, 8000)
        self.maj_etat_bas()
        self._aller(0)

    def maj_etat_bas(self):
        m = self.etat.modele_courant
        if self.etat.modele_est_charge() and m is not None:
            self.label_etat.setText(f"● {m.nom}\n{m.resume()}")
        elif m is not None:
            self.label_etat.setText(f"○ {m.nom} (non chargé)")
        else:
            self.label_etat.setText("Aucun modèle chargé")
