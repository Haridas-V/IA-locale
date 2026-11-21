"""Lecture des métadonnées d'un fichier GGUF (en-tête v1 à v3, sans dépendance)."""

import struct
from pathlib import Path

MAGIE_GGUF = b"GGUF"

# Types de valeurs GGUF
T_UINT8 = 0
T_INT8 = 1
T_UINT16 = 2
T_INT16 = 3
T_UINT32 = 4
T_INT32 = 5
T_FLOAT32 = 6
T_BOOL = 7
T_STRING = 8
T_ARRAY = 9
T_UINT64 = 10
T_INT64 = 11
T_FLOAT64 = 12

TAILLE_TYPE_OCTETS = {
    T_UINT8: 1, T_INT8: 1, T_UINT16: 2, T_INT16: 2, T_UINT32: 4, T_INT32: 4,
    T_FLOAT32: 4, T_BOOL: 1, T_UINT64: 8, T_INT64: 8, T_FLOAT64: 8,
}

# Tailles des types de tenseurs GGUF (les plus courants)
TAILLE_TENSEUR = {
    0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 4, 7: 4, 8: 2, 9: 2,
    10: 2, 11: 4, 12: 4, 13: 4, 14: 1, 15: 1,
    16: 2, 17: 2, 18: 4, 19: 4, 20: 8, 21: 8, 22: 8, 23: 8, 24: 8, 25: 8,
    26: 4, 27: 4, 28: 8, 29: 8, 30: 4, 31: 4,
}


class ErreurGGUF(Exception):
    pass


class _Lecteur:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def lire(self, n: int) -> bytes:
        if self.pos + n > len(self.data):
            raise ErreurGGUF("Fin de fichier inattendue")
        morceau = self.data[self.pos:self.pos + n]
        self.pos += n
        return morceau

    def u32(self) -> int:
        return struct.unpack("<I", self.lire(4))[0]

    def i32(self) -> int:
        return struct.unpack("<i", self.lire(4))[0]

    def u64(self) -> int:
        return struct.unpack("<Q", self.lire(8))[0]

    def f32(self) -> float:
        return struct.unpack("<f", self.lire(4))[0]

    def chaine(self) -> str:
        longueur = self.u64()
        return self.lire(longueur).decode("utf-8", errors="replace")

    def valeur(self, type_valeur: int):
        if type_valeur in (T_UINT8, T_INT8, T_BOOL):
            return self.lire(1)[0]
        if type_valeur in (T_UINT16, T_INT16):
            return struct.unpack("<H" if type_valeur == T_UINT16 else "<h", self.lire(2))[0]
        if type_valeur in (T_UINT32, T_INT32):
            return struct.unpack("<I" if type_valeur == T_UINT32 else "<i", self.lire(4))[0]
        if type_valeur == T_FLOAT32:
            return self.f32()
        if type_valeur in (T_UINT64, T_INT64):
            return struct.unpack("<Q" if type_valeur == T_UINT64 else "<q", self.lire(8))[0]
        if type_valeur == T_FLOAT64:
            return struct.unpack("<d", self.lire(8))[0]
        if type_valeur == T_STRING:
            return self.chaine()
        if type_valeur == T_ARRAY:
            type_elem = self.u32()
            n = self.u64()
            return [self.valeur(type_elem) for _ in range(n)]
        raise ErreurGGUF(f"Type de valeur inconnu : {type_valeur}")


def lire_entete_gguf(chemin: Path) -> dict:
    """Retourne les métadonnées GGUF utiles + estimation des paramètres."""
    with open(chemin, "rb") as f:
        tete = f.read(8 * 1024 * 1024)
    lecteur = _Lecteur(tete)
    if lecteur.lire(4) != MAGIE_GGUF:
        raise ErreurGGUF("Ce n'est pas un fichier GGUF (magie manquante)")
    version = lecteur.u32()
    if version not in (1, 2, 3):
        raise ErreurGGUF(f"Version GGUF non supportée : {version}")
    nb_tensors = lecteur.u64() if version >= 3 else lecteur.u32()
    nb_meta = lecteur.u64() if version >= 3 else lecteur.u32()

    meta: dict = {}
    for _ in range(nb_meta):
        cle = lecteur.chaine()
        type_valeur = lecteur.u32()
        meta[cle] = lecteur.valeur(type_valeur)

    octets_tensors = 0
    for _ in range(nb_tensors):
        lecteur.chaine()  # nom du tenseur
        n_dims = lecteur.u32()
        dims = [lecteur.u64() for _ in range(n_dims)]
        type_t = lecteur.u32()
        lecteur.u64()  # offset
        taille_elem = TAILLE_TENSEUR.get(type_t, 4)
        produit = 1
        for d in dims:
            produit *= d
        octets_tensors += produit * taille_elem

    arch = meta.get("general.architecture", "")
    resultat = {
        "version": version,
        "architecture": arch,
        "nom": meta.get("general.name", ""),
        "nombre_tensors": nb_tensors,
        "octets_tensors": octets_tensors,
        "meta_brute": meta,
        "blocs": _entier(meta, f"{arch}.block_count"),
        "embedding": _entier(meta, f"{arch}.embedding_length"),
        "tetes": _entier(meta, f"{arch}.attention.head_count"),
        "tetes_kv": _entier(meta, f"{arch}.attention.head_count_kv"),
        "dimension_tete": _entier(meta, f"{arch}.attention.key_length"),
        "parametres_declares": _entier(meta, "general.parameter_count"),
    }
    return resultat


def _entier(meta: dict, cle: str):
    valeur = meta.get(cle)
    return int(valeur) if isinstance(valeur, (int, float)) else None
