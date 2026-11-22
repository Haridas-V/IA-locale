"""Génère les icônes PNG (256/512) à partir du SVG via QtSvg."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)
svg = ROOT / "assets" / "icon.svg"
renderer = QSvgRenderer(str(svg))
for taille in (256, 512):
    image = QImage(taille, taille, QImage.Format.Format_ARGB32)
    image.fill(0)
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    sortie = ROOT / "packaging" / f"ia-locale-{taille}.png"
    image.save(str(sortie))
    print("icône écrite :", sortie)
