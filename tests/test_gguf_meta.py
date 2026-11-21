from pathlib import Path

from ia_locale.modeles.gguf_meta import ErreurGGUF, lire_entete_gguf
from tests.util_gguf import ecrire_gguf, meta_llama_test


def test_lecture_entete_gguf(tmp_path: Path):
    tensors = [
        ("tok_embeddings.weight", [32000, 4096], 6),
        ("layers.0.weight", [4096, 4096], 6),
    ]
    fichier = ecrire_gguf(tmp_path / "test.gguf", meta_llama_test(), tensors)
    entete = lire_entete_gguf(fichier)
    assert entete["architecture"] == "llama"
    assert entete["nom"] == "Modele Test 7B"
    assert entete["blocs"] == 32
    assert entete["embedding"] == 4096
    assert entete["tetes"] == 32
    assert entete["tetes_kv"] == 8
    assert entete["dimension_tete"] == 128
    assert entete["parametres_declares"] == 7_000_000_000
    attendu = (32000 * 4096 + 4096 * 4096) * 4
    assert entete["octets_tensors"] == attendu


def test_fichier_non_gguf(tmp_path: Path):
    fichier = tmp_path / "faux.gguf"
    fichier.write_bytes(b"PAS GGUF" + b"\x00" * 64)
    try:
        lire_entete_gguf(fichier)
        assert False, "devrait lever ErreurGGUF"
    except ErreurGGUF:
        pass
