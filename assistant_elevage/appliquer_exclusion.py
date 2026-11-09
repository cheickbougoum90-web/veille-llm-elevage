# -*- coding: utf-8 -*-
"""
appliquer_exclusion.py : exclut de la recherche les pages sans contenu vétérinaire.

À lancer une fois dans assistant_elevage (après appliquer_diversite.py) :  python appliquer_exclusion.py
 - config.py : ajoute EXCLUDE_PAGES (liste de (document, page) ignorés par la recherche)
 - rag.py    : retrieve() ignore ces pages
Sauvegardes : config.py.bak2 et rag.py.bak2. Pour exclure d'autres pages, ajoute-les dans config.EXCLUDE_PAGES.
"""
import re
import shutil
import sys
from pathlib import Path

AJOUT_CONFIG = '''
# Pages sans contenu vétérinaire, écartées de la recherche : elles sortaient en tête pour presque toutes
# les questions (constat par hubs.py). (identifiant du document, numéro de page)
EXCLUDE_PAGES = {
    ("vaudaux-mali-2008", "7"),     # remerciements
    ("vaudaux-mali-2008", "115"),   # guide de questions d'enquête (annexe)
}
'''


def main():
    rag, cfg = Path("rag.py"), Path("config.py")
    if not rag.exists() or not cfg.exists():
        sys.exit("Lance ce script dans le dossier assistant_elevage.")
    r, c = rag.read_text(encoding="utf-8"), cfg.read_text(encoding="utf-8")
    if "EXCLUDE_PAGES" in c and "EXCLUDE_PAGES" in r:
        sys.exit("Déjà appliqué : rien à faire.")
    if "MAX_PER_DOC" not in r:
        sys.exit("Lance d'abord appliquer_diversite.py.")

    ancien1 = '    max_doc = getattr(config, "MAX_PER_DOC", 0)\n    candidats = max(k * 4, 16) if max_doc else k\n'
    nouveau1 = ('    max_doc = getattr(config, "MAX_PER_DOC", 0)\n'
                '    exclus = getattr(config, "EXCLUDE_PAGES", set())\n'
                '    candidats = max(k * 4, 16) if (max_doc or exclus) else k\n')
    ancien2 = '        doc = m.get("id") or m.get("source_id") or m.get("titre") or "?"\n'
    nouveau2 = ancien2 + '        if (str(doc), str(m.get("page", ""))) in exclus:\n            continue\n'
    if ancien1 not in r or ancien2 not in r:
        sys.exit("retrieve() n'a pas la forme attendue : rien n'a été changé. Envoie-moi rag.py.")

    m = re.search(r"^MAX_PER_DOC\s*=.*$", c, flags=re.M)
    if not m:
        sys.exit("MAX_PER_DOC introuvable dans config.py : rien n'a été changé.")

    shutil.copy(rag, "rag.py.bak2")
    shutil.copy(cfg, "config.py.bak2")
    rag.write_text(r.replace(ancien1, nouveau1).replace(ancien2, nouveau2), encoding="utf-8")
    cfg.write_text(c[: m.end()] + "\n" + AJOUT_CONFIG + c[m.end():], encoding="utf-8")
    print("OK : EXCLUDE_PAGES ajouté dans config.py, retrieve() mis à jour.")
    print("Vérifie avec : python hubs.py   puis   python diag_refus.py Q03 Q07 Q14")


if __name__ == "__main__":
    main()
