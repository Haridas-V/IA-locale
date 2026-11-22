"""Moteur GGUF via llama-cpp-python (offload de couches GPU/CPU)."""

from .base import ErreurMoteur, MoteurBase, ParametresGeneration
from ..modeles import vram


class MoteurGGUF(MoteurBase):
    nom = "GGUF (llama-cpp-python)"

    def __init__(self):
        self._llm = None
        self._modele = None
        self._decision = None

    @staticmethod
    def disponible() -> tuple[bool, str]:
        try:
            import llama_cpp  # noqa: F401
            return True, "llama-cpp-python est installé."
        except ImportError:
            import sys
            return False, (
                "Le moteur GGUF (llama-cpp-python) n'est pas installé.\n"
                f"Installez-le dans le Python utilisé par l'application :\n"
                f"  {sys.executable} -m pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu   # CPU (roue précompilée)\n"
                f"  {sys.executable} -m pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu124   # GPU NVIDIA (CUDA 12.4)\n"
                f"  CMAKE_ARGS=\"-DGGML_VULKAN=ON\" {sys.executable} -m pip install llama-cpp-python --no-binary :all:   # GPU Vulkan\n"
                f"  CMAKE_ARGS=\"-DGGML_HIP=ON\" {sys.executable} -m pip install llama-cpp-python --no-binary :all:   # GPU AMD (ROCm)\n"
                "Le GPU nécessite un moteur compilé avec le backend adapté à votre carte."
            )

    def charger(self, modele, profil, contexte: int) -> None:
        ok, message = self.disponible()
        if not ok:
            raise ErreurMoteur(message)
        from llama_cpp import Llama

        decision = vram.choisir_mode(modele, profil, contexte)
        self._decision = decision
        self._llm = Llama(
            model_path=str(modele.chemin),
            n_ctx=int(contexte),
            n_threads=int(profil.threads_cpu),
            n_gpu_layers=int(decision.couches_gpu),
            verbose=False,
        )
        self._modele = modele

    def decharger(self) -> None:
        self._llm = None
        self._modele = None

    def est_charge(self) -> bool:
        return self._llm is not None

    def repondre(self, messages, params: ParametresGeneration, on_token=None) -> str:
        if self._llm is None:
            raise ErreurMoteur("Aucun modèle GGUF chargé.")
        messages_complets = [{"role": "system", "content": params.message_systeme()}] + messages
        kwargs = dict(
            messages=messages_complets,
            temperature=float(params.temperature),
            top_p=float(params.top_p),
            max_tokens=int(params.max_tokens),
        )
        if on_token is not None:
            kwargs["stream"] = True
            texte = ""
            for morceau in self._llm.create_chat_completion(**kwargs):
                delta = morceau["choices"][0]["delta"].get("content", "")
                if delta:
                    texte += delta
                    on_token(delta)
            return texte
        reponse = self._llm.create_chat_completion(**kwargs)
        return reponse["choices"][0]["message"]["content"]
