"""Page Paramètres : génération, matériel (profils par modèle), dossier, apprentissage."""

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFileDialog, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QPushButton,
    QScrollArea, QSlider, QSpinBox, QVBoxLayout, QWidget,
)

from ..modeles import vram
from ..modeles.profil import MODES_CALCUL, ProfilMateriel, sauvegarder_profil, existe_profil, charger_profil
from .dialogue_apprentissage import DialogueApprentissage

PREREGLAGES = {
    "Neutre": {
        "instruction": "Tu es un assistant utile, clair et concis. Réponds en français.",
        "temperature": 0.7, "top_p": 0.9, "max_tokens": 512,
    },
    "Créatif": {
        "instruction": "Tu es un assistant créatif et imaginatif. Réponds en français avec des formulations originales.",
        "temperature": 0.95, "top_p": 0.95, "max_tokens": 1024,
    },
    "Technique": {
        "instruction": "Tu es un assistant technique et factuel. Cite les étapes, sois précis. Réponds en français.",
        "temperature": 0.3, "top_p": 0.8, "max_tokens": 1024,
    },
    "Pédagogique": {
        "instruction": "Tu es un enseignant patient. Explique pas à pas, avec des exemples simples. Réponds en français.",
        "temperature": 0.6, "top_p": 0.9, "max_tokens": 1024,
    },
    "Concis": {
        "instruction": "Tu réponds en quelques phrases courtes et directes, sans fioritures. Réponds en français.",
        "temperature": 0.4, "top_p": 0.85, "max_tokens": 256,
    },
}

MODES_AFFICHAGE = {"auto": "Auto", "cpu": "CPU", "gpu": "GPU", "hybride": "Hybride"}
CONTEXTES = [1024, 2048, 4096, 8192, 16384, 32768, 65536]


