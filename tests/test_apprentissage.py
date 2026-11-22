import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from ia_locale.apprentissage import Apprenant, LimitesApprentissage

PAGES = {
    "/p1": "<html><head><title>Page Un</title></head><body><p>" + ("alpha " * 400) + "</p></body></html>",
    "/p2": "<html><head><title>Page Deux</title></head><body><p>" + ("beta " * 400) + "</p></body></html>",
    "/p3": "<html><body><script>var x=1;</script><p>" + ("gamma " * 400) + "</p></body></html>",
    "/p4": "<html><body><p>" + ("delta " * 400) + "</p></body></html>",
}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        page = PAGES.get(self.path)
        if page is None:
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
def serveur_loopback():
    serveur = HTTPServer(("127.0.0.1", 0), Handler)
    port = serveur.server_address[1]
    thread = threading.Thread(target=serveur.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    serveur.shutdown()
    thread.join(timeout=2)


def test_apprendre_avec_limites(tmp_path, serveur_loopback):
    limites = LimitesApprentissage(max_pages=2, max_caracteres_page=500, max_total=800, limite_resume=300, delai_s=5)
    apprenant = Apprenant(tmp_path / "apprentissages", limites)
    urls = [f"{serveur_loopback}/p{i}" for i in (1, 2, 3, 4)]
    resultat = apprenant.apprendre("sujet test", urls=urls)
    assert len(resultat.sources) == 2  # max_pages respecté
    total = sum(len(s.extrait) for s in resultat.sources)
    assert total <= 800  # max_total respecté
    for s in resultat.sources:
        assert len(s.extrait) <= 500  # max par page respecté
        assert "<script>" not in s.extrait  # HTML nettoyé
    assert len(resultat.resume) <= 300  # limite de paramètres à la fin respectée
    assert resultat.sources[0].titre == "Page Un"
    assert resultat.fichier
    with open(resultat.fichier, encoding="utf-8") as f:
        data = json.load(f)
    assert data["sujet"] == "sujet test"
    assert len(data["sources"]) == 2


def test_dernier_resume_et_suppression(tmp_path, serveur_loopback):
    limites = LimitesApprentissage(max_pages=1, max_caracteres_page=2000, max_total=5000, limite_resume=1000)
    apprenant = Apprenant(tmp_path / "apprentissages", limites)
    resultat = apprenant.apprendre("autre sujet", urls=[f"{serveur_loopback}/p1"])
    assert apprenant.dernier_resume() == resultat.resume
    apprenant.supprimer()
    assert apprenant.dernier_resume() is None


def test_page_injoignable_ignoree(tmp_path):
    limites = LimitesApprentissage(max_pages=3, max_caracteres_page=1000, max_total=5000, limite_resume=500, delai_s=2)
    apprenant = Apprenant(tmp_path / "apprentissages", limites)
    resultat = apprenant.apprendre("test", urls=["http://127.0.0.1:1/rien"])
    assert resultat.sources == []
    assert resultat.resume.startswith("Sujet : test")
