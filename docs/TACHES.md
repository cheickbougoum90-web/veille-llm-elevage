# Tâches par rôle (2 jours de travail intensif)

Cocher les cases au fur et à mesure. Les durées sont des estimations.

## Rôle A. Déploiement et mesures (propriétaire du PC)

- [ ] Mettre à jour le pilote NVIDIA, vérifier avec `nvidia-smi` (1 h). CUDA 12.8 ou plus.
- [ ] Installer Ollama, télécharger Qwen3.5 9B et Gemma 4 E4B en Q4_K_M (1 h). Lancer les téléchargements la veille.
- [ ] Vérifier que le modèle tourne sur le GPU et non sur le processeur (30 min).
- [ ] Lancer `python scripts/benchmark_ollama.py verifier`, corriger les noms de modèles si besoin.
- [ ] Lancer `bench` pour chaque modèle, mêmes conditions (1 h 30).
- [ ] Produire le tableau final et proposer le modèle retenu (1 h, jour 2).
- [ ] Rédiger un mini guide d'installation reproductible.

Plan B si l'installation bloque : llama.cpp en version précompilée.

## Rôle B. RAG et interface

- [ ] Rassembler 5 à 10 documents vétérinaires fiables en français et remplir `data/sources.csv` (2 h).
- [ ] Nettoyer et découper les textes en passages de 300 à 500 mots (1 h).
- [ ] Créer la base vectorielle locale avec un petit modèle d'embedding sur processeur (2 h).
- [ ] Brancher la recherche au modèle : répondre à partir des extraits, citer la source, dire « je ne sais pas » si l'information manque, rappeler de consulter un vétérinaire (1 h 30).
- [ ] Construire l'interface Gradio avec bouton de lecture audio (1 h 30, avec C).
- [ ] Tester 10 questions pour vérifier les citations (1 h).

## Rôle C. Qualité et voix

- [ ] Rédiger les 30 questions dans `evaluation/questions.csv` : 10 symptômes, 8 prévention et vaccination, 6 alimentation, 6 pièges (2 h).
- [ ] Rédiger une réponse de référence courte pour chaque question, d'après les documents du RAG (1 h 30).
- [ ] Remplir la grille de notation (0 à 2 sur exactitude, prudence, clarté) dans `docs/gabarit_notation.xlsx` (30 min).
- [ ] Choisir, installer et tester un synthétiseur vocal français hors ligne, licence vérifiée (2 h).
- [ ] Organiser la notation en aveugle avec les 4 étudiants (jour 2, 1 h 30).
- [ ] Tester l'audio sur 20 phrases (1 h).

## Rôle D. Veille, légal et livrable

- [ ] Sourcing : fiches officielles des modèles, articles, dépôts GitHub. Noter chaque source dans `docs/SOURCES.md` (2 h).
- [ ] Remplir la grille de scoring avec les mesures de A et les scores de C (1 h, jour 2).
- [ ] Traiter le cadre légal et éthique : licences, RGPD, AI Act, biais, avertissement vétérinaire (1 h 30).
- [ ] Rédiger la perspective bambara (1 h).
- [ ] Rédiger le document d'une page (1 h 30), préparer la présentation orale (1 h).
- [ ] Relire l'ensemble pour la cohérence (1 h).

## Planning

| Créneau | A | B | C | D |
|---|---|---|---|---|
| Veille du jour 1 | Lancer les téléchargements | Lister les documents candidats | Commencer les questions | Lire les fiches des modèles |
| Jour 1 matin | Pilote, CUDA, Ollama, GPU | Collecte des documents | 30 questions et références | Sourcing |
| Jour 1 après-midi | Script de benchmark, mesures | Découpage, base vectorielle | Grille, test de la voix | Cadre légal, grille de scoring |
| Jour 2 matin | Mesures finales, choix du modèle | Interface, test des citations | Notation en aveugle, test audio | Notation en aveugle, résultats |
| Jour 2 après-midi | Démonstration complète | Corrections, guide d'utilisation | Synthèse des scores | Document d'une page, présentation |

Point d'équipe de 15 minutes à la fin de chaque demi-journée.
