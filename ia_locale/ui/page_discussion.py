"""Page Discussion : historique, saisie, états du modèle chargé."""

from PySide6.QtCore import QThread, Qt, QTimer, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QPlainTextEdit,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)


class ZoneSaisie(QPlainTextEdit):
    entree_pressee = Signal()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not (
            event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        ):
            self.entree_pressee.emit()
            return
        super().keyPressEvent(event)

from ..moteurs.base import ErreurMoteur
from ..moteurs.registre import disponibilite
from .dialogue_apprentissage import DialogueApprentissage


class TravailleurDiscussion(QThread):
    morceau = Signal(str)
    termine = Signal(str)
    erreur = Signal(str)

    def __init__(self, moteur, messages, params, parent=None):
        super().__init__(parent)
        self._moteur = moteur
        self._messages = messages
        self._params = params

    def run(self):
        try:
            texte = self._moteur.repondre(
                self._messages, self._params, on_token=self.morceau.emit
            )
            self.termine.emit(texte)
        except ErreurMoteur as e:
            self.erreur.emit(str(e))
        except Exception as e:
            self.erreur.emit(f"Erreur pendant la génération : {e}")


class PageDiscussion(QWidget):
    def __init__(self, etat, parent=None):
        super().__init__(parent)
        self.etat = etat
        self.historique: list[dict] = []
        self._travailleur: TravailleurDiscussion | None = None
        self._bulle_en_cours: QLabel | None = None
        self._construire()
        self.maj_etat()

    def _construire(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        titre = QLabel("Discussion")
        titre.setObjectName("titre_page")
        layout.addWidget(titre)

        barre = QFrame()
        barre.setObjectName("bandeau")
        barre_layout = QHBoxLayout(barre)
        barre_layout.setContentsMargins(10, 8, 10, 8)
        barre_layout.setSpacing(8)
        barre_layout.addWidget(QLabel("Modèle :"))
        self.combo_modeles = QComboBox()
        self.combo_modeles.setMinimumWidth(260)
        self.combo_modeles.currentIndexChanged.connect(self._on_changement_modele)
        barre_layout.addWidget(self.combo_modeles)
        self.bouton_charger = QPushButton("Charger")
        self.bouton_charger.setObjectName("bouton_principal")
        self.bouton_charger.clicked.connect(self._on_charger)
        barre_layout.addWidget(self.bouton_charger)
        self.bouton_decharger = QPushButton("Décharger")
        self.bouton_decharger.setObjectName("bouton_secondaire")
        self.bouton_decharger.clicked.connect(self._on_decharger)
        barre_layout.addWidget(self.bouton_decharger)
        barre_layout.addStretch(1)
        self.bouton_apprentissage = QPushButton("Mode apprentissage…")
        self.bouton_apprentissage.setObjectName("bouton_secondaire")
        self.bouton_apprentissage.clicked.connect(self._ouvrir_apprentissage)
        barre_layout.addWidget(self.bouton_apprentissage)
        self.bouton_nouvelle = QPushButton("Nouvelle conversation")
        self.bouton_nouvelle.setObjectName("bouton_secondaire")
        self.bouton_nouvelle.clicked.connect(self.nouvelle_conversation)
        barre_layout.addWidget(self.bouton_nouvelle)
        layout.addWidget(barre)

        self.label_statut = QLabel("")
        self.label_statut.setWordWrap(True)
        layout.addWidget(self.label_statut)

        barre2 = QHBoxLayout()
        barre2.addWidget(QLabel("Connaissances :"))
        self.combo_connaissances = QComboBox()
        self.combo_connaissances.addItem("Aucune", None)
        self.combo_connaissances.currentIndexChanged.connect(self._on_connaissances)
        barre2.addWidget(self.combo_connaissances)
        barre2.addStretch(1)
        layout.addLayout(barre2)

        self.zone_historique = QScrollArea()
        self.zone_historique.setWidgetResizable(True)
        conteneur = QWidget()
        self.layout_bulles = QVBoxLayout(conteneur)
        self.layout_bulles.setContentsMargins(8, 8, 8, 8)
        self.layout_bulles.setSpacing(8)
        self.layout_bulles.addStretch(1)
        self.zone_historique.setWidget(conteneur)
        layout.addWidget(self.zone_historique, stretch=1)

        self._etat_vide = QWidget()
        ev_layout = QVBoxLayout(self._etat_vide)
        ev_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t = QLabel("Aucun modèle chargé")
        t.setObjectName("etat_vide_titre")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        d = QLabel("Rendez-vous dans la Bibliothèque pour choisir un modèle, puis cliquez sur « Charger ».\n"
                   "Vous pouvez aussi déposer un fichier .gguf ou un dossier Transformers dans le dossier models/.")
        d.setObjectName("etat_vide_detail")
        d.setAlignment(Qt.AlignmentFlag.AlignCenter)
        d.setWordWrap(True)
        ev_layout.addWidget(t)
        ev_layout.addWidget(d)
        self.layout_bulles.insertWidget(0, self._etat_vide)

        bas = QHBoxLayout()
        self.saisie = ZoneSaisie()
        self.saisie.setPlaceholderText("Écrivez votre message… (Entrée pour envoyer, Maj+Entrée pour un saut de ligne)")
        self.saisie.setMaximumHeight(110)
        self.saisie.entree_pressee.connect(self._on_envoyer)
        bas.addWidget(self.saisie, stretch=1)
        self.bouton_envoyer = QPushButton("Envoyer")
        self.bouton_envoyer.setObjectName("bouton_principal")
        self.bouton_envoyer.clicked.connect(self._on_envoyer)
        bas.addWidget(self.bouton_envoyer)
        layout.addLayout(bas)

    def rafraichir_liste_modeles(self):
        courant = self.etat.modele_courant.id if self.etat.modele_courant else None
        self.combo_modeles.blockSignals(True)
        self.combo_modeles.clear()
        for m in self.etat.modeles:
            self.combo_modeles.addItem(f"{m.nom}  ({m.resume()})", m.id)
        index = self.combo_modeles.findData(courant) if courant else -1
        self.combo_modeles.setCurrentIndex(index if index >= 0 else (0 if self.combo_modeles.count() else -1))
        self.combo_modeles.blockSignals(False)
        self.maj_etat()

    def _on_changement_modele(self):
        id_modele = self.combo_modeles.currentData()
        if id_modele:
            self.etat.selectionner_modele(id_modele, charger=False)
            self.maj_etat()

    def _on_charger(self):
        id_modele = self.combo_modeles.currentData()
        if id_modele and not self.etat.modele_courant or (self.etat.modele_courant and self.etat.modele_courant.id != id_modele):
            self.etat.selectionner_modele(id_modele, charger=False)
        ok, message = self.etat.charger_modele()
        self.label_statut.setText(message)
        self.label_statut.setObjectName("avertissement" if not ok else "info")
        self.style().unpolish(self.label_statut)
        self.style().polish(self.label_statut)
        self.maj_etat()

    def _on_decharger(self):
        self.etat.decharger_modele()
        self.maj_etat()

    def _on_connaissances(self):
        valeur = self.combo_connaissances.currentData()
        if valeur == "dernier":
            from ..apprentissage import Apprenant, LimitesApprentissage
            from ..etat import dossier_apprentissages
            limites = LimitesApprentissage(**self.etat.config.get("apprentissage", {}))
            resume = Apprenant(dossier_apprentissages(), limites).dernier_resume()
            self.etat.connaissances = resume
        else:
            self.etat.connaissances = None

    def _ouvrir_apprentissage(self):
        dialogue = DialogueApprentissage(self.etat, self)
        dialogue.exec()
        if self.etat.connaissances:
            index = self.combo_connaissances.findData("dernier")
            if index < 0:
                self.combo_connaissances.addItem("Dernières connaissances apprises (mode learn)", "dernier")
                index = self.combo_connaissances.findData("dernier")
            self.combo_connaissances.setCurrentIndex(index)

    def maj_etat(self):
        charge = self.etat.modele_est_charge()
        m = self.etat.modele_courant
        if charge and m is not None:
            self.label_statut.setText(f"Modèle chargé : {m.nom} — {m.resume()}")
            self.label_statut.setObjectName("info")
        elif m is not None:
            ok, dispo = disponibilite(m)
            if ok:
                self.label_statut.setText(f"Modèle sélectionné : {m.nom} — cliquez sur « Charger ».")
                self.label_statut.setObjectName("")
            else:
                self.label_statut.setText(dispo)
                self.label_statut.setObjectName("avertissement")
        else:
            self.label_statut.setText("Aucun modèle chargé.")
            self.label_statut.setObjectName("avertissement")
        self.style().unpolish(self.label_statut)
        self.style().polish(self.label_statut)
        self._etat_vide.setVisible(not charge)
        self.saisie.setEnabled(charge)
        self.bouton_envoyer.setEnabled(charge and self._travailleur is None)
        self.bouton_charger.setEnabled(m is not None)
        self.bouton_decharger.setEnabled(charge)

    def nouvelle_conversation(self):
        self.historique = []
        self._bulle_en_cours = None
        while self.layout_bulles.count() > 1:
            item = self.layout_bulles.takeAt(0)
            w = item.widget()
            if w is not None and w is not self._etat_vide:
                w.deleteLater()
        self.maj_etat()

    def _ajouter_bulle(self, role: str, texte: str) -> QLabel:
        conteneur = QFrame()
        conteneur.setObjectName("bulle_utilisateur" if role == "user" else "bulle_assistant")
        cl = QVBoxLayout(conteneur)
        cl.setContentsMargins(10, 8, 10, 8)
        cl.setSpacing(2)
        role_label = QLabel("Vous" if role == "user" else "Assistant")
        role_label.setObjectName("bulle_role")
        texte_label = QLabel(texte)
        texte_label.setObjectName("bulle_texte")
        texte_label.setWordWrap(True)
        texte_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        cl.addWidget(role_label)
        cl.addWidget(texte_label)
        self.layout_bulles.insertWidget(self.layout_bulles.count() - 1, conteneur)
        QTimer.singleShot(0, self._defiler_bas)
        return texte_label

    def _defiler_bas(self):
        barre = self.zone_historique.verticalScrollBar()
        barre.setValue(barre.maximum())

    def _on_envoyer(self):
        if not self.etat.modele_est_charge() or self._travailleur is not None:
            return
        texte = self.saisie.toPlainText().strip()
        if not texte:
            return
        self.saisie.clear()
        self._ajouter_bulle("user", texte)
        self.historique.append({"role": "user", "content": texte})
        params = self.etat.parametres_generation()
        self._bulle_en_cours = self._ajouter_bulle("assistant", "…")
        self.bouton_envoyer.setEnabled(False)
        self._travailleur = TravailleurDiscussion(self.etat.moteur, list(self.historique), params, self)
        self._travailleur.morceau.connect(self._on_morceau)
        self._travailleur.termine.connect(self._on_termine)
        self._travailleur.erreur.connect(self._on_erreur)
        self._travailleur.start()

    def _on_morceau(self, delta: str):
        if self._bulle_en_cours is not None:
            texte = self._bulle_en_cours.text()
            if texte == "…":
                texte = ""
            self._bulle_en_cours.setText(texte + delta)
            QTimer.singleShot(0, self._defiler_bas)

    def _on_termine(self, texte: str):
        if self._bulle_en_cours is not None:
            self._bulle_en_cours.setText(texte)
        self.historique.append({"role": "assistant", "content": texte})
        self._bulle_en_cours = None
        self._travailleur = None
        self.maj_etat()

    def _on_erreur(self, message: str):
        if self._bulle_en_cours is not None:
            self._bulle_en_cours.setText(f"Erreur : {message}")
        self._bulle_en_cours = None
        self._travailleur = None
        self.maj_etat()
