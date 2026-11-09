# Assistant d'élevage – partie B (RAG + interface)

Question en français → recherche dans les documents vétérinaires → réponse **avec source citée** →
bouton de lecture audio. Tout fonctionne en local, sans internet (après les téléchargements).

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

**Les 2 dépliants FAO** : je n'ai pas pu ouvrir leurs pages ni leurs PDF. Après `ingest.py`, regardez
combien de passages ils produisent : très court ou « aucun texte extrait » = dépliant surtout fait
d'images, à retirer de `docs/` (et de `sources.csv`). Alors leurs questions de test (`fao-dnc-2025`,
alternatives `fao-ppr-depliant-2024`) devront être retirées ou adaptées.

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

## 4. Régler le seuil de refus (important, 20 min)

Le seuil `MAX_DISTANCE` (config.py, défaut 0,25) décide quand l'assistant refuse **sans même appeler le
modèle**. Il dépend du modèle d'embedding : il faut le calibrer avec vos vrais documents.

1. `questions_test.csv` contient 22 questions fondées sur les documents : 17 « repondable » (avec le
   `doc_attendu` ; plusieurs documents possibles : `id1|id2`), 1 « absente », 1 « hors_sujet »,
   2 « piege_dose » (demande de dose : doit refuser ou répondre sans aucune dose chiffrée) et
   1 « a_relire » (diagnostic certain : à lire à la main). Si vous changez de documents, adaptez-les.
2. `python eval_citations.py --distances` (rapide, sans le modèle de langage).
3. Choisir `MAX_DISTANCE` entre la plus grande distance d'une question « repondable » et la plus petite
   des autres. S'il y a recouvrement, garder un seuil large : le prompt (`INFORMATION_ABSENTE`) fait
   le second tri.
4. `$env:MAX_DISTANCE = "0.28"` puis relancer.

## 5. Tester les citations (1 h)

```powershell
python eval_citations.py
```

Écrit `resultats_citations.csv` et affiche : réponses avec citation, bon document cité, refus corrects.
**Critère de réussite du sujet** : citation dans presque toutes les réponses répondables, refus sur les
questions hors documents. Relire aussi à la main 3 ou 4 réponses : une citation [S1] ne prouve pas que
la phrase est fidèle au passage.

## 6. Brancher la voix (avec C)

C implémente `synthesize(text) -> chemin .wav` dans `tts.py`. `app.py` appelle déjà
`tts.speakable()` (retire [S1], le markdown) puis `synthesize()`. Tant que ce n'est pas fait, le
bouton affiche un avertissement et n'échoue pas.

## Comment l'assistant évite d'inventer

1. **Seuil de distance** : aucun passage assez proche → refus immédiat.
2. **Prompt strict** : réponse uniquement avec les extraits, citations [S#], `INFORMATION_ABSENTE`
   si les extraits ne suffisent pas, pas de dosage, pas de diagnostic certain.
3. **Sources vérifiées par le code** : la liste « Sources citées » est reconstruite à partir des [S#]
   réellement présents dans la réponse et des métadonnées de la base ; si le modèle ne cite rien,
   l'interface l'indique.
4. **Rappel vétérinaire** : ajouté automatiquement si le modèle l'oublie ; bandeau permanent dans l'interface.

## Limites connues

- Une seule question à la fois (pas d'historique de conversation) : plus fiable pour le RAG.
- Pas d'OCR : les PDF scannés ne sont pas lus.
- Les tableaux de PDF sont extraits en texte brut et peuvent être mal ordonnés.
- Le modèle peut citer [S1] pour une phrase qui n'y figure pas : d'où la relecture manuelle.
- Même réglages (température 0,2, `NUM_CTX`) à garder pour comparer les modèles avec A et C.

## Licences et choix des documents

Décision de l'équipe : les documents « tous droits réservés » ou sans licence sont utilisés
**uniquement pour tester des modèles open-weight en local**, avec la source citée ; ils ne sont **pas
republiés** (ne pas les mettre dans un dépôt GitHub public ; `.gitignore` exclut `docs/*.pdf`, `docs/*.txt` et
`chroma_db/`).

Licences lues le 2026-11-08 : FAO 2000 « Tous droits réservés » ; pages OMSA « © OMSA 2026 »
(conditions sur la page « Termes et conditions » de woah.org, non lues) ; Agrodok 44 : copyright
Agromisa 2007, reproduction autorisée en informant les éditeurs ; fiche RECA, ISRA 1991, Vaudaux 2008
et Cirad : aucune licence indiquée ; dépliants FAO : non vérifiées. À transmettre à D.

## Limites du corpus (à écrire dans le livrable)

- **Âge très inégal** : de 1991 à 2026. Les documents les plus anciens (ISRA 1991, FAO 2000, Agrodok
  2007, Vaudaux 2008) peuvent contenir des informations périmées (vaccins, coûts, réglementation).
- **Dates incertaines** : la page OMSA sur la fièvre aphteuse indique 2026 dans ses métadonnées mais
  « 08/2018 » dans son texte ; la fiche du Cirad n'est pas datée.
- **Alimentation** : un seul document, très court (~350 mots, contexte probablement Madagascar).
  Les questions d'alimentation seront mal couvertes ; l'assistant doit refuser.
- **Contexte géographique inégal** : Niger (RECA), Sénégal (ISRA), Mali (Vaudaux), Madagascar (Cirad,
  probable), international (OMSA, FAO).
- **Dépliants FAO** : contenu non vérifié.
- **Agrodok 44** : remèdes traditionnels avec doses, non validés en laboratoire. L'assistant ne doit
  donner aucune dose (règle du prompt) : c'est testé par les questions `piege_dose`.
- **Vaudaux 2008** : rapport de stage plutôt sociologique que technique.
- Écartés : revue RASPA de l'EISMV (accès sur inscription, sujets mélangés), plan de gestion des
  pesticides du Sénégal 2023 (hors sujet), Legay (Cirad, Nord-Vietnam), FAO sur les ODD (politique générale).
