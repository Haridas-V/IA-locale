"""Mode « learn » : l'IA récupère des données sur Internet, avec des limites strictes.

Les pages sont téléchargées, leur texte extrait, tronqué selon les limites
choisies, puis stocké localement. Un résumé final est produit avec une
limite de taille fixée (la « limite de paramètres à la fin du learn »).
Aucune donnée ne quitte la machine : seules des requêtes de lecture sont
envoyées vers les sites indiqués.
"""

import json
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

ENTETES = {"User-Agent": "IA-Locale/1.0 (apprentissage local; lecture seule)"}


class _ExtracteurTexte(HTMLParser):
    _IGNORER = {"script", "style", "noscript", "svg", "head"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._morceaux: list[str] = []
        self._profondeur_ignorer = 0
        self._titre = ""
        self._dans_titre = False

    def handle_starttag(self, balise, attrs):
        if balise in self._IGNORER:
            self._profondeur_ignorer += 1
        if balise == "title":
            self._dans_titre = True
        if balise in ("p", "br", "div", "li", "h1", "h2", "h3", "h4", "tr"):
            self._morceaux.append("\n")

    def handle_endtag(self, balise):
        if balise in self._IGNORER and self._profondeur_ignorer > 0:
            self._profondeur_ignorer -= 1
        if balise == "title":
            self._dans_titre = False

    def handle_data(self, data):
        texte = data.strip()
        if not texte:
            return
        if self._dans_titre:
            self._titre = (self._titre + " " + texte).strip()
            return
        if self._profondeur_ignorer:
            return
        self._morceaux.append(texte + " ")

    def texte(self) -> str:
        brut = "".join(self._morceaux)
        brut = re.sub(r"[ \t]+", " ", brut)
        brut = re.sub(r"\n\s*\n+", "\n\n", brut)
        return brut.strip()


@dataclass
class LimitesApprentissage:
    max_pages: int = 5
    max_caracteres_page: int = 20000
    max_total: int = 100000
    limite_resume: int = 4000  # limite de paramètres (taille) à la fin du learn
    delai_s: int = 15


@dataclass
class SourceApprise:
    url: str
    titre: str
    extrait: str


@dataclass
class ResultatApprentissage:
    sujet: str
    sources: list[SourceApprise] = field(default_factory=list)
    resume: str = ""
    date: str = ""
    fichier: str = ""

    def vers_dict(self) -> dict:
        return {
            "sujet": self.sujet,
            "date": self.date,
            "resume": self.resume,
            "sources": [{"url": s.url, "titre": s.titre, "extrait": s.extrait} for s in self.sources],
        }


class Apprenant:
    def __init__(self, dossier_stockage: Path, limites: LimitesApprentissage):
        self.dossier = Path(dossier_stockage)
        self.dossier.mkdir(parents=True, exist_ok=True)
        self.limites = limites

    def rechercher_urls(self, sujet: str, max_urls: int = 10) -> list[str]:
        """Recherche des URLs via DuckDuckGo (HTML léger)."""
        requete = urllib.parse.urlencode({"q": sujet})
        url = f"https://html.duckduckgo.com/html/?{requete}"
        try:
            html = self._telecharger(url)
        except Exception:
            return []
        urls = []
        for m in re.finditer(r'href="(https?://[^"]+)"', html):
            cible = m.group(1)
            if "duckduckgo.com" in cible:
                continue
            cible = cible.split("uddg=")[-1]
            if "uddg=" in m.group(1):
                cible = urllib.parse.unquote(cible)
            if cible.startswith("http") and cible not in urls:
                urls.append(cible)
            if len(urls) >= max_urls:
                break
        return urls

    def _telecharger(self, url: str) -> str:
        req = urllib.request.Request(url, headers=ENTETES)
        with urllib.request.urlopen(req, timeout=self.limites.delai_s) as reponse:
            donnees = reponse.read(4 * 1024 * 1024)
            charset = reponse.headers.get_content_charset() or "utf-8"
        return donnees.decode(charset, errors="replace")

    def _extraire_texte(self, html: str) -> tuple[str, str]:
        parseur = _ExtracteurTexte()
        parseur.feed(html)
        return parseur.texte(), parseur._titre

    def apprendre(self, sujet: str, urls: list[str] | None = None, on_progression=None) -> ResultatApprentissage:
        limites = self.limites
        if not urls:
            urls = self.rechercher_urls(sujet, max_urls=limites.max_pages)
        urls = urls[: limites.max_pages]
        sources: list[SourceApprise] = []
        total = 0
        for i, url in enumerate(urls):
            if len(sources) >= limites.max_pages or total >= limites.max_total:
                break
            if on_progression:
                on_progression(i + 1, len(urls), url)
            try:
                html = self._telecharger(url)
            except Exception as e:
                if on_progression:
                    on_progression(i + 1, len(urls), f"[échec] {url} : {e}")
                continue
            texte, titre = self._extraire_texte(html)
            reste = limites.max_total - total
            extrait = texte[: min(limites.max_caracteres_page, max(0, reste))]
            total += len(extrait)
            sources.append(SourceApprise(url=url, titre=titre or url, extrait=extrait))
        resume = self._resumer(sujet, sources, limites.limite_resume)
        resultat = ResultatApprentissage(
            sujet=sujet,
            sources=sources,
            resume=resume,
            date=time.strftime("%Y-%m-%d %H:%M:%S"),
        )
        resultat.fichier = str(self._sauvegarder(resultat))
        return resultat

    def _resumer(self, sujet: str, sources: list[SourceApprise], limite: int) -> str:
        """Concatène les extraits avec une limite stricte de taille finale."""
        morceaux = [f"Sujet : {sujet}"]
        for s in sources:
            morceaux.append(f"Source : {s.titre} ({s.url})\n{s.extrait}")
        texte = "\n\n---\n\n".join(morceaux)
        suffixe = "\n… [tronqué à la limite fixée]"
        if len(texte) > limite:
            texte = texte[: max(0, limite - len(suffixe))] + suffixe
        return texte

    def _sauvegarder(self, resultat: ResultatApprentissage) -> Path:
        slug = re.sub(r"[^a-z0-9]+", "-", resultat.sujet.lower()).strip("-")[:50] or "learn"
        horodatage = time.strftime("%Y%m%d-%H%M%S")
        fichier = self.dossier / f"{horodatage}_{slug}.json"
        with fichier.open("w", encoding="utf-8") as f:
            json.dump(resultat.vers_dict(), f, ensure_ascii=False, indent=2)
        dernier = self.dossier / "dernier.json"
        with dernier.open("w", encoding="utf-8") as f:
            json.dump(resultat.vers_dict(), f, ensure_ascii=False, indent=2)
        return fichier

    def dernier_resume(self) -> str | None:
        fichier = self.dossier / "dernier.json"
        if not fichier.is_file():
            return None
        try:
            with fichier.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("resume") or None
        except (OSError, json.JSONDecodeError):
            return None

    def supprimer(self) -> None:
        for fichier in self.dossier.glob("*.json"):
            fichier.unlink()
