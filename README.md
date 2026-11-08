# Assistant d'élevage en local (travail de veille technologique)

Travail du module **Veille technologique** (ESMT, Dr Moustapha DER). Sujet : choisir un modèle open-weight, l'appliquer dans un domaine, et le déployer en local sur GPU.

## Le projet en bref

Un assistant d'aide à l'élevage (bovins et petits ruminants) qui tourne **sans internet** sur un ordinateur portable. L'utilisateur écrit sa question en français. L'assistant répond en texte et à voix haute, en français, à partir de documents vétérinaires fiables (RAG).

> **Avertissement** : cet assistant ne remplace pas un vétérinaire. Il fournit une aide d'information, pas un diagnostic.

## Chaîne de traitement

1. Question en texte français.
2. Modèle open-weight (candidat principal : Qwen3.5 9B en Q4_K_M) avec recherche dans les documents vétérinaires.
3. Réponse en texte, avec la source citée.
4. Synthèse vocale française hors ligne.

Les briques passent l'une après l'autre dans la mémoire du GPU.

## Matériel de référence

Windows 11, NVIDIA RTX 5060 (8 Go de VRAM), 32 Go de RAM, 100 Go de disque. La RTX 5060 exige un pilote NVIDIA récent et CUDA 12.8 ou plus.

## Modèles comparés

Les noms exacts sont à vérifier avec `ollama list`.

| Modèle | Rôle dans la comparaison |
|---|---|
| Qwen3.5 9B | Candidat principal |
| Gemma 4 E4B | Candidat léger |
| Gemma 4 12B | Point de comparaison, si le temps le permet |

## Structure du dépôt

```
scripts/       benchmark_ollama.py (mesures et réponses anonymisées)     Rôle A
rag/           recherche dans les documents vétérinaires                  Rôle B
app/           interface Gradio et synthèse vocale                        Rôles B et C
evaluation/    questions.csv (30 questions) et références                 Rôle C
data/          documents vétérinaires et fiche des sources                Rôle B
resultats/     mesures de performance (CSV)                               Rôle A
reponses/      réponses des modèles, anonymisées                          Rôles A et C
docs/          gabarit de notation, tâches, sources, légal, perspective   Rôle D
```

## Démarrage rapide (Windows 11)

1. Installer Python 3.10 ou plus et [Ollama pour Windows](https://ollama.com/download).
2. Cloner le dépôt et installer les dépendances :

```
git clone <adresse du dépôt>
cd veille-llm-elevage
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

3. Télécharger les modèles, puis vérifier :

```
ollama pull <nom du modèle>
python scripts/benchmark_ollama.py verifier
```

4. Mesurer la performance :

```
python scripts/benchmark_ollama.py bench
```

5. Faire répondre les modèles aux questions, en vue de la notation en aveugle :

```
python scripts/benchmark_ollama.py repondre --questions evaluation/questions.csv
```

Les résultats arrivent dans `resultats/` et `reponses/`. Le classeur `docs/gabarit_notation.xlsx` sert à noter, comparer et décider.

## Notation en aveugle

Le script mélange les réponses des modèles et leur donne un code (R001, R002, ...). Les évaluateurs notent sans savoir quel modèle a répondu. La clé `reponses/cle_modeles.csv` et les réponses brutes sont **exclues de Git** (voir `.gitignore`) pour ne pas casser l'anonymat. Le rôle A les transmet à l'équipe seulement après la fin de la notation.

## Travail en équipe

| Rôle | Mission | Branche |
|---|---|---|
| A. Déploiement et mesures | Installer, mesurer, choisir le modèle | `role-a-deploiement` |
| B. RAG et interface | Documents fiables, recherche, interface | `role-b-rag` |
| C. Qualité et voix | 30 questions, notation, synthèse vocale | `role-c-qualite` |
| D. Veille, légal et livrable | Sourcing, licences, document d'une page | `role-d-veille` |

Règles simples :
- Chacun travaille sur sa branche, puis ouvre une *pull request* vers `main`.
- Un autre membre relit avant de fusionner.
- Messages de commit courts, au présent : « Ajoute le script de benchmark ».
- Ne jamais committer de modèle, de base vectorielle, ni de document dont la licence interdit la diffusion.

Le détail des tâches et du planning est dans `docs/TACHES.md`.

## Licence

Le code est publié sous licence MIT (fichier `LICENSE`). Chaque modèle et chaque document garde sa propre licence : voir `docs/SOURCES.md`.

## Perspective

Le bambara (reconnaissance vocale, synthèse, traduction) est gardé en perspective, hors du périmètre noté : voir `docs/perspective_bambara.md`.
