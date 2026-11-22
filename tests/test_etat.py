def test_etat_detecte_modeles(etat_tmp):
    assert len(etat_tmp.modeles) == 2
    assert str(etat_tmp.dossier_modeles).endswith("models")


def test_chargement_mock_et_reponse(etat_tmp, monkeypatch):
    monkeypatch.setenv("IA_LOCALE_MOCK", "1")
    id_gguf = next(m.id for m in etat_tmp.modeles if m.format == "gguf")
    ok, message = etat_tmp.selectionner_modele(id_gguf, charger=True)
    assert ok, message
    assert etat_tmp.modele_est_charge()
    params = etat_tmp.parametres_generation()
    params.connaissances = "Connaissance test"
    assert "Connaissance test" in params.message_systeme()
    reponse = etat_tmp.moteur.repondre([{"role": "user", "content": "bonjour"}], params)
    assert "bonjour" in reponse
    etat_tmp.decharger_modele()
    assert not etat_tmp.modele_est_charge()


def test_profil_enregistre_par_etat(etat_tmp):
    id_hf = next(m.id for m in etat_tmp.modeles if m.format == "transformers")
    etat_tmp.selectionner_modele(id_hf)
    etat_tmp.profil_courant.mode_calcul = "gpu"
    etat_tmp.profil_courant.budget_vram_go = 10.0
    fichier = etat_tmp.enregistrer_profil_courant()
    assert fichier.is_file()
    assert etat_tmp.profil_existe()
