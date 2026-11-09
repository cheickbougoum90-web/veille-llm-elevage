# -*- coding: utf-8 -*-
"""
appliquer_prompt.py : assouplit la règle 3 du SYSTEM_PROMPT de rag.py pour autoriser les réponses partielles.

Avant : si les extraits ne contiennent pas la réponse, le modèle doit répondre exactement INFORMATION_ABSENTE.
Après : s'il y a une partie de la réponse, il la donne (avec citations) et dit ce qui manque ;
        il ne répond INFORMATION_ABSENTE que si les extraits ne contiennent rien d'utile.

À lancer une fois dans assistant_elevage :  python appliquer_prompt.py
Sauvegarde : rag.py.bak3. Relancer ne change rien.
"""
import re
import shutil
import sys
from pathlib import Path

NOUVELLE_REGLE = (
    "3. Si les extraits contiennent une partie de la réponse, donne cette partie avec les citations,\n"
    "   puis dis clairement ce qui manque (par exemple : « Les extraits ne précisent pas ... »).\n"
    "   Si les extraits ne contiennent rien d'utile pour la question, tu réponds exactement : {ABSENT_TAG}\n"
    "   (rien d'autre). N'invente jamais. Ne complète jamais avec tes connaissances générales."
)


def main():
    p = Path("rag.py")
    if not p.exists():
        sys.exit("Lance ce script dans le dossier assistant_elevage.")
    r = p.read_text(encoding="utf-8")
    if "partie de la réponse" in r:
        sys.exit("Déjà appliqué : rien à faire.")
    motif = re.compile(r"3\.\s+Si les extraits ne contiennent pas la réponse.*?connaissances\s+générales\.", re.S)
    if not motif.search(r):
        sys.exit("Règle 3 introuvable sous la forme attendue : rien n'a été changé. Envoie-moi rag.py.")
    shutil.copy(p, "rag.py.bak3")
    p.write_text(motif.sub(lambda m: NOUVELLE_REGLE, r, count=1), encoding="utf-8")
    print("OK : règle 3 mise à jour dans rag.py (sauvegarde rag.py.bak3).")
    print("Vérifie : python -c \"import rag; print(rag.SYSTEM_PROMPT)\"")


if __name__ == "__main__":
    main()
