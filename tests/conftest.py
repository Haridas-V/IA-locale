import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.util_gguf import ecrire_gguf, meta_llama_test  # noqa: E402


@pytest.fixture
def env_tmp(tmp_path, monkeypatch):
    """Isole config et données dans un dossier temporaire."""
    config = tmp_path / "config"
    donnees = tmp_path / "donnees"
    monkeypatch.setenv("IA_LOCALE_CONFIG", str(config))
    monkeypatch.setenv("IA_LOCALE_DATA", str(donnees))
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.delenv("APPIMAGE", raising=False)
    return tmp_path


@pytest.fixture
def dossier_modeles_faux(env_tmp):
    """Crée un dossier models/ avec un faux GGUF et un faux modèle Transformers."""
    models = env_tmp / "models"
    models.mkdir(parents=True, exist_ok=True)
    tensors = [("tok_embeddings.weight", [32000, 4096], 6)]  # 32000*4096*4 o = 512 Mio
    ecrire_gguf(models / "mon-modele-7b-q4_k_m.gguf", meta_llama_test(), tensors, octets_donnees=64)
    hf = models / "petit-transformers"
    hf.mkdir(parents=True, exist_ok=True)
    (hf / "config.json").write_text(json.dumps({
        "model_type": "llama",
        "architectures": ["LlamaForCausalLM"],
    }), encoding="utf-8")
    (hf / "model.safetensors").write_bytes(b"\x00" * (2 * 1024 * 1024))
    return models


@pytest.fixture
def etat_tmp(env_tmp, dossier_modeles_faux):
    from ia_locale.etat import EtatApplication
    from ia_locale import config as cfg_module
    config = cfg_module.charger_config()
    config["dossier_modeles"] = str(dossier_modeles_faux)
    cfg_module.sauvegarder_config(config)
    return EtatApplication()
