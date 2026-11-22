# Dossier des modèles

Déposez ici vos modèles locaux :

- un ou plusieurs fichiers **`.gguf`** (ex. `models/mistral-7b-q4_k_m.gguf`) ;
- ou un dossier par modèle **Transformers** contenant `config.json` et les poids
  (ex. `models/mon-modele-hf/config.json`, `model.safetensors`).

L'application les détecte automatiquement dans la page **Bibliothèque** (bouton **Actualiser**).

Chaque modèle peut avoir son **profil matériel** enregistré à côté de lui
(`profil_materiel.json` dans le dossier du modèle, ou `<fichier>.profil_materiel.json` pour un GGUF),
créé depuis **Paramètres → Enregistrer comme profil du modèle**.
