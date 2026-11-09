# -*- coding: utf-8 -*-
"""
appliquer_plafond.py : plafond par document (au lieu d'un plafond identique pour tous).

Constat (voir_passages.py, Q15) : avec « 1 passage maximum par document », le passage « Prévention et
contrôle » de woah-brucellose était écarté au profit de la définition du même document.
Nouvelle règle : un plafond strict seulement pour la thèse Vaudaux (90 passages, surtout des enquêtes
sociales, qui encombrait les résultats) ; les autres documents suivent MAX_PER_DOC.

À lancer une fois dans assistant_elevage (après appliquer_diversite.py et appliquer_exclusion.py) :
    python appliquer_plafond.py
Sauvegardes : rag.py.bak4 et config.py.bak4. Relancer ne change rien.
"""
import re
import shutil
import sys
from pathlib import Path

AJOUT_CONFIG = '''
# Plafond particulier par document : la thèse Vaudaux (90 passages) est limitée à 1 passage par réponse.
# Les autres documents suivent MAX_PER_DOC.
MAX_PER_DOC_BY_ID = {"vaudaux-mali-2008": 1}
'''


def main():
    rag, cfg = Path("rag.py"), Path("config.py")
    if not rag.exists() or not cfg.exists():
        sys.exit("Lance ce script dans le dossier assistant_elevage.")
    r, c = rag.read_text(encoding="utf-8"), cfg.read_text(encoding="utf-8")
    if "MAX_PER_DOC_BY_ID" in c and "MAX_PER_DOC_BY_ID" in r:
        sys.exit("Déjà appliqué : rien à faire.")
    if "EXCLUDE_PAGES" not in r:
        sys.exit("Lance d'abord appliquer_diversite.py puis appliquer_exclusion.py.")

    a1 = '    exclus = getattr(config, "EXCLUDE_PAGES", set())\n    candidats = max(k * 4, 16) if (max_doc or exclus) else k\n'
    n1 = ('    exclus = getattr(config, "EXCLUDE_PAGES", set())\n'
          '    par_doc = getattr(config, "MAX_PER_DOC_BY_ID", {})\n'
          '    candidats = max(k * 4, 16) if (max_doc or par_doc or exclus) else k\n')
    a2 = '        if max_doc and compte.get(doc, 0) >= max_doc:\n'
    n2 = ('        limite = par_doc.get(doc, max_doc)\n'
          '        if limite and compte.get(doc, 0) >= limite:\n')
    if a1 not in r or a2 not in r:
        sys.exit("retrieve() n'a pas la forme attendue : rien n'a été changé. Envoie-moi rag.py.")
    m = re.search(r"^MAX_PER_DOC\s*=.*$", c, flags=re.M)
    if not m:
        sys.exit("MAX_PER_DOC introuvable dans config.py : rien n'a été changé.")

    shutil.copy(rag, "rag.py.bak4")
    shutil.copy(cfg, "config.py.bak4")
    rag.write_text(r.replace(a1, n1).replace(a2, n2), encoding="utf-8")
    cfg.write_text(c[: m.end()] + "\n" + AJOUT_CONFIG + c[m.end():], encoding="utf-8")
    print("OK : plafond par document ajouté (sauvegardes .bak4).")
    print("Étape suivante : python eval_recherche.py")


if __name__ == "__main__":
    main()
