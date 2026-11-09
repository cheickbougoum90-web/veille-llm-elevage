# Assistant d'élevage – partie B (RAG + interface)

Question en français → recherche dans les documents vétérinaires → réponse **avec source citée** →
bouton de lecture audio. Les questions et les documents restent sur le PC. Après le premier téléchargement
des modèles, l'ensemble doit pouvoir tourner hors ligne (voir section « Hors ligne », pas encore testé sans connexion).

```
docs/*.pdf|txt  --ingest.py-->  chroma_db/  --rag.py-->  Ollama (Qwen3.5 9B)  --app.py-->  Gradio
sources.csv (source, date, licence)                                              tts.py (voix, étudiant C)
```

| Fichier | Rôle |
|---|---|
| `config.py` | tous les réglages (modèle, seuil de refus, taille des passages) |
| `ingest.py` | nettoie, découpe (300-500 mots), crée la base vectorielle |
| `rag.py` | recherche + prompt + appel d'Ollama + citations + refus |
| `app.py` | interface Gradio |
| `tts.py` | **point d'accroche pour la voix** : C remplit `synthesize()` |
| `eval_citations.py` + `questions_test.csv` | test des citations et des refus |
| `sources.csv` | fiche des sources : une ligne par document |

## 1. Installation (Windows 11)

Utiliser **Python 3.11 ou 3.12** (le plus sûr avec chromadb / sentence-transformers).

