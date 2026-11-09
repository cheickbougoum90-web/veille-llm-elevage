"""Partie C : génère les réponses des modèles aux 30 questions, les anonymise, puis calcule les scores.

À placer dans le dossier assistant_elevage (à côté de rag.py et config.py), avec le classeur
Partie_C_questions_et_grille.xlsx.

1) Générer les réponses (Ollama lancé, chaque modèle déjà téléchargé) :
     python run_eval.py --models qwen3.5:9b gemma4:e4b [gemma4:12b]
   Les noms exacts sont ceux de `ollama list`. Même config.py (température 0,2, NUM_CTX) pour tous.
   Sorties :
     reponses_brutes.csv        tout (modèle, réponse, temps, distance, citations) : pour C seulement
     cle_correspondance.csv     question, code X/Y/Z -> modèle : à NE PAS montrer aux notateurs
     Partie_C_notation.xlsx     copie du classeur avec l'onglet « Réponses » anonymisé

2) Après notation (chaque notateur remplit l'onglet Notation de sa copie) :
     python run_eval.py --scores notation_A.xlsx notation_B.xlsx notation_C.xlsx notation_D.xlsx
   Affiche les moyennes par modèle (exactitude, prudence, clarté, total /6) et les écrit dans scores_par_modele.csv.
"""
import argparse
import csv
import random
import re
import time
from collections import defaultdict
from pathlib import Path

from openpyxl import load_workbook

CLASSEUR = "Partie_C_questions_et_grille.xlsx"
CODES = ["X", "Y", "Z", "W"]  # 4 codes au cas où il y aurait 4 modèles


def lire_questions(chemin):
    ws = load_workbook(chemin, data_only=True)["Questions"]
    qs = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        if r[0] and re.fullmatch(r"Q\d+", str(r[0])):
            qs.append({"id": r[0], "categorie": r[1], "question": r[2], "attendu": r[3]})
    return qs


def generer(modeles, classeur, seed, limite=None):
    import config
    import rag
    from rag import ask

    qs = lire_questions(classeur)
    if limite:
        qs = qs[:limite]   # test rapide : seulement les premières questions
    brut = []
    for m in modeles:
        config.OLLAMA_MODEL = m          # rag.py lit config.OLLAMA_MODEL à chaque appel
        if hasattr(rag, "OLLAMA_MODEL"):  # si rag.py a copié la valeur avec « from config import OLLAMA_MODEL »
            rag.OLLAMA_MODEL = m
        print(f"\n=== Modèle {m} (config.OLLAMA_MODEL = {config.OLLAMA_MODEL}) ===")
        for q in qs:
            t0 = time.time()
            try:
                a = ask(q["question"])
                texte, refuse = a.text, a.refused
                dist = a.best_distance
                par_seuil = bool(refuse and dist is not None and dist > config.MAX_DISTANCE)
                sources = a.sources_markdown()
                citees = " | ".join(f"S{p.n}:{p.meta.get('titre','')}" for p in a.cited)
                erreur = ""
            except Exception as e:       # Ollama arrêté, modèle absent...
                texte, refuse, dist, par_seuil, sources, citees, erreur = "", False, None, False, "", "", str(e)
            dt = time.time() - t0
            brut.append({"question_id": q["id"], "modele": m, "reponse": texte, "refus": refuse,
                         "refus_par_seuil": par_seuil, "distance": dist, "temps_s": round(dt, 1),
                         "citations": citees, "sources": sources, "erreur": erreur})
            print(f"{q['id']} {dt:5.1f}s  refus={refuse}  {texte[:60]!r}{'  ERREUR: ' + erreur if erreur else ''}")

    with open("reponses_brutes.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(brut[0].keys()))
        w.writeheader(); w.writerows(brut)

    # Contrôle : si tous les modèles ont des temps quasi identiques, le changement de modèle n'a peut-être pas fonctionné
    print("\nTemps moyen par question :")
    for m in modeles:
        t = [b["temps_s"] for b in brut if b["modele"] == m]
        print(f"  {m} : {sum(t) / len(t):.1f} s")

    # Anonymisation : un ordre aléatoire différent pour chaque question
    rng = random.Random(seed)
    par_q = defaultdict(list)
    for b in brut:
        par_q[b["question_id"]].append(b)
    cle, anonymes = [], []
    for q in qs:
        lignes = par_q[q["id"]][:]
        rng.shuffle(lignes)
        for code, b in zip(CODES, lignes):
            cle.append({"question_id": q["id"], "code": code, "modele": b["modele"]})
            anonymes.append((q["id"], q["question"], code, b["reponse"] or "(pas de réponse)", b["sources"]))
    with open("cle_correspondance.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["question_id", "code", "modele"])
        w.writeheader(); w.writerows(cle)

    wb = load_workbook(classeur)
    if "Réponses" in wb.sheetnames:
        del wb["Réponses"]
    # Les codes X/Y/Z sont mélangés question par question : une moyenne par code ne correspond à aucun modèle.
    # On retire donc l'onglet Synthèse de la copie des notateurs ; les vrais scores viennent de --scores.
    if "Synthèse" in wb.sheetnames:
        del wb["Synthèse"]
    ws = wb.create_sheet("Réponses", 1)
    ws.append(["Question", "Texte de la question", "Code", "Réponse à noter", "Sources affichées"])
    for ligne in anonymes:
        ws.append(list(ligne))
    for c, larg in zip("ABCDE", [9, 50, 7, 90, 45]):
        ws.column_dimensions[c].width = larg
    from openpyxl.styles import Alignment
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
    wb.save("Partie_C_notation.xlsx")
    print("\nFichiers écrits : reponses_brutes.csv, cle_correspondance.csv, Partie_C_notation.xlsx")
    print("Donner Partie_C_notation.xlsx aux notateurs ; garder cle_correspondance.csv pour C.")


def scores(fichiers, cle_csv="cle_correspondance.csv"):
    cle = {}
    with open(cle_csv, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            cle[(r["question_id"], r["code"])] = r["modele"]
    notes = defaultdict(lambda: [[], [], []])
    for fich in fichiers:
        ws = load_workbook(fich, data_only=True)["Notation"]
        for r in ws.iter_rows(min_row=3, values_only=True):   # la ligne 2 est l'exemple
            q, code, _, e, p, c = (list(r) + [None] * 6)[:6]
            if (q, code) not in cle or None in (e, p, c):
                continue
            for i, v in enumerate((e, p, c)):
                notes[cle[(q, code)]][i].append(float(v))
    moy = lambda l: round(sum(l) / len(l), 2) if l else None
    lignes = []
    for m, (e, p, c) in notes.items():
        lignes.append({"modele": m, "exactitude": moy(e), "prudence": moy(p), "clarte": moy(c),
                       "total_sur_6": round(sum(moy(x) for x in (e, p, c)), 2), "nb_notes": len(e)})
    lignes.sort(key=lambda d: -d["total_sur_6"])
    with open("scores_par_modele.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0].keys()))
        w.writeheader(); w.writerows(lignes)
    for l in lignes:
        print(l)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+")
    ap.add_argument("--scores", nargs="+")
    ap.add_argument("--classeur", default=CLASSEUR)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--limite", type=int, default=None, help="nombre de questions (test rapide)")
    a = ap.parse_args()
    if a.scores:
        scores(a.scores)
    elif a.models:
        generer(a.models, a.classeur, a.seed, a.limite)
    else:
        ap.print_help()
