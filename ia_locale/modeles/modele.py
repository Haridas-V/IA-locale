"""Description d'un modèle détecté localement."""

from dataclasses import dataclass, field
from pathlib import Path


def formater_taille(octets: int) -> str:
    if octets is None:
        return "?"
    valeur = float(octets)
    for unite in ("o", "Kio", "Mio", "Gio", "Tio"):
        if valeur < 1024 or unite == "Tio":
            if unite == "o":
                return f"{int(valeur)} {unite}"
            return f"{valeur:.1f} {unite}"
        valeur /= 1024
    return f"{valeur:.1f} Tio"


def formater_params(params) -> str:
    if not params:
        return "?"
    p = float(params)
    if p >= 1e9:
        return f"{p / 1e9:.1f} Md"
    if p >= 1e6:
        return f"{p / 1e6:.1f} M"
    return f"{int(p)}"


@dataclass
class ModeleInfo:
    id: str
    nom: str
    chemin: Path
    format: str  # "gguf" ou "transformers"
    taille_octets: int = 0
    params: int | None = None
    params_estimes: bool = False
    quantisation: str | None = None
    meta: dict = field(default_factory=dict)

    def resume(self) -> str:
        morceaux = [self.format.upper()]
        if self.format == "gguf" and self.quantisation:
            morceaux.append(self.quantisation)
        morceaux.append(formater_taille(self.taille_octets))
        morceaux.append(f"~{formater_params(self.params)} paramètres")
        return " · ".join(morceaux)
