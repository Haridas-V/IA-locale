"""Utilitaire de test : écrit un faux fichier GGUF avec un en-tête valide."""

import struct
from pathlib import Path

T_F32 = 6
T_STRING = 8
T_UINT32 = 4


def _s(texte: str) -> bytes:
    b = texte.encode("utf-8")
    return struct.pack("<Q", len(b)) + b


def ecrire_gguf(chemin: Path, meta: dict, tensors: list[tuple[str, list[int], int]] | None = None,
                octets_donnees: int = 0) -> Path:
    tensors = tensors or []
    out = bytearray()
    out += b"GGUF"
    out += struct.pack("<I", 3)
    out += struct.pack("<Q", len(tensors))
    out += struct.pack("<Q", len(meta))
    for cle, valeur in meta.items():
        out += _s(cle)
        if isinstance(valeur, str):
            out += struct.pack("<I", T_STRING) + _s(valeur)
        elif isinstance(valeur, bool):
            out += struct.pack("<I", 7) + (b"\x01" if valeur else b"\x00")
        elif isinstance(valeur, float):
            out += struct.pack("<I", 6) + struct.pack("<f", valeur)
        else:
            entier = int(valeur)
            if entier > 0xFFFFFFFF or entier < 0:
                out += struct.pack("<I", 10) + struct.pack("<Q", entier & 0xFFFFFFFFFFFFFFFF)
            else:
                out += struct.pack("<I", T_UINT32) + struct.pack("<I", entier)
    for nom, dims, type_t in tensors:
        out += _s(nom)
        out += struct.pack("<I", len(dims))
        for d in dims:
            out += struct.pack("<Q", d)
        out += struct.pack("<I", type_t)
        out += struct.pack("<Q", 0)
    out += b"\x00" * octets_donnees
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with chemin.open("wb") as f:
        f.write(bytes(out))
    return chemin


def meta_llama_test() -> dict:
    return {
        "general.architecture": "llama",
        "general.name": "Modele Test 7B",
        "general.parameter_count": 7_000_000_000,
        "llama.block_count": 32,
        "llama.embedding_length": 4096,
        "llama.attention.head_count": 32,
        "llama.attention.head_count_kv": 8,
        "llama.attention.key_length": 128,
    }
