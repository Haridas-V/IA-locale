"""Page Bibliothèque : détection des modèles GGUF et Transformers locaux."""

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, QSplitter, QTextBrowser,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from ..modeles import vram
from ..modeles.profil import charger_profil, existe_profil
from ..modeles.modele import formater_params, formater_taille


class PageBibliotheque(QWidget):
    def __init__(self, etat, on_charger, parent=None):
        super().__init__(parent)
        self.etat = etat
        self._on_charger = on_charger
        self._construire()
        self.rafraichir()

    def _construire(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        titre = QLabel("Bibliothèque")
        titre.setObjectName("titre_page")
        layout.addWidget(titre)
        sous = QLabel("Modèles détectés dans le dossier models/ : fichiers .gguf et dossiers Transformers (config.json).")
        sous.setObjectName("sous_titre")
        sous.setWordWrap(True)
        layout.addWidget(sous)

        barre = QHBoxLayout()
        self.label_dossier = QLabel(f"Dossier : {self.etat.dossier_modeles}")
        self.label_dossier.setObjectName("sous_titre")
        self.label_dossier.setWordWrap(True)
        barre.addWidget(self.label_dossier, stretch=1)
        self.bouton_ouvrir = QPushButton("Ouvrir le dossier models/")
        self.bouton_ouvrir.clicked.connect(self._ouvrir_dossier)
        barre.addWidget(self.bouton_ouvrir)
        self.bouton_actualiser = QPushButton("Actualiser")
        self.bouton_actualiser.clicked.connect(self.rafraichir)
        barre.addWidget(self.bouton_actualiser)
        self.bouton_charger = QPushButton("Charger le modèle sélectionné")
        self.bouton_charger.setObjectName("bouton_principal")
        self.bouton_charger.clicked.connect(self._charger_selection)
        barre.addWidget(self.bouton_charger)
        layout.addLayout(barre)

        splitter = QSplitter(Qt.Orientation.Vertical)
        self.arbre = QTreeWidget()
        self.arbre.setHeaderLabels(["Nom", "Format", "Taille", "Paramètres", "Profil matériel"])
        self.arbre.setColumnWidth(0, 260)
        self.arbre.setColumnWidth(1, 110)
        self.arbre.setColumnWidth(2, 90)
        self.arbre.setColumnWidth(3, 120)
        self.arbre.itemSelectionChanged.connect(self._maj_details)
        splitter.addWidget(self.arbre)

        self.details = QTextBrowser()
        self.details.setMinimumHeight(140)
        splitter.addWidget(self.details)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, stretch=1)

        self.label_vide = QLabel("")
        self.label_vide.setObjectName("etat_vide_detail")
        self.label_vide.setWordWrap(True)
        layout.addWidget(self.label_vide)

    def rafraichir(self):
        self.etat.actualiser_modeles()
        self.label_dossier.setText(f"Dossier : {self.etat.dossier_modeles}")
        self.arbre.clear()
        for m in self.etat.modeles:
            profil = charger_profil(m, self.etat.config.get("profil_defaut", {}))
            item = QTreeWidgetItem([
                m.nom,
                m.format.upper() + (f" ({m.quantisation})" if m.quantisation else ""),
                formater_taille(m.taille_octets),
                formater_params(m.params) + (" (est.)" if m.params_estimes else ""),
                profil.resume() if existe_profil(m) else "Profil par défaut",
            ])
            item.setData(0, Qt.ItemDataRole.UserRole, m.id)
            self.arbre.addTopLevelItem(item)
        if not self.etat.modeles:
            self.label_vide.setText(
                "Aucun modèle détecté pour le moment.\n"
                f"Déposez un fichier .gguf ou un dossier de modèle Transformers (contenant config.json) dans :\n"
                f"{self.etat.dossier_modeles}\n"
                "Puis cliquez sur « Actualiser ». L'application fonctionne aussi sans modèle (pages ouvertes, bibliothèque vide)."
            )
            self.details.setHtml("<i>Aucun modèle sélectionné.</i>")
        else:
            self.label_vide.setText("")
        self._maj_details()

    def _ouvrir_dossier(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.etat.dossier_modeles)))

    def _charger_selection(self):
        items = self.arbre.selectedItems()
        if not items:
            return
        id_modele = items[0].data(0, Qt.ItemDataRole.UserRole)
        self.etat.selectionner_modele(id_modele, charger=False)
        ok, message = self.etat.charger_modele()
        self._on_charger(ok, message)

    def _maj_details(self):
        items = self.arbre.selectedItems()
        if not items:
            if self.etat.modeles:
                self.details.setHtml("<i>Sélectionnez un modèle pour voir ses détails et l'estimation VRAM.</i>")
            return
        id_modele = items[0].data(0, Qt.ItemDataRole.UserRole)
        modele = next((m for m in self.etat.modeles if m.id == id_modele), None)
        if modele is None:
            return
        profil = charger_profil(modele, self.etat.config.get("profil_defaut", {}))
        contexte = int(self.etat.config.get("generation", {}).get("contexte", 4096))
        lignes = [f"<b>{modele.nom}</b>", f"Chemin : {modele.chemin}", f"Format : {modele.format}",
                  f"Taille : {formater_taille(modele.taille_octets)}",
                  f"Paramètres : ~{formater_params(modele.params)}"]
        if modele.format == "gguf":
            meta = modele.meta
            if meta.get("blocs"):
                lignes.append(f"Blocs : {meta['blocs']} · embedding : {meta.get('embedding')} · têtes KV : {meta.get('tetes_kv')}")
            decision = vram.choisir_mode(modele, profil, contexte)
            estim = vram.estimer_vram_go(modele, contexte, decision.couches_gpu)
            lignes.append(
                f"<br><b>Estimation VRAM</b> (contexte {contexte}, marge contexte incluse) : "
                f"poids {estim['poids_go']:.2f} Gio + cache KV {estim['kv_go']:.2f} Gio + marge {estim['marge_go']:.2f} Gio "
                f"= <b>{estim['total_go']:.2f} Gio</b> pour {decision.couches_gpu}/{decision.couches_totales} couches sur GPU."
            )
            lignes.append(f"Mode résolu : <b>{decision.mode}</b> (budget {decision.budget_go:.1f} Gio)")
            if decision.avertissement:
                lignes.append(f"<span style='color:#f0c36d'>{decision.avertissement}</span>")
        else:
            carte = vram.carte_appareils_transformers(profil)
            lignes.append(f"<br><b>Carte des appareils</b> : {carte['device_map']} · limites mémoire : GPU {carte['max_memory'][0]}, CPU {carte['max_memory']['cpu']}")
            lignes.append(f"Type : {modele.meta.get('type_modele')} · architectures : {', '.join(modele.meta.get('architectures') or []) or '?'}")
        lignes.append(f"<br>Profil matériel : {profil.resume()} {'(enregistré)' if existe_profil(modele) else '(profil par défaut, non enregistré)'}")
        self.details.setHtml("<br>".join(lignes))
