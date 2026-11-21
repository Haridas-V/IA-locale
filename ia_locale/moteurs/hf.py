"""Moteur Transformers via Hugging Face (carte des appareils automatique)."""

from .base import ErreurMoteur, MoteurBase, ParametresGeneration
from ..modeles import vram


class MoteurTransformers(MoteurBase):
    nom = "Transformers (Hugging Face)"

    def __init__(self):
        self._modele = None
        self._tokeniseur = None
        self._pipe = None

    @staticmethod
    def disponible() -> tuple[bool, str]:
        try:
            import torch  # noqa: F401
            import transformers  # noqa: F401
            import accelerate  # noqa: F401
            return True, "transformers + torch sont installés."
        except ImportError:
            return False, (
                "Le moteur Transformers n'est pas installé.\n"
                "  - CPU : pip install transformers accelerate torch\n"
                "  - GPU NVIDIA : pip install torch --index-url https://download.pytorch.org/whl/cu124\n"
                "    puis : pip install transformers accelerate\n"
                "Le GPU nécessite torch compilé avec le backend adapté (CUDA, ROCm, etc.)."
            )

    def charger(self, modele, profil, contexte: int) -> None:
        ok, message = self.disponible()
        if not ok:
            raise ErreurMoteur(message)
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        torch.set_num_threads(int(profil.threads_cpu))
        carte = vram.carte_appareils_transformers(profil)
        self._tokeniseur = AutoTokenizer.from_pretrained(str(modele.chemin))
        self._modele = AutoModelForCausalLM.from_pretrained(
            str(modele.chemin),
            device_map=carte["device_map"],
            max_memory=carte["max_memory"],
        )
        self._contexte = int(contexte)

    def decharger(self) -> None:
        self._modele = None
        self._tokeniseur = None

    def est_charge(self) -> bool:
        return self._modele is not None

    def repondre(self, messages, params: ParametresGeneration, on_token=None) -> str:
        if self._modele is None:
            raise ErreurMoteur("Aucun modèle Transformers chargé.")
        messages_complets = [{"role": "system", "content": params.message_systeme()}] + messages
        try:
            invite = self._tokeniseur.apply_chat_template(
                messages_complets, tokenize=False, add_generation_prompt=True
            )
        except Exception:
            invite = "\n".join(f"{m['role']} : {m['content']}" for m in messages_complets) + "\nassistant : "
        entrees = self._tokeniseur(invite, return_tensors="pt").to(self._modele.device)
        import torch
        with torch.no_grad():
            sortie = self._modele.generate(
                **entrees,
                max_new_tokens=int(params.max_tokens),
                do_sample=float(params.temperature) > 0,
                temperature=max(1e-5, float(params.temperature)),
                top_p=float(params.top_p),
                pad_token_id=self._tokeniseur.eos_token_id,
            )
        nouveaux = sortie[0][entrees["input_ids"].shape[1]:]
        texte = self._tokeniseur.decode(nouveaux, skip_special_tokens=True)
        if on_token is not None and texte:
            on_token(texte)
        return texte
