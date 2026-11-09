# -*- coding: utf-8 -*-
"""
eval_recherche.py : qualité de la recherche mesurée avec la vraie fonction rag.retrieve().

Pour chaque question de C qui a des documents attendus :
  - « au moins un » : un des documents attendus est dans les passages donnés au modèle
  - « tous »        : tous les documents attendus y sont
On teste plusieurs valeurs de config.MAX_PER_DOC (0 = pas de limite).
À placer dans assistant_elevage. Usage :  python eval_recherche.py
"""
import re

from openpyxl import load_workbook

import config
import rag

CLASSEUR = "Partie_C_questions_et_grille.xlsx"

ws = load_workbook(CLASSEUR, data_only=True)["Questions"]
qs = []
for r in ws.iter_rows(min_row=2, values_only=True):
    if r[0] and re.fullmatch(r"Q\d+", str(r[0])):
        att = {d.strip() for d in str(r[4] or "").split(";") if d.strip() and not d.startswith("(")}
        if att:
            qs.append((r[0], r[2], att))

print("Vaudaux plafonné à 1 passage ; autres documents : plafond testé ci-dessous")
print(f"TOP_K = {config.TOP_K} | pages exclues : {sorted(getattr(config, 'EXCLUDE_PAGES', set()))}")
print(f"{len(qs)} questions avec documents attendus\n")
# La thèse Vaudaux reste plafonnée à 1 ; on fait varier le plafond des autres documents.
config.MAX_PER_DOC_BY_ID = {"vaudaux-mali-2008": 1}
for m in (1, 2, 3, 0):
    config.MAX_PER_DOC = m
    un, tous, rat_un, rat_tous = 0, 0, [], []
    for qid, texte, att in qs:
        docs = {(p.meta.get("id") or p.meta.get("source_id") or p.meta.get("titre")) for p in rag.retrieve(texte)}
        if docs & att:
            un += 1
        else:
            rat_un.append(qid)
        if att <= docs:
            tous += 1
        else:
            rat_tous.append(qid)
    n = len(qs)
    etiquette = "autres : sans limite" if m == 0 else f"autres : max {m}"
    print(f"{etiquette:<20} au moins un : {un}/{n} ({100 * un / n:.0f} %) | tous : {tous}/{n} ({100 * tous / n:.0f} %)")
    print(f"{'':<20} sans aucun bon document : {', '.join(rat_un) or 'aucune'}")