```powershell
cd assistant_elevage
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Ollama doit tourner (A s'en charge) avec le modèle téléchargé. Vérifier le **nom exact** du tag :

```powershell
ollama list
$env:OLLAMA_MODEL = "qwen3.5:9b"     # remplacer par le nom affiché par ollama list
```

Le petit modèle d'embedding (`intfloat/multilingual-e5-small`, ~120 M de paramètres) se télécharge
au premier lancement de `ingest.py` et tourne **sur le processeur** : il ne prend pas de VRAM.

## 2. Les documents (choisis avec l'équipe)

`docs/` est **vide** : il faut récupérer les 11 documents et les enregistrer **avec exactement ces noms**
(colonne `fichier` de `sources.csv`). Les liens sont dans la colonne `url`.

| Nom de fichier | Document | Date | Contenu lu par nous |
|---|---|---|---|
| `reca_ppcb_fiche_technique_2025.pdf` | RECA Niger, fiche technique PPCB | juil. 2025 | oui |
| `woah_fievre_aphteuse.txt` | OMSA, page Fièvre aphteuse | 2026 (date incohérente) | oui |
| `woah_ppcb.txt` | OMSA, page PPCB | juil. 2026 | oui |
| `woah_brucellose.txt` | OMSA, page Brucellose (remplace l'ancienne fiche PDF) | août 2024 | oui |
| `fao_reconnaitre_ppr.pdf` | FAO, Reconnaître la PPR | 2000 | oui |
| `fao_depliant_ppr_2024.pdf` | FAO, dépliant PPR | 2024 | **non** |
| `fao_depliant_dnc_2025.pdf` | FAO, dépliant Dermatose nodulaire contagieuse | 2025 | **non** |
| `agrodok44_ethnomedecine_veterinaire.pdf` | Agrodok 44, Ethnomédecine vétérinaire | 2007 | oui |
| `isra_prophylaxies_petits_ruminants_1991.pdf` | ISRA, Prophylaxies petits ruminants Sénégal | 1991 | oui |
| `vaudaux_vaccination_mali_2008.pdf` | Vaudaux, Vaccination du bétail au Mali | 2008 | oui |
| `cirad_rationnement_vaches_laitieres.pdf` | CIRAD, Rationnement des vaches laitières | non datée | oui |

**Pages web OMSA (3 fichiers `.txt`)** : ouvrir la page, copier **uniquement le texte de l'article**
(sans menus ni pied de page) dans un fichier texte UTF-8 du nom indiqué. C'est plus propre qu'une
impression en PDF, qui embarque la navigation du site.

**Les 2 dépliants FAO** : leur texte est bien extrait par `ingest.py` (2 et 3 passages). Le dépliant PPR est
bilingue (p. 1 anglais, p. 2 français) et sa traduction contient une erreur (« Bouche not couch »).

Un fichier de `docs/` absent de `sources.csv` est ignoré (source, date et licence obligatoires).
Pour ajouter un document : copier le fichier dans `docs/` et ajouter une ligne à `sources.csv`.
PDF scannés (images) : `ingest.py` le signale ; il faudrait un OCR.

```powershell
python ingest.py
```

Certains documents sont courts (Cirad ~350 mots, ISRA ~7 pages, dépliants) et ne donneront que
quelques passages.

## 3. Lancer l'interface

```powershell
python app.py        # puis ouvrir http://127.0.0.1:7860
```

## 4. Recherche : seuil, pages exclues, plafond par document

**Seuil de distance `MAX_DISTANCE` = 0,17 : INACTIF.** Sur les 30 questions de C il ne s'est déclenché
**jamais** (0 sur 30) : les distances de `multilingual-e5-small` sont très serrées (0,08 à 0,20), donc même les
questions hors sujet passent. Il ne faut pas le présenter comme un garde-fou. Le tri des questions sans
réponse se fait par la **consigne au modèle** (`INFORMATION_ABSENTE`). Le seuil reste dans le code, au cas où un
embedding plus discriminant (`bge-m3`, `e5-base`) serait testé : il faudrait alors le recalibrer
(`python eval_citations.py --distances`).

**Corrections de la recherche** (mesurées avec `eval_recherche.py`, vraie fonction `rag.retrieve()`) :

| Réglage (`config.py`) | Effet |
|---|---|
| `EXCLUDE_PAGES` : Vaudaux p. 7 (remerciements) et p. 115 (guide d'enquête) | ces deux pages revenaient pour presque toutes les questions |
| `MAX_PER_DOC_BY_ID = {"vaudaux-mali-2008": 1}` | un seul passage de la thèse Vaudaux (90 passages sur 188) par réponse |
| `MAX_PER_DOC = 3` | au plus 3 passages du même document ; un plafond de 1 pour tous écartait un passage utile (Q15, brucellose) |

Résultat : au moins un bon document trouvé pour **21 questions sur 24** (17 au départ) ; tous les documents
attendus présents pour 18 sur 24. **Chiffre optimiste** : les réglages ont été choisis sur les mêmes 24 questions
que l'évaluation, et la mesure se fait par document, pas par passage.

Échecs connus : Q03 (« ampoules » dans la question, « lésions » dans le document) ; Q18 (le passage utile sur la
PPR arrive vers le rang 98).

## 5. Tester les citations (1 h)

```powershell
python eval_citations.py
```

Écrit `resultats_citations.csv` (à lancer avec le modèle retenu par A) et affiche : réponses avec citation, bon document cité, refus corrects.
**Critère de réussite du sujet** : citation dans presque toutes les réponses répondables, refus sur les
questions hors documents. Relire aussi à la main 3 ou 4 réponses : une citation [S1] ne prouve pas que
la phrase est fidèle au passage.

## 6. Brancher la voix (avec C)

C implémente `synthesize(text) -> chemin .wav` dans `tts.py`. `app.py` appelle déjà
`tts.speakable()` (retire [S1], le markdown) puis `synthesize()`. Tant que ce n'est pas fait, le
bouton affiche un avertissement et n'échoue pas.

## Comment l'assistant évite d'inventer

1. **Recherche contrôlée** : 4 passages au plus, plafond par document, pages sans contenu vétérinaire exclues.
   (Le seuil de distance existe mais est inactif, voir section 4.)
2. **Consigne au modèle, version 2** (`rag.py`) : réponse uniquement avec les extraits, citations [S#].
   **Une réponse partielle est permise** : le modèle donne ce que les extraits contiennent, puis dit ce qui
   manque (« Les extraits ne précisent pas... »). `INFORMATION_ABSENTE` (donc le refus) seulement si les
   extraits ne contiennent rien d'utile. Pas de dosage, pas de diagnostic certain, rappel vétérinaire.
3. **Sources vérifiées par le code** : la liste « Sources citées » est reconstruite à partir des [S#]
   réellement présents dans la réponse et des métadonnées de la base ; si le modèle ne cite rien,
   l'interface l'indique.
4. **Rappel vétérinaire** : ajouté automatiquement si le modèle l'oublie ; bandeau permanent « intelligence
   artificielle, pas un vétérinaire » dans l'interface.

Ces règles dépendent du modèle : un modèle peut les suivre moins bien (voir la notation en aveugle).

## Hors ligne et confidentialité

- **`HF_HUB_OFFLINE=1`** : le modèle d'embeddings se télécharge une fois depuis Hugging Face. Ensuite, pour que
  `ingest.py` et `app.py` ne contactent plus le site, lancer dans le terminal :
  ```powershell
  $env:HF_HUB_OFFLINE = "1"
  ```
  (à retirer pour re-télécharger un modèle : `Remove-Item Env:HF_HUB_OFFLINE`). Le fonctionnement sans connexion
  **n'a pas été testé de bout en bout**.
- `app.py` désactive les statistiques de Gradio (`GRADIO_ANALYTICS_ENABLED=False`) et n'enregistre pas les
  questions ; chaque question est traitée seule.
- Ollama écoute uniquement sur `127.0.0.1:11434` (vérifié avec `netstat` par A) : l'API n'est pas accessible
  depuis le réseau.

## Limites connues

- Une seule question à la fois (pas d'historique de conversation) : plus fiable pour le RAG.
- Pas d'OCR : les PDF scannés ne sont pas lus.
- Les tableaux de PDF sont extraits en texte brut et peuvent être mal ordonnés.
- Le modèle peut citer [S1] pour une phrase qui n'y figure pas : d'où la relecture manuelle.
- Même réglages (température 0,2, `NUM_CTX` = 4096) à garder pour comparer les modèles avec A et C.
- Marge de contexte faible : environ 177 tokens libres sur 4096 avec 4 passages.
- Démarrage à froid : environ 22 s pour la première réponse, moins de 4 s ensuite ; Ollama décharge le modèle après
  5 minutes (`setx OLLAMA_KEEP_ALIVE 30m` pour la démonstration).
- Français uniquement : le bambara reste une perspective.

## Licences et choix des documents

Décision de l'équipe : les documents « tous droits réservés » ou sans licence sont utilisés
**uniquement pour tester des modèles open-weight en local**, avec la source citée ; ils ne sont **pas
republiés** (ne pas les mettre dans un dépôt GitHub public ; `.gitignore` exclut `docs/*.pdf`, `docs/*.txt` et
`chroma_db/`).

Conditions lues le 09/11/2026 (détail dans `sources.csv`, affichées dans l'interface) :
- **OMSA (WOAH)** : réutilisation **sans modification**, avec mention de la source, pour l'information et la
  sensibilisation ; tout autre usage, dont commercial, demande un accord écrit. Risque : reformuler un texte de
  l'OMSA peut contredire « sans modification ».
- **FAO (dermatose nodulaire)** : copie autorisée pour l'étude, la recherche, l'enseignement et les produits non
  commerciaux, avec mention de la FAO. FAO 2000 : « Tous droits réservés ». Dépliant PPR 2024 : CC BY-NC-SA 3.0 IGO
  (mention lue dans le PDF).
- Agrodok 44 : copyright Agromisa 2007, reproduction autorisée en informant les éditeurs.
- Fiche RECA, ISRA 1991, Vaudaux 2008, Cirad : aucune licence indiquée.

Vérifié en ligne le 09/11/2026 (par recherche web ; les pages officielles de woah.org et fao.org n'ont pas toutes pu être rouvertes) :
- **`intfloat/multilingual-e5-small`** : licence **MIT** (champ `license: mit` de la fiche Hugging Face). Confirmé.
- **Piper (le programme)** : le dépôt actuel `OHF-Voice/piper1-gpl` est sous **GPL-3.0 ou ultérieure** ; l'ancien
  `rhasspy/piper` (MIT) a été archivé en octobre 2025. Source : un article de test, pas le fichier LICENSE du
  dépôt (à relire). Pour un usage local de démonstration, aucun problème ; en cas de redistribution de
  l'application avec Piper, la GPL s'applique.
- **Voix `fr_FR-siwis-medium`** : entraînée sur la base SIWIS (Édimbourg / Idiap). Une copie publiée sur Hugging Face
  (`Trelis/piper-fr-fr-siwis-medium`) indique **CC BY 4.0**, donc citer la source ; le dépôt officiel
  `rhasspy/piper-voices` affiche `license: mit` pour tout le dépôt, ce qui n'est pas la licence de cette voix.
  **Non confirmé à la source** : C doit lire le fichier `MODEL_CARD` de la voix et la page de la base SIWIS
  (datashare.is.ed.ac.uk, non accessible ici).
- **Dépliant FAO PPR 2024** : la mention **CC BY-NC-SA 3.0 IGO** a été lue dans le PDF lui-même (par B). Je n'ai pas
  retrouvé la page FAO du dépliant pour la recouper.

## Limites du corpus (à écrire dans le livrable)

- **Âge très inégal** : de 1991 à 2026. Les documents les plus anciens (ISRA 1991, FAO 2000, Agrodok
  2007, Vaudaux 2008) peuvent contenir des informations périmées (vaccins, coûts, réglementation).
- **Dates incertaines** : la page OMSA sur la fièvre aphteuse indique 2026 dans ses métadonnées mais
  « 08/2018 » dans son texte ; la fiche du Cirad n'est pas datée.
- **Alimentation** : un seul document, très court (~350 mots, 2 passages, contexte probablement Madagascar).
  Les questions d'alimentation sont mal couvertes ; l'assistant doit dire ce qui manque.
- **Corpus déséquilibré** : Vaudaux et Agrodok font 74 % des 188 passages.
- **Contexte géographique inégal** : Niger (RECA), Sénégal (ISRA), Mali (Vaudaux), Madagascar (Cirad,
  probable), international (OMSA, FAO).
- **Dépliants FAO** : lus après coup ; le dépliant PPR est bilingue (voir section 2).
- **Agrodok 44** : remèdes traditionnels avec doses, non validés en laboratoire. L'assistant ne doit
  donner aucune dose (règle du prompt) : c'est testé par les questions `piege_dose`.
- **Vaudaux 2008** : rapport de stage plutôt sociologique que technique.
- Écartés : revue RASPA de l'EISMV (accès sur inscription, sujets mélangés), plan de gestion des
  pesticides du Sénégal 2023 (hors sujet), Legay (Cirad, Nord-Vietnam), FAO sur les ODD (politique générale).
