# -*- coding: utf-8 -*-
"""
compare_embeddings.py : quel modèle d'embeddings retrouve le mieux les bons documents ?

Pour chaque question de C qui a des documents attendus, on regarde si au moins un
document attendu figure dans les K premiers passages (K = config.TOP_K, puis 8).
On réutilise le texte des passages déjà dans la base : pas besoin de réingérer.

Il faut Internet pour télécharger les modèles la première fois :
  PowerShell : Remove-Item Env:HF_HUB_OFFLINE   (ou ouvrir un nouveau terminal)
Usage (dans assistant_elevage, venv actif) :
  python compare_embeddings.py
  python compare_embeddings.py intfloat/multilingual-e5-base BAAI/bge-m3
"""
import re
import sys
import time

import chromadb
import numpy as np
from openpyxl import load_workbook
from sentence_transformers import SentenceTransformer

import config

CLASSEUR = "Partie_C_questions_et_grille.xlsx"
MODELES = sys.argv[1:] or [
    "intfloat/multilingual-e5-small",   # modèle actuel
    "intfloat/multilingual-e5-base",
    "BAAI/bge-m3",
]


def prefixes(nom):
    # Les modèles e5 exigent ces préfixes ; bge-m3 n'en veut pas.
    return ("passage: ", "query: ") if "e5" in nom.lower() else ("", "")


def questions():
    ws = load_workbook(CLASSEUR, data_only=True)["Questions"]
    out = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        if r[0] and re.fullmatch(r"Q\d+", str(r[0])):
            att = [d.strip() for d in str(r[4] or "").split(";") if d.strip() and not d.startswith("(")]
            if att:
                out.append((r[0], r[2], set(att)))
    return out


col = chromadb.PersistentClient(path=str(config.DB_DIR)).get_collection(config.COLLECTION)
d = col.get(include=["documents", "metadatas"])
textes = d["documents"]
ids = [next((m[k] for k in ("id", "source_id", "doc_id", "titre") if k in m), "?") for m in d["metadatas"]]
qs = questions()
print(f"{len(textes)} passages, {len(qs)} questions avec documents attendus, TOP_K = {config.TOP_K}\n")

resume = []
for nom in MODELES:
    t0 = time.time()
    model = SentenceTransformer(nom, device="cpu")
    pp, pq = prefixes(nom)
    P = model.encode([pp + t for t in textes], normalize_embeddings=True, batch_size=16)
    Q = model.encode([pq + q for _, q, _ in qs], normalize_embeddings=True)
    sims = Q @ P.T
    hit_k = hit_8 = 0
    rangs, ratees = [], []
    for i, (qid, _, att) in enumerate(qs):
        ordre = np.argsort(-sims[i])
        premiers = [ids[j] for j in ordre]
        rang = next((r for r, k in enumerate(premiers, 1) if k in att), None)
        rangs.append(rang if rang else 999)
        hit_k += bool(rang and rang <= config.TOP_K)
        hit_8 += bool(rang and rang <= 8)
        if not (rang and rang <= config.TOP_K):
            ratees.append(qid)
    n = len(qs)
    mrr = np.mean([1 / r if r < 999 else 0 for r in rangs])
    resume.append((nom, hit_k, hit_8, n, mrr, ratees, time.time() - t0))
    print(f"{nom}\n  bon document dans le top {config.TOP_K} : {hit_k}/{n} ({100 * hit_k / n:.0f} %)"
          f" | top 8 : {hit_8}/{n} | rang inverse moyen : {mrr:.2f} | {time.time() - t0:.0f} s")
    print(f"  questions ratées : {', '.join(ratees) or 'aucune'}\n")

print("--- Résumé ---")
for nom, hk, h8, n, mrr, _, _ in sorted(resume, key=lambda x: -x[1]):
    print(f"{hk:3d}/{n} top {config.TOP_K} | {h8:3d}/{n} top 8 | MRR {mrr:.2f} | {nom}")
