from pathlib import Path

from ia_locale.modeles.modele import ModeleInfo
from ia_locale.modeles.profil import ProfilMateriel
from ia_locale.modeles import vram

GIO = 1024 ** 3


def modele_gguf_test() -> ModeleInfo:
    return ModeleInfo(
        id="test.gguf",
        nom="Test 7B",
        chemin=Path("/tmp/test.gguf"),
        format="gguf",
        taille_octets=int(4 * GIO),
        params=7_000_000_000,
        meta={
            "blocs": 32,
            "embedding": 4096,
            "tetes": 32,
            "tetes_kv": 8,
            "dimension_tete": 128,
            "octets_tensors": int(4 * GIO),
        },
    )


def profil(**kwargs) -> ProfilMateriel:
    return ProfilMateriel(**kwargs)


def test_kv_par_couche():
    # 2 * 4096 ctx * 8 tetes_kv * 128 dim * 2 octets = 16 Mio = 0.015625 Gio
    assert abs(vram.kv_par_couche_go(4096, 8, 128) - 16 * 1024 * 1024 / GIO) < 1e-9


def test_estimation_inclut_marge_contexte():
    m = modele_gguf_test()
    estim = vram.estimer_vram_go(m, 4096, 32)
    assert estim["poids_go"] == 4.0
    assert estim["kv_go"] == 0.5  # 32 couches * 0.015625
    assert estim["marge_go"] > 0  # marge pour le contexte / le runtime
    assert estim["total_go"] == estim["poids_go"] + estim["kv_go"] + estim["marge_go"]
    assert estim["total_go"] > 4.5


def test_contexte_plus_grand_augmente_vram():
    m = modele_gguf_test()
    petit = vram.estimer_vram_go(m, 2048, 32)["total_go"]
    grand = vram.estimer_vram_go(m, 32768, 32)["total_go"]
    assert grand > petit


def test_couches_dans_budget():
    m = modele_gguf_test()
    assert vram.couches_dans_budget(m, 4096, 6.0) == 32
    couches = vram.couches_dans_budget(m, 4096, 1.0)
    assert 0 < couches < 32
    assert vram.estimer_vram_go(m, 4096, couches)["total_go"] <= 1.0
    assert vram.couches_dans_budget(m, 4096, 0.2) == 0


def test_mode_auto_gpu_quand_ca_tient():
    m = modele_gguf_test()
    d = vram.choisir_mode(m, profil(mode_calcul="auto", budget_vram_go=6.0), 4096)
    assert d.mode == "gpu" and d.couches_gpu == 32


def test_mode_auto_hybride_quand_budget_serre():
    m = modele_gguf_test()
    d = vram.choisir_mode(m, profil(mode_calcul="auto", budget_vram_go=1.0), 4096)
    assert d.mode == "hybride"
    assert 0 < d.couches_gpu < 32
    assert d.vram_estimee_go <= 1.0


def test_mode_auto_cpu_quand_rien_ne_tient():
    m = modele_gguf_test()
    d = vram.choisir_mode(m, profil(mode_calcul="auto", budget_vram_go=0.2), 4096)
    assert d.mode == "cpu" and d.couches_gpu == 0
    assert d.avertissement


def test_mode_gpu_depasse_budget_avertit_et_reduit():
    m = modele_gguf_test()
    d = vram.choisir_mode(m, profil(mode_calcul="gpu", budget_vram_go=1.0), 4096)
    assert d.mode == "hybride" and d.avertissement
    assert d.vram_estimee_go <= 1.0


def test_mode_gpu_plein_si_assez_de_vram():
    m = modele_gguf_test()
    d = vram.choisir_mode(m, profil(mode_calcul="gpu", budget_vram_go=8.0), 4096)
    assert d.mode == "gpu" and d.couches_gpu == 32


def test_mode_hybride_respecte_offload_demande():
    m = modele_gguf_test()
    d = vram.choisir_mode(m, profil(mode_calcul="hybride", budget_vram_go=6.0, offload_couches=10), 4096)
    assert d.mode == "hybride" and d.couches_gpu == 10
    d2 = vram.choisir_mode(m, profil(mode_calcul="hybride", budget_vram_go=6.0, offload_couches=-1), 4096)
    assert d2.couches_gpu == 32


def test_mode_cpu():
    m = modele_gguf_test()
    d = vram.choisir_mode(m, profil(mode_calcul="cpu"), 4096)
    assert d.mode == "cpu" and d.couches_gpu == 0


def test_carte_appareils_transformers():
    p = profil(budget_vram_go=8.0, budget_ram_go=32.0)
    carte = vram.carte_appareils_transformers(p)
    assert carte["device_map"] == "auto"
    assert carte["max_memory"][0] == "8.0GiB"
    assert carte["max_memory"]["cpu"] == "32.0GiB"


def test_decision_transformers():
    m = ModeleInfo(id="d", nom="hf", chemin=Path("/tmp/hf"), format="transformers", taille_octets=10**9)
    d = vram.choisir_mode(m, profil(mode_calcul="hybride", budget_vram_go=4.0, budget_ram_go=8.0), 4096)
    assert d.mode == "hybride"
    assert "auto" in (d.avertissement or "")
