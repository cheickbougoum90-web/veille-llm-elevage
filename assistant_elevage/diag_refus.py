# -*- coding: utf-8 -*-
"""
diag_refus.py : montre les passages retrouvés par le RAG pour des questions données,
et indique si le document attendu par C figure parmi eux.

À placer à côté de rag.py. Usage :
  python diag_refus.py Q03 Q14 Q21
  python diag_refus.py Q03 --k 8
"""
import argparse
import re
import sys

from openpyxl import load_workbook

import rag

CLASSEUR = "Partie_C_questions_et_grille.xlsx"

# Correspondance entre les noms de documents du classeur de C et les id de sources.csv
ALIAS = {"agrodok-44": "agrodok-44", "cirad-rationnement-vl": "cirad-rationnement-vl"}


def lire(chemin):
    ws = load_workbook(chemin, data_only=True)["Questions"]
    out = {}
    for r in ws.iter_rows(min_row=2, values_only=True):
        if r[0] and re.fullmatch(r"Q\d+", str(r[0])):
            out[r[0]] = {"question": r[2], "attendu": r[3], "docs": r[4]}
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("ids", nargs="+")
    p.add_argument("--k", type=int, default=None)
    p.add_argument("--classeur", default=CLASSEUR)
    a = p.parse_args()

    qs = lire(a.classeur)
    for qid in a.ids:
        q = qs.get(qid)
        if not q:
            print(f"{qid} : introuvable dans le classeur")
            continue
        attendus = [d.strip() for d in str(q["docs"] or "").split(";") if d.strip() and not d.startswith("(")]
        print("=" * 78)
        print(f"{qid} : {q['question']}")
        print(f"Comportement attendu : {q['attendu']}")
        print(f"Documents attendus   : {', '.join(attendus) or '(aucun)'}")
        passages = rag.retrieve(q["question"], a.k)
        trouves = set()
        for i, ps in enumerate(passages, 1):
            meta = getattr(ps, "meta", {}) or {}
            vals = {str(v) for v in meta.values()}
            trouves |= vals
            txt = next((getattr(ps, k) for k in ("text", "texte", "content", "page_content") if hasattr(ps, k)), "")
            doc = next((meta[k] for k in ("id", "source_id", "doc_id", "source", "titre") if k in meta), "?")
            print(f"  [S{getattr(ps, 'n', i)}] dist {ps.distance:.3f} | {doc} p.{meta.get('page', '')} | {str(txt)[:160]!r}")
        if attendus:
            manquants = [d for d in attendus if d not in trouves]
            if len(manquants) == len(attendus):
                print("  => AUCUN document attendu dans les passages : problème de RECHERCHE.")
            elif manquants:
                print(f"  => Documents attendus absents : {', '.join(manquants)}")
            else:
                print("  => Tous les documents attendus sont présents : le refus vient du PROMPT ou du modèle.")
        print()


if __name__ == "__main__":
    main()
