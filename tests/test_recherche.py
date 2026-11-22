"""Tests de la recherche d'URLs du mode learn (faux moteur de recherche en local)."""

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from ia_locale.apprentissage import Apprenant, LimitesApprentissage


class FauxMoteur(BaseHTTPRequestHandler):
    port = 0

    def do_GET(self):
        if self.path.startswith("/search_local"):
            page = (
                f'<a href="http://127.0.0.1:{self.port}/p1">P1</a>'
                f'<a href="http://127.0.0.1:{self.port}/p2">P2</a>'
            )
        elif self.path.startswith("/search"):
            page = (
                '<a rel="nofollow" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexemple.org%2Fa&rut=xyz">A</a>'
                f'<a href="http://127.0.0.1:{self.port}/p1">P1</a>'
                f'<a href="http://127.0.0.1:{self.port}/p2">P2</a>'
                '<a href="https://www.bing.com/search?q=x">bing</a>'
                '<a href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexemple.org%2Fb">B</a>'
            )
        elif self.path in ("/p1", "/p2"):
            page = f"<html><head><title>{self.path}</title></head><body><p>contenu de {self.path} " + ("mot " * 50) + "</p></body></html>"
        else:
            self.send_response(404)
            self.end_headers()
            return
        data = page.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


@pytest.fixture
def faux_moteur():
    serveur = HTTPServer(("127.0.0.1", 0), FauxMoteur)
    FauxMoteur.port = serveur.server_address[1]
    thread = threading.Thread(target=serveur.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{serveur.server_address[1]}"
    serveur.shutdown()
    thread.join(timeout=2)


def test_recherche_extrait_uddg_et_liens_directs(tmp_path, faux_moteur):
    apprenant = Apprenant(tmp_path / "a", LimitesApprentissage())
    urls = apprenant.rechercher_urls("sujet", max_urls=10, endpoints=[f"{faux_moteur}/search?q={{q}}"])
    assert "https://exemple.org/a" in urls
    assert "https://exemple.org/b" in urls
    assert f"{faux_moteur}/p1" in urls
    assert f"{faux_moteur}/p2" in urls
    assert not any("bing.com" in u or "duckduckgo.com/l/" in u for u in urls)


def test_apprendre_de_bout_en_bout_via_recherche(tmp_path, faux_moteur):
    limites = LimitesApprentissage(max_pages=5, max_caracteres_page=2000, max_total=5000, limite_resume=1500, delai_s=5)
    apprenant = Apprenant(tmp_path / "a", limites)
    resultat = apprenant.apprendre("sujet test", endpoints=[f"{faux_moteur}/search_local?q={{q}}"])
    assert len(resultat.sources) == 2  # p1 et p2 trouvées puis lues
    assert all(s.extrait for s in resultat.sources)
    assert len(resultat.resume) <= limites.limite_resume


def test_diagnostic(etat_tmp, capsys, monkeypatch):
    from ia_locale.main import main
    monkeypatch.setenv("IA_LOCALE_MOCK", "1")
    rc = main(["--diagnostic"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Python utilisé" in out
    assert "llama-cpp-python" in out
    assert "Dossier des modèles" in out
