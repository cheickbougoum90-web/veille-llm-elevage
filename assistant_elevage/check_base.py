# -*- coding: utf-8 -*-
"""
check_base.py : contenu réel de la base vectorielle.
  1) nombre de passages par document
  2) passages contenant un mot clé (ex. aphteuse), avec document et page
À placer à côté de config.py. Usage :
  python check_base.py
  python check_base.py aphteuse ampoule onglon
"""
import collections
import sys

import chromadb

import config

mots = [m.lower() for m in sys.argv[1:]] or ["aphteuse", "ampoule", "quarantaine", "vêlage"]

col = chromadb.PersistentClient(path=str(config.DB_DIR)).get_collection(config.COLLECTION)
d = col.get(include=["documents", "metadatas"])
docs, metas = d["documents"], d["metadatas"]


def ident(m):
    return next((m[k] for k in ("id", "source_id", "doc_id", "titre") if k in m), "?")


print(f"Total : {len(docs)} passages\n")
print("Passages par document :")
for k, n in collections.Counter(ident(m) for m in metas).most_common():
    print(f"  {n:4d}  {k}")

for mot in mots:
    trouves = [(ident(m), m.get("page", "?")) for t, m in zip(docs, metas) if mot in t.lower()]
    par_doc = collections.Counter(k for k, _ in trouves)
    print(f"\nMot « {mot} » : {len(trouves)} passage(s)")
    for k, n in par_doc.most_common():
        pages = sorted({p for kk, p in trouves if kk == k}, key=str)
        print(f"  {n:3d}  {k}  pages {pages[:12]}")
