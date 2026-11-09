# -*- coding: utf-8 -*-
"""
voir_passages.py : pour une question, montre TOUS les passages des documents attendus par C,
avec leur rang de similarité sur l'ensemble de la base et un marqueur « REÇU » si le modèle l'a eu.

Permet de voir si un passage utile existe dans le bon document mais a été écarté (limite par document).
À placer dans assistant_elevage. Usage :  python voir_passages.py Q15 Q18
"""
import re
import sys

from openpyxl import load_workbook

import config
import rag
from embeddings import embed_query

CLASSEUR = "Partie_C_questions_et_grille.xlsx"

ws = load_workbook(CLASSEUR, data_only=True)["Questions"]
questions = {}
for r in ws.iter_rows(min_row=2, values_only=True):
    if r[0] and re.fullmatch(r"Q\d+", str(r[0])):
        att = {d.strip() for d in str(r[4] or "").split(";") if d.strip() and not d.startswith("(")}
        questions[r[0]] = (r[2], r[3], att)

col = rag._collection()
tout = col.get(include=["documents", "metadatas"])
n_total = len(tout["documents"])


def doc_id(m):
    return m.get("id") or m.get("source_id") or m.get("titre") or "?"


for qid in sys.argv[1:]:
    if qid not in questions:
        print(f"{qid} : introuvable")
        continue
    texte, attendu, att = questions[qid]
    recus = {p.text for p in rag.retrieve(texte)}
    res = col.query(query_embeddings=[embed_query(texte)], n_results=n_total,
                    include=["documents", "metadatas", "distances"])
    print("=" * 78)
    print(f"{qid} : {texte}\nAttendu : {attendu} | documents : {', '.join(sorted(att)) or '(aucun)'}")
    print(f"(MAX_PER_DOC = {getattr(config, 'MAX_PER_DOC', 0)})\n")
    for rang, (d, m, dist) in enumerate(zip(res["documents"][0], res["metadatas"][0], res["distances"][0]), 1):
        if doc_id(m) in att:
            marque = "REÇU " if d in recus else "écarté"
            print(f"  rang {rang:3d} | {marque} | {doc_id(m)} p.{m.get('page', '?')} | dist {dist:.3f}")
            print(f"           {d[:420].replace(chr(10), ' ')!r}\n")
