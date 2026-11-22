from ia_locale.modeles.scanner import scanner_modeles, trouver_modele


def test_scan_detecte_gguf_et_transformers(dossier_modeles_faux):
    modeles = scanner_modeles(dossier_modeles_faux)
    assert len(modeles) == 2
    formats = {m.format for m in modeles}
    assert formats == {"gguf", "transformers"}
    gguf = next(m for m in modeles if m.format == "gguf")
    assert gguf.quantisation == "Q4_K_M"
    assert gguf.params == 7_000_000_000
    assert gguf.meta["blocs"] == 32
    hf = next(m for m in modeles if m.format == "transformers")
    assert hf.meta["type_modele"] == "llama"
    assert hf.taille_octets == 2 * 1024 * 1024
    assert hf.params == 1024 * 1024  # 2 Mio / 2 octets par paramètre


def test_scan_dossier_vide(tmp_path):
    assert scanner_modeles(tmp_path) == []
    assert scanner_modeles(tmp_path / "inexistant") == []


def test_scan_gguf_extension_majuscules(tmp_path):
    from tests.util_gguf import ecrire_gguf, meta_llama_test
    ecrire_gguf(tmp_path / "MODELE.GGUF", meta_llama_test(), [("w", [10, 10], 6)])
    ecrire_gguf(tmp_path / "autre.Gguf", meta_llama_test(), [("w", [10, 10], 6)])
    modeles = scanner_modeles(tmp_path)
    assert len(modeles) == 2
    assert all(m.format == "gguf" for m in modeles)


def test_trouver_modele(dossier_modeles_faux):
    modeles = scanner_modeles(dossier_modeles_faux)
    m = trouver_modele(modeles, "mon-modele-7b-q4_k_m.gguf")
    assert m is not None and m.format == "gguf"
    assert trouver_modele(modeles, "inconnu") is None
    assert trouver_modele(modeles, None) is None
