# -*- coding: utf-8 -*-
"""
hubs.py : repère les passages « aimants », ceux qui reviennent dans les résultats de presque toutes
les questions sans avoir de contenu utile (remerciements, sommaire, bibliographie...).

Lance la recherche (sans Ollama) sur les 30 questions de C et compte les apparitions de chaque passage.
À placer dans assistant_elevage. Usage :  python hubs.py
"""
import collections
import re

from openpyxl import load_workbook

import rag

CLASSEUR = "Partie_C_questions_et_grille.xlsx"

ws = load_workbook(CLASSEUR, data_only=True)["Questions"]
qs = [(r[0], r[2]) for r in ws.iter_rows(min_row=2, values_only=True) if r[0] and re.fullmatch(r"Q\d+", str(r[0]))]

compte, extrait, quand = collections.Counter(), {}, collections.defaultdict(list)
for qid, texte in qs:
    for p in rag.retrieve(texte):
        doc = p.meta.get("id") or p.meta.get("source_id") or p.meta.get("titre") or "?"
        cle = (doc, p.meta.get("page", "?"))
        compte[cle] += 1
        extrait.setdefault(cle, p.text[:110].replace("\n", " "))
        quand[cle].append(qid)

print(f"{len(qs)} questions, {len(compte)} passages différents retrouvés (4 par question)\n")
print("Passages les plus fréquents (>= 3 apparitions) :")
for (doc, page), n in compte.most_common():
    if n < 3:
        break
    print(f"\n{n:2d} fois | {doc} p.{page} | {extrait[(doc, page)]!r}")
    print(f"        questions : {', '.join(quand[(doc, page)])}")