class PageParametres(QWidget):
    def __init__(self, etat, parent=None):
        super().__init__(parent)
        self.etat = etat
        self._construire()
        self.charger_depuis_config()

    def _construire(self):
        externe = QVBoxLayout(self)
        externe.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        contenu = QWidget()
        layout = QVBoxLayout(contenu)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        titre = QLabel("Paramètres")
        titre.setObjectName("titre_page")
        layout.addWidget(titre)

        layout.addWidget(self._groupe_generation())
        layout.addWidget(self._groupe_materiel())
        layout.addWidget(self._groupe_dossier())
        layout.addWidget(self._groupe_apprentissage())
        layout.addStretch(1)
        scroll.setWidget(contenu)
        externe.addWidget(scroll)

    def _groupe_generation(self) -> QGroupBox:
        groupe = QGroupBox("Réglages de génération")
        g = QGridLayout(groupe)
        g.setColumnStretch(1, 1)

        g.addWidget(QLabel("Préréglage de style :"), 0, 0)
        self.combo_prereglage = QComboBox()
        self.combo_prereglage.addItems(list(PREREGLAGES.keys()))
        self.combo_prereglage.currentTextChanged.connect(self._on_prereglage)
        g.addWidget(self.combo_prereglage, 0, 1)

        g.addWidget(QLabel("Instruction système :"), 1, 0)
        self.edit_instruction = QPlainTextEdit()
        self.edit_instruction.setMaximumHeight(90)
        self.edit_instruction.textChanged.connect(self._sauvegarder_generation)
        g.addWidget(self.edit_instruction, 1, 1)

        self.slider_temperature, self.spin_temperature = self._ligne_curseur(
            g, 2, "Température :", 0.0, 2.0, 0.05, "Plus créatif ← → plus factuel"
        )
        self.slider_temperature.valueChanged.connect(
            lambda v: self.spin_temperature.setValue(v / 100))
        self.spin_temperature.valueChanged.connect(
            lambda v: self.slider_temperature.setValue(int(round(v * 100))))
        self.spin_temperature.valueChanged.connect(self._sauvegarder_generation)

        self.slider_top_p, self.spin_top_p = self._ligne_curseur(
            g, 3, "Top-p :", 0.0, 1.0, 0.05, "Diversité des réponses"
        )
        self.slider_top_p.valueChanged.connect(lambda v: self.spin_top_p.setValue(v / 100))
        self.spin_top_p.valueChanged.connect(lambda v: self.slider_top_p.setValue(int(round(v * 100))))
        self.spin_top_p.valueChanged.connect(self._sauvegarder_generation)

        g.addWidget(QLabel("Nombre maximal de tokens :"), 4, 0)
        self.spin_max_tokens = QSpinBox()
        self.spin_max_tokens.setRange(16, 8192)
        self.spin_max_tokens.setSingleStep(64)
        self.spin_max_tokens.valueChanged.connect(self._sauvegarder_generation)
        g.addWidget(self.spin_max_tokens, 4, 1)

        g.addWidget(QLabel("Contexte (tokens) :"), 5, 0)
        self.combo_contexte = QComboBox()
        self.combo_contexte.setEditable(True)
        for c in CONTEXTES:
            self.combo_contexte.addItem(str(c), c)
        self.combo_contexte.currentIndexChanged.connect(self._sauvegarder_generation)
        g.addWidget(self.combo_contexte, 5, 1)
        return groupe

    def _ligne_curseur(self, parent_layout, ligne, label, mini, maxi, pas, conseil):
        etiquette = QLabel(label)
        etiquette.setToolTip(conseil)
        parent_layout.addWidget(etiquette, ligne, 0)
        h = QHBoxLayout()
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(int(mini * 100), int(maxi * 100))
        slider.setToolTip(conseil)
        spin = QDoubleSpinBox()
        spin.setRange(mini, maxi)
        spin.setSingleStep(pas)
        spin.setDecimals(2)
        h.addWidget(slider, stretch=1)
        h.addWidget(spin)
        parent_layout.addLayout(h, ligne, 1)
        return slider, spin

    def _groupe_materiel(self) -> QGroupBox:
        groupe = QGroupBox("Matériel et calcul (profil propre à chaque modèle)")
        g = QGridLayout(groupe)
        g.setColumnStretch(1, 1)

        g.addWidget(QLabel("Mode de calcul :"), 0, 0)
        self.combo_mode = QComboBox()
        for mode in MODES_CALCUL:
            self.combo_mode.addItem(MODES_AFFICHAGE[mode], mode)
        self.combo_mode.currentIndexChanged.connect(self._maj_explication_materielle)
        g.addWidget(self.combo_mode, 0, 1)

        g.addWidget(QLabel("Budget mémoire GPU (Gio) :"), 1, 0)
        self.spin_vram = QDoubleSpinBox()
        self.spin_vram.setRange(0.5, 128.0)
        self.spin_vram.setSingleStep(0.5)
        self.spin_vram.setDecimals(1)
        g.addWidget(self.spin_vram, 1, 1)

        g.addWidget(QLabel("Mémoire CPU max (Gio) :"), 2, 0)
        self.spin_ram = QDoubleSpinBox()
        self.spin_ram.setRange(0.5, 512.0)
        self.spin_ram.setSingleStep(1.0)
        self.spin_ram.setDecimals(1)
        g.addWidget(self.spin_ram, 2, 1)

        g.addWidget(QLabel("Offload des couches (GGUF) :"), 3, 0)
        h = QHBoxLayout()
        self.slider_couches = QSlider(Qt.Orientation.Horizontal)
        self.slider_couches.setRange(0, 120)
        self.slider_couches.setValue(120)
        self.label_couches = QLabel("Toutes les couches")
        self.slider_couches.valueChanged.connect(self._maj_label_couches)
        h.addWidget(self.slider_couches, stretch=1)
        h.addWidget(self.label_couches)
        g.addLayout(h, 3, 1)

        g.addWidget(QLabel("Threads CPU :"), 4, 0)
        self.spin_threads = QSpinBox()
        self.spin_threads.setRange(1, max(1, os.cpu_count() or 1))
        g.addWidget(self.spin_threads, 4, 1)

        self.label_explication = QLabel("")
        self.label_explication.setWordWrap(True)
        self.label_explication.setObjectName("sous_titre")
        g.addWidget(self.label_explication, 5, 0, 1, 2)

        boutons = QHBoxLayout()
        self.bouton_appliquer = QPushButton("Appliquer au modèle courant")
        self.bouton_appliquer.clicked.connect(self.appliquer_au_modele)
        boutons.addWidget(self.bouton_appliquer)
        self.bouton_enregistrer = QPushButton("Enregistrer comme profil du modèle")
        self.bouton_enregistrer.setObjectName("bouton_principal")
        self.bouton_enregistrer.clicked.connect(self.enregistrer_profil)
        boutons.addWidget(self.bouton_enregistrer)
        self.bouton_recharger = QPushButton("Recharger le profil du modèle")
        self.bouton_recharger.clicked.connect(self.recharger_profil)
        boutons.addWidget(self.bouton_recharger)
        g.addLayout(boutons, 6, 0, 1, 2)

        self.label_profil = QLabel("")
        self.label_profil.setWordWrap(True)
        g.addWidget(self.label_profil, 7, 0, 1, 2)
        self._maj_explication_materielle()
        return groupe

    def _groupe_dossier(self) -> QGroupBox:
        groupe = QGroupBox("Dossier des modèles (models/)")
        h = QHBoxLayout(groupe)
        self.edit_dossier = QLineEdit()
        self.edit_dossier.setPlaceholderText("Laisser vide pour utiliser models/ à côté de l'application")
        h.addWidget(self.edit_dossier, stretch=1)
        b_parcourir = QPushButton("Parcourir…")
        b_parcourir.clicked.connect(self._parcourir_dossier)
        h.addWidget(b_parcourir)
        b_appliquer = QPushButton("Appliquer")
        b_appliquer.clicked.connect(self._appliquer_dossier)
        h.addWidget(b_appliquer)
        return groupe

    def _groupe_apprentissage(self) -> QGroupBox:
        groupe = QGroupBox("Mode apprentissage (learn) — limites appliquées à chaque session")
        g = QGridLayout(groupe)
        g.setColumnStretch(1, 1)
        g.addWidget(QLabel("Nombre maximal de pages :"), 0, 0)
        self.spin_max_pages = QSpinBox()
        self.spin_max_pages.setRange(1, 50)
        self.spin_max_pages.valueChanged.connect(self._sauvegarder_apprentissage)
        g.addWidget(self.spin_max_pages, 0, 1)
        g.addWidget(QLabel("Caractères max par page :"), 1, 0)
        self.spin_max_page = QSpinBox()
        self.spin_max_page.setRange(500, 200000)
        self.spin_max_page.setSingleStep(1000)
        self.spin_max_page.valueChanged.connect(self._sauvegarder_apprentissage)
        g.addWidget(self.spin_max_page, 1, 1)
        g.addWidget(QLabel("Caractères max au total :"), 2, 0)
        self.spin_max_total = QSpinBox()
        self.spin_max_total.setRange(1000, 1000000)
        self.spin_max_total.setSingleStep(5000)
        self.spin_max_total.valueChanged.connect(self._sauvegarder_apprentissage)
        g.addWidget(self.spin_max_total, 2, 1)
        g.addWidget(QLabel("Limite du résumé final (caractères) :"), 3, 0)
        self.spin_limite_resume = QSpinBox()
        self.spin_limite_resume.setRange(200, 50000)
        self.spin_limite_resume.setSingleStep(200)
        self.spin_limite_resume.valueChanged.connect(self._sauvegarder_apprentissage)
        g.addWidget(self.spin_limite_resume, 3, 1)
        note = QLabel("Le mode learn télécharge des pages (recherche automatique ou URLs fournies), extrait leur texte "
                      "dans les limites ci-dessus, stocke tout localement, puis produit un résumé tronqué à la limite fixée. "
                      "Nécessite une connexion Internet. Aucune donnée n'est envoyée ailleurs que les requêtes de lecture.")
        note.setWordWrap(True)
        note.setObjectName("sous_titre")
        g.addWidget(note, 4, 0, 1, 2)
        b = QPushButton("Ouvrir le mode apprentissage…")
        b.clicked.connect(lambda: DialogueApprentissage(self.etat, self).exec())
        g.addWidget(b, 5, 0, 1, 2)
        return groupe

    def _maj_label_couches(self, valeur: int):
        if valeur >= self.slider_couches.maximum():
            self.label_couches.setText("Toutes les couches (-1)")
        else:
            self.label_couches.setText(f"{valeur} couches sur GPU")

    def _maj_explication_materielle(self):
        mode = self.combo_mode.currentData()
        if mode == "gpu":
            texte = "GPU : toutes les couches du modèle sont déchargées sur la carte graphique (nécessite un moteur compilé avec le backend adapté : CUDA, Vulkan ou ROCm)."
        elif mode == "hybride":
            texte = "Hybride : le modèle est réparti entre GPU et CPU selon le budget VRAM (GGUF : nombre de couches déchargées ; Transformers : device_map auto + limites mémoire)."
        elif mode == "cpu":
            texte = "CPU : tout le calcul est fait par le processeur (threads CPU réglables ci-dessus). Aucun backend GPU requis."
        else:
            texte = "Auto : GPU si la VRAM estimée (marge pour le contexte incluse) tient dans le budget, sinon répartition hybride GPU/CPU, sinon CPU."
        self.label_explication.setText(texte)

    def _profil_depuis_widgets(self) -> ProfilMateriel:
        couches = self.slider_couches.value()
        return ProfilMateriel(
            mode_calcul=self.combo_mode.currentData() or "auto",
            budget_vram_go=float(self.spin_vram.value()),
            budget_ram_go=float(self.spin_ram.value()),
            offload_couches=-1 if couches >= self.slider_couches.maximum() else couches,
            threads_cpu=int(self.spin_threads.value()),
        )

    def _widgets_depuis_profil(self, profil: ProfilMateriel):
        self.combo_mode.setCurrentIndex(max(0, self.combo_mode.findData(profil.mode_calcul)))
        self.spin_vram.setValue(profil.budget_vram_go)
        self.spin_ram.setValue(profil.budget_ram_go)
        self.slider_couches.setValue(
            self.slider_couches.maximum() if profil.offload_couches < 0 else min(profil.offload_couches, self.slider_couches.maximum())
        )
        self.spin_threads.setValue(profil.threads_cpu)

    def appliquer_au_modele(self):
        m = self.etat.modele_courant
        if m is None:
            self.label_profil.setText("Sélectionnez d'abord un modèle (Discussion ou Bibliothèque).")
            return
        self.etat.profil_courant = self._profil_depuis_widgets()
        decision = vram.choisir_mode(m, self.etat.profil_courant, int(self.etat.config["generation"]["contexte"]))
        self.label_profil.setText(
            f"Appliqué à « {m.nom} » : mode résolu = {decision.mode}, "
            f"{decision.couches_gpu}/{decision.couches_totales} couches GPU, VRAM estimée {decision.vram_estimee_go:.2f} Gio."
        )

    def enregistrer_profil(self):
        m = self.etat.modele_courant
        if m is None:
            self.label_profil.setText("Sélectionnez d'abord un modèle (Discussion ou Bibliothèque).")
            return
        self.etat.profil_courant = self._profil_depuis_widgets()
        fichier = sauvegarder_profil(m, self.etat.profil_courant)
        self.label_profil.setText(f"Profil matériel enregistré pour « {m.nom} » : {fichier}")

    def recharger_profil(self):
        m = self.etat.modele_courant
        if m is None:
            self.label_profil.setText("Sélectionnez d'abord un modèle.")
            return
        profil = charger_profil(m, self.etat.config.get("profil_defaut", {}))
        self.etat.profil_courant = profil
        self._widgets_depuis_profil(profil)
        self.label_profil.setText(
            f"Profil chargé pour « {m.nom} » : {profil.resume()}"
            + (" (enregistré)" if existe_profil(m) else " (profil par défaut)")
        )

    def maj_profil_modele(self):
        """Recharge les widgets depuis le profil du modèle courant (changement de sélection)."""
        m = self.etat.modele_courant
        if m is not None:
            self._widgets_depuis_profil(charger_profil(m, self.etat.config.get("profil_defaut", {})))
            self.label_profil.setText(f"Profil actuel de « {m.nom} » : {self.etat.profil_courant.resume()}")
        else:
            self.label_profil.setText("Aucun modèle sélectionné.")

    def _parcourir_dossier(self):
        dossier = QFileDialog.getExistingDirectory(self, "Choisir le dossier models/", str(self.etat.dossier_modeles))
        if dossier:
            self.edit_dossier.setText(dossier)

    def _appliquer_dossier(self):
        texte = self.edit_dossier.text().strip()
        self.etat.config["dossier_modeles"] = texte or None
        self.etat.sauvegarder()
        self.etat.actualiser_modeles()

    def _on_prereglage(self, nom: str):
        if nom in PREREGLAGES:
            p = PREREGLAGES[nom]
            self.edit_instruction.setPlainText(p["instruction"])
            self.spin_temperature.setValue(p["temperature"])
            self.spin_top_p.setValue(p["top_p"])
            self.spin_max_tokens.setValue(p["max_tokens"])
            self._sauvegarder_generation()

    def _sauvegarder_generation(self):
        g = self.etat.config.setdefault("generation", {})
        g["prereglage"] = self.combo_prereglage.currentText()
        g["instruction_systeme"] = self.edit_instruction.toPlainText()
        g["temperature"] = float(self.spin_temperature.value())
        g["top_p"] = float(self.spin_top_p.value())
        g["max_tokens"] = int(self.spin_max_tokens.value())
        try:
            g["contexte"] = int(self.combo_contexte.currentText())
        except ValueError:
            g["contexte"] = 4096
        self.etat.sauvegarder()

    def _sauvegarder_apprentissage(self):
        a = self.etat.config.setdefault("apprentissage", {})
        a["max_pages"] = int(self.spin_max_pages.value())
        a["max_caracteres_page"] = int(self.spin_max_page.value())
        a["max_total"] = int(self.spin_max_total.value())
        a["limite_resume"] = int(self.spin_limite_resume.value())
        self.etat.sauvegarder()

    def charger_depuis_config(self):
        g = self.etat.config.get("generation", {})
        index = self.combo_prereglage.findText(g.get("prereglage", "Neutre"))
        self.combo_prereglage.setCurrentIndex(index if index >= 0 else 0)
        self.edit_instruction.setPlainText(g.get("instruction_systeme", ""))
        self.spin_temperature.setValue(float(g.get("temperature", 0.7)))
        self.spin_top_p.setValue(float(g.get("top_p", 0.9)))
        self.spin_max_tokens.setValue(int(g.get("max_tokens", 512)))
        contexte = str(int(g.get("contexte", 4096)))
        i = self.combo_contexte.findText(contexte)
        if i >= 0:
            self.combo_contexte.setCurrentIndex(i)
        else:
            self.combo_contexte.setCurrentText(contexte)
        p = self.etat.config.get("profil_defaut", {})
        self._widgets_depuis_profil(ProfilMateriel.depuis_dict(p))
        self.edit_dossier.setText(self.etat.config.get("dossier_modeles") or "")
        a = self.etat.config.get("apprentissage", {})
        self.spin_max_pages.setValue(int(a.get("max_pages", 5)))
        self.spin_max_page.setValue(int(a.get("max_caracteres_page", 20000)))
        self.spin_max_total.setValue(int(a.get("max_total", 100000)))
        self.spin_limite_resume.setValue(int(a.get("limite_resume", 4000)))
        self.maj_profil_modele()
