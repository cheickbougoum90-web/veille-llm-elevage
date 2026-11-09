# -*- coding: utf-8 -*-
"""
appliquer_diversite.py : ajoute la règle « au plus N passages par document » à la recherche.

À lancer une fois dans assistant_elevage :  python appliquer_diversite.py
 - config.py : ajoute MAX_PER_DOC (2 par défaut, réglable avec la variable d'environnement MAX_PER_DOC ; 0 = désactivé)
 - rag.py    : remplace retrieve() : on récupère plus de candidats, on limite par document, on garde TOP_K
Les originaux sont sauvegardés en config.py.bak et rag.py.bak. Relancer le script ne change rien (idempotent).
"""
import re
import shutil
import sys
from pathlib import Path

NOUVEAU_RETRIEVE = '''def retrieve(question: str, k: int | None = None) -> list[Passage]:
    """Passages les plus proches de la question, avec au plus config.MAX_PER_DOC passages par document.

    Sans cette limite, la thèse Vaudaux (90 passages sur 188) occupe presque tout le top K et les petits
    documents (WOAH, RECA, CIRAD) n'apparaissent jamais. MAX_PER_DOC = 0 désactive la limite.
    """
    from embeddings import embed_query

    k = k or config.TOP_K
    max_doc = getattr(config, "MAX_PER_DOC", 0)
    candidats = max(k * 4, 16) if max_doc else k
    res = _collection().query(query_embeddings=[embed_query(question)], n_results=candidats,
                              include=["documents", "metadatas", "distances"])
    triplets = list(zip(res["documents"][0], res["metadatas"][0], res["distances"][0]))

    gardes, ecartes, compte = [], [], {}
    for d, m, dist in triplets:
        doc = m.get("id") or m.get("source_id") or m.get("titre") or "?"
        if max_doc and compte.get(doc, 0) >= max_doc:
            ecartes.append((d, m, dist))
            continue
        compte[doc] = compte.get(doc, 0) + 1
        gardes.append((d, m, dist))
        if len(gardes) == k:
            break
    gardes += ecartes[: k - len(gardes)]   # complète si le corpus est trop petit pour remplir K
    return [Passage(i + 1, d, m, float(dist)) for i, (d, m, dist) in enumerate(gardes)]


'''

LIGNE_CONFIG = (
    '\n# Au plus N passages du même document dans les passages donnés au modèle (0 = pas de limite)\n'
    'MAX_PER_DOC = int(os.getenv("MAX_PER_DOC", "2"))\n'
)


def main():
    rag, cfg = Path("rag.py"), Path("config.py")
    if not rag.exists() or not cfg.exists():
        sys.exit("Lance ce script dans le dossier assistant_elevage (rag.py et config.py introuvables).")

    c = cfg.read_text(encoding="utf-8")
    r = rag.read_text(encoding="utf-8")
    if "MAX_PER_DOC" in c and "MAX_PER_DOC" in r:
        sys.exit("Déjà appliqué : rien à faire.")

    debut = r.find("def retrieve(")
    fin = r.find("# ---------------------------------------------------------------- prompt", debut)
    if debut < 0 or fin < 0:
        sys.exit("Fonction retrieve() introuvable dans rag.py : modification annulée, rien n'a été changé.")
    m = re.search(r"^TOP_K\s*=.*$", c, flags=re.M)
    if not m:
        sys.exit("Ligne TOP_K introuvable dans config.py : modification annulée, rien n'a été changé.")

    shutil.copy(rag, "rag.py.bak")
    shutil.copy(cfg, "config.py.bak")
    rag.write_text(r[:debut] + NOUVEAU_RETRIEVE + r[fin:], encoding="utf-8")
    cfg.write_text(c[: m.end()] + LIGNE_CONFIG + c[m.end():], encoding="utf-8")
    print("OK : retrieve() mis à jour dans rag.py, MAX_PER_DOC ajouté dans config.py (sauvegardes .bak créées).")
    print("Vérifie avec : python diag_refus.py Q03 Q14 Q21")


if __name__ == "__main__":
    main()
