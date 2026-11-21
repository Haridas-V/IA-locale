"""Dialogue du mode apprentissage (learn) avec limites de paramètres."""

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QDialog, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
    QPushButton, QProgressBar, QSpinBox, QTextBrowser, QVBoxLayout,
)

from ..apprentissage import Apprenant, LimitesApprentissage
from ..etat import dossier_apprentissages


class TravailleurApprentissage(QThread):
    progression = Signal(int, int, str)
    termine = Signal(object)
    erreur = Signal(str)

    def __init__(self, apprenant: Apprenant, sujet: str, urls: list[str], parent=None):
        super().__init__(parent)
        self._apprenant = apprenant
        self._sujet = sujet
        self._urls = urls

    def run(self):
        try:
            resultat = self._apprenant.apprendre(
                self._sujet, self._urls, on_progression=lambda i, n, u: self.progression.emit(i, n, u)
            )
            self.termine.emit(resultat)
        except Exception as e:
            self.erreur.emit(str(e))


class DialogueApprentissage(QDialog):
    def __init__(self, etat, parent=None):
        super().__init__(parent)
        self.etat = etat
        self.setWindowTitle("Mode apprentissage (learn)")
        self.resize(640, 560)
        self._resultat = None
        self._construire()
        self._charger_limites()

    def _construire(self):
        layout = QVBoxLayout(self)
        intro = QLabel(
            "L'IA va chercher des informations sur Internet (recherche automatique ou URLs fournies), "
            "extraire le texte des pages dans les limites ci-dessous, tout stocker localement, "
            "puis produire un résumé tronqué à la « limite de paramètres » fixée en bas. "
            "Nécessite une connexion Internet ; seules des requêtes de lecture sont envoyées."
        )
        intro.setWordWrap(True)
        intro.setObjectName("sous_titre")
        layout.addWidget(intro)

        g = QGridLayout()
        g.addWidget(QLabel("Sujet :"), 0, 0)
        self.edit_sujet = QLineEdit()
        self.edit_sujet.setPlaceholderText("Ex. : actualités récentes sur les batteries sodium-ion")
        g.addWidget(self.edit_sujet, 0, 1)
        g.addWidget(QLabel("URLs (facultatif, une par ligne) :"), 1, 0)
        self.edit_urls = QPlainTextEdit()
        self.edit_urls.setMaximumHeight(70)
        self.edit_urls.setPlaceholderText("https://exemple.org/page1\nhttps://exemple.org/page2")
        g.addWidget(self.edit_urls, 1, 1)
        g.addWidget(QLabel("Pages max :"), 2, 0)
        self.spin_pages = QSpinBox()
        self.spin_pages.setRange(1, 50)
        g.addWidget(self.spin_pages, 2, 1)
        g.addWidget(QLabel("Caractères max par page :"), 3, 0)
        self.spin_page = QSpinBox()
        self.spin_page.setRange(500, 200000)
        self.spin_page.setSingleStep(1000)
        g.addWidget(self.spin_page, 3, 1)
        g.addWidget(QLabel("Caractères max au total :"), 4, 0)
        self.spin_total = QSpinBox()
        self.spin_total.setRange(1000, 1000000)
        self.spin_total.setSingleStep(5000)
        g.addWidget(self.spin_total, 4, 1)
        g.addWidget(QLabel("Limite de paramètres à la fin (résumé, caractères) :"), 5, 0)
        self.spin_resume = QSpinBox()
        self.spin_resume.setRange(200, 50000)
        self.spin_resume.setSingleStep(200)
        g.addWidget(self.spin_resume, 5, 1)
        layout.addLayout(g)

        self.barre = QProgressBar()
        self.barre.setRange(0, 1)
        self.barre.setValue(0)
        layout.addWidget(self.barre)
        self.label_progression = QLabel("Prêt.")
        self.label_progression.setWordWrap(True)
        layout.addWidget(self.label_progression)

        self.zone_resultat = QTextBrowser()
        layout.addWidget(self.zone_resultat, stretch=1)

        boutons = QHBoxLayout()
        self.bouton_lancer = QPushButton("Lancer l'apprentissage")
        self.bouton_lancer.setObjectName("bouton_principal")
        self.bouton_lancer.clicked.connect(self._lancer)
        boutons.addWidget(self.bouton_lancer)
        self.bouton_utiliser = QPushButton("Utiliser ces connaissances dans la discussion")
        self.bouton_utiliser.setEnabled(False)
        self.bouton_utiliser.clicked.connect(self._utiliser)
        boutons.addWidget(self.bouton_utiliser)
        self.bouton_supprimer = QPushButton("Supprimer les apprentissages")
        self.bouton_supprimer.clicked.connect(self._supprimer)
        boutons.addWidget(self.bouton_supprimer)
        self.bouton_fermer = QPushButton("Fermer")
        self.bouton_fermer.clicked.connect(self.reject)
        boutons.addWidget(self.bouton_fermer)
        layout.addLayout(boutons)

    def _charger_limites(self):
        a = self.etat.config.get("apprentissage", {})
        self.spin_pages.setValue(int(a.get("max_pages", 5)))
        self.spin_page.setValue(int(a.get("max_caracteres_page", 20000)))
        self.spin_total.setValue(int(a.get("max_total", 100000)))
        self.spin_resume.setValue(int(a.get("limite_resume", 4000)))

    def _limites(self) -> LimitesApprentissage:
        return LimitesApprentissage(
            max_pages=int(self.spin_pages.value()),
            max_caracteres_page=int(self.spin_page.value()),
            max_total=int(self.spin_total.value()),
            limite_resume=int(self.spin_resume.value()),
            delai_s=int(self.etat.config.get("apprentissage", {}).get("delai_s", 15)),
        )

    def _lancer(self):
        sujet = self.edit_sujet.text().strip()
        if not sujet:
            self.label_progression.setText("Indiquez un sujet (ou des URLs) avant de lancer.")
            return
        urls = [u.strip() for u in self.edit_urls.toPlainText().splitlines() if u.strip()]
        limites = self._limites()
        apprenant = Apprenant(dossier_apprentissages(), limites)
        self.bouton_lancer.setEnabled(False)
        self.barre.setRange(0, max(1, min(limites.max_pages, len(urls) if urls else limites.max_pages)))
        self.label_progression.setText("Apprentissage en cours…")
        self._travailleur = TravailleurApprentissage(apprenant, sujet, urls, self)
        self._travailleur.progression.connect(self._on_progression)
        self._travailleur.termine.connect(self._on_termine)
        self._travailleur.erreur.connect(self._on_erreur)
        self._travailleur.start()

    def _on_progression(self, i: int, n: int, url: str):
        self.barre.setRange(0, max(1, n))
        self.barre.setValue(i)
        self.label_progression.setText(f"Page {i}/{n} : {url[:120]}")

    def _on_termine(self, resultat):
        self._resultat = resultat
        self.bouton_lancer.setEnabled(True)
        self.bouton_utiliser.setEnabled(True)
        self.label_progression.setText(
            f"Terminé : {len(resultat.sources)} page(s) lue(s), résumé de {len(resultat.resume)} caractères "
            f"(limite {self.spin_resume.value()}), stocké dans {resultat.fichier}"
        )
        self.zone_resultat.setPlainText(resultat.resume)

    def _on_erreur(self, message: str):
        self.bouton_lancer.setEnabled(True)
        self.label_progression.setText(f"Erreur : {message}")

    def _utiliser(self):
        if self._resultat is not None:
            self.etat.connaissances = self._resultat.resume
        self.accept()

    def _supprimer(self):
        limites = self._limites()
        Apprenant(dossier_apprentissages(), limites).supprimer()
        self.etat.connaissances = None
        self.zone_resultat.setPlainText("")
        self.label_progression.setText("Apprentissages locaux supprimés.")
