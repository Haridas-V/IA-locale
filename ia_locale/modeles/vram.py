"""Estimation de la VRAM et répartition GPU/CPU pour les modèles locaux."""

from dataclasses import dataclass

OCTETS_FP16 = 2
MARGE_PROPORTIONNELLE = 0.12
MARGE_FIXE_MO = 256.0


@dataclass
class DecisionMaterielle:
    mode: str  # "cpu", "gpu" ou "hybride"
    couches_gpu: int
    couches_totales: int
    vram_estimee_go: float
    budget_go: float
    avertissement: str | None = None


def _meta_gguf(modele) -> dict:
    return modele.meta or {}


def couches_totales(modele) -> int:
    if modele.format == "gguf":
        return int(_meta_gguf(modele).get("blocs") or 0)
    return 0


def kv_par_couche_go(n_ctx: int, tetes_kv: int, dimension_tete: int, octets: int = OCTETS_FP16) -> float:
    """Cache KV par couche en Gio (2 tenseurs K et V, précision 16 bits)."""
    octets_couche = 2 * n_ctx * tetes_kv * dimension_tete * octets
    return octets_couche / (1024 ** 3)


def estimer_vram_go(modele, n_ctx: int, couches_gpu: int | None = None) -> dict:
    """Estime la VRAM nécessaire, avec une marge pour le contexte.

    Retourne un dict avec le détail : poids, cache KV, marge, total (en Gio).
    """
    if modele.format != "gguf":
        return {"poids_go": 0.0, "kv_go": 0.0, "marge_go": 0.0, "total_go": 0.0, "couches": 0}
    meta = _meta_gguf(modele)
    n_couches = int(meta.get("blocs") or 0)
    if couches_gpu is None:
        couches_gpu = n_couches
    couches_gpu = max(0, min(couches_gpu, n_couches))
    poids_total_go = (modele.taille_octets or meta.get("octets_tensors") or 0) / (1024 ** 3)
    tetes_kv = int(meta.get("tetes_kv") or meta.get("tetes") or 1)
    dim_tete = int(meta.get("dimension_tete") or 0)
    if not dim_tete and meta.get("embedding") and meta.get("tetes"):
        dim_tete = meta["embedding"] // meta["tetes"]
    kv_go = kv_par_couche_go(n_ctx, tetes_kv, dim_tete)
    fraction = (couches_gpu / n_couches) if n_couches else 0.0
    poids_go = poids_total_go * fraction
    kv_total_go = kv_go * couches_gpu
    marge_go = (poids_go + kv_total_go) * MARGE_PROPORTIONNELLE + MARGE_FIXE_MO / 1024
    return {
        "poids_go": poids_go,
        "kv_go": kv_total_go,
        "marge_go": marge_go,
        "total_go": poids_go + kv_total_go + marge_go,
        "couches": couches_gpu,
        "couches_totales": n_couches,
        "kv_par_couche_go": kv_go,
    }


def couches_dans_budget(modele, n_ctx: int, budget_go: float) -> int:
    """Nombre maximal de couches GGUF déchargeables sur le GPU dans le budget."""
    n_couches = couches_totales(modele)
    if n_couches <= 0 or budget_go <= 0:
        return 0
    for k in range(n_couches, 0, -1):
        if estimer_vram_go(modele, n_ctx, k)["total_go"] <= budget_go:
            return k
    return 0


def choisir_mode(modele, profil, n_ctx: int) -> DecisionMaterielle:
    """Applique le mode de calcul demandé (auto/cpu/gpu/hybride) au profil."""
    budget = float(profil.budget_vram_go)
    n_couches = couches_totales(modele)
    demande = (profil.mode_calcul or "auto").lower()

    if modele.format != "gguf":
        return DecisionMaterielle(
            mode=demande if demande != "auto" else "auto",
            couches_gpu=n_couches,
            couches_totales=n_couches,
            vram_estimee_go=0.0,
            budget_go=budget,
            avertissement="Format Transformers : carte des appareils « auto » avec limites mémoire GPU/CPU.",
        )

    if demande == "cpu":
        return DecisionMaterielle("cpu", 0, n_couches, 0.0, budget)

    tout = estimer_vram_go(modele, n_ctx, n_couches)["total_go"]
    if demande == "gpu":
        if tout <= budget:
            return DecisionMaterielle("gpu", n_couches, n_couches, tout, budget)
        possibles = couches_dans_budget(modele, n_ctx, budget)
        if possibles <= 0:
            return DecisionMaterielle(
                "cpu", 0, n_couches, 0.0, budget,
                avertissement=f"Le modèle complet (~{tout:.1f} Gio) dépasse le budget GPU ({budget:.1f} Gio) : calcul CPU.",
            )
        return DecisionMaterielle(
            "hybride", possibles, n_couches,
            estimer_vram_go(modele, n_ctx, possibles)["total_go"], budget,
            avertissement=f"Le modèle complet (~{tout:.1f} Gio) dépasse le budget GPU ({budget:.1f} Gio) : {possibles}/{n_couches} couches sur GPU.",
        )

    if demande == "hybride":
        demandees = profil.offload_couches
        if demandees is None or demandees < 0:
            demandees = n_couches
        demandees = max(0, min(demandees, n_couches))
        possibles = couches_dans_budget(modele, n_ctx, budget)
        couches = min(demandees, possibles)
        if couches <= 0:
            return DecisionMaterielle("cpu", 0, n_couches, 0.0, budget,
                                      avertissement="Aucune couche ne tient dans le budget GPU : calcul CPU.")
        return DecisionMaterielle("hybride", couches, n_couches,
                                  estimer_vram_go(modele, n_ctx, couches)["total_go"], budget)

    # auto
    if tout <= budget:
        return DecisionMaterielle("gpu", n_couches, n_couches, tout, budget)
    possibles = couches_dans_budget(modele, n_ctx, budget)
    if possibles > 0:
        return DecisionMaterielle("hybride", possibles, n_couches,
                                  estimer_vram_go(modele, n_ctx, possibles)["total_go"], budget)
    return DecisionMaterielle("cpu", 0, n_couches, 0.0, budget,
                              avertissement=f"VRAM estimée ~{tout:.1f} Gio > budget {budget:.1f} Gio : calcul CPU.")


def carte_appareils_transformers(profil) -> dict:
    """Carte automatique des appareils et limites mémoire pour Transformers."""
    return {
        "device_map": "auto",
        "max_memory": {
            0: f"{float(profil.budget_vram_go):.1f}GiB",
            "cpu": f"{float(profil.budget_ram_go):.1f}GiB",
        },
    }
