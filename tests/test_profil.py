from pathlib import Path

from ia_locale.modeles.modele import ModeleInfo
from ia_locale.modeles.profil import (
    ProfilMateriel, charger_profil, existe_profil, sauvegarder_profil, supprimer_profil, chemin_profil,
)


def modele_gguf(tmp_path) -> ModeleInfo:
    return ModeleInfo(id="m.gguf", nom="m", chemin=tmp_path / "m.gguf", format="gguf", taille_octets=10)


def modele_dossier(tmp_path) -> ModeleInfo:
    d = tmp_path / "hf"
    d.mkdir()
    return ModeleInfo(id="hf", nom="hf", chemin=d, format="transformers", taille_octets=10)


def test_sauvegarde_et_rechargement_gguf(tmp_path):
    m = modele_gguf(tmp_path)
    p = ProfilMateriel(mode_calcul="hybride", budget_vram_go=8.5, budget_ram_go=24.0, offload_couches=12, threads_cpu=6)
    assert not existe_profil(m)
    fichier = sauvegarder_profil(m, p)
    assert fichier.is_file()
    assert existe_profil(m)
    relu = charger_profil(m, {"mode_calcul": "cpu"})
    assert relu.mode_calcul == "hybride"
    assert relu.budget_vram_go == 8.5
    assert relu.offload_couches == 12
    assert relu.threads_cpu == 6


def test_sauvegarde_et_rechargement_dossier(tmp_path):
    m = modele_dossier(tmp_path)
    p = ProfilMateriel(mode_calcul="gpu", budget_vram_go=12.0, offload_couches=-1, threads_cpu=8)
    sauvegarder_profil(m, p)
    assert chemin_profil(m) == m.chemin / "profil_materiel.json"
    relu = charger_profil(m)
    assert relu.mode_calcul == "gpu" and relu.offload_couches == -1


def test_profil_invalide_retombe_sur_defaut(tmp_path):
    m = modele_gguf(tmp_path)
    sauvegarder_profil(m, ProfilMateriel(mode_calcul="gpu"))
    fichier = chemin_profil(m)
    fichier.write_text('{"mode_calcul": "nimportequoi", "budget_vram_go": "beaucoup", "champs_inconnu": 1}', encoding="utf-8")
    relu = charger_profil(m, {"mode_calcul": "cpu", "threads_cpu": 2})
    assert relu.mode_calcul == "auto"
    assert relu.threads_cpu >= 1


def test_supprimer_profil(tmp_path):
    m = modele_gguf(tmp_path)
    sauvegarder_profil(m, ProfilMateriel())
    assert supprimer_profil(m) is True
    assert not existe_profil(m)
    assert supprimer_profil(m) is False


def test_resume_en_francais(tmp_path):
    p = ProfilMateriel(mode_calcul="hybride", budget_vram_go=6.0, budget_ram_go=16.0, offload_couches=-1, threads_cpu=4)
    r = p.resume()
    assert "Hybride" in r and "VRAM 6.0 Gio" in r and "toutes" in r and "4 fils CPU" in r
