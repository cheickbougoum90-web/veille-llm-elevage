# -*- coding: utf-8 -*-
"""
maj_licences.py : remplace « conditions de réutilisation non lues » par les conditions réellement lues
(OMSA/WOAH et FAO, le 9 novembre 2026) dans sources.csv.

À lancer dans assistant_elevage :  python maj_licences.py
 - lit sources.csv (séparateur , ou ; détecté, encodage conservé), sauvegarde sources.csv.bak
 - met à jour la colonne de licence pour woah-fievre-aphteuse, woah-ppcb, woah-brucellose et fao-dnc-2025
 - affiche chaque changement ; relancer ne change rien
Ensuite : python ingest.py  (reconstruit la base : les licences affichées dans l'interface viennent de là)
"""
import csv
import io
import shutil
import sys
from pathlib import Path

LU = "lues le 09/11/2026"
NOUVELLES = {
    "woah-fievre-aphteuse": f"© OMSA (WOAH). Réutilisation sans modification, avec mention de la source, pour l'information et la sensibilisation ; autre usage (dont commercial) : accord écrit de l'OMSA (conditions {LU})",
    "woah-ppcb":            f"© OMSA (WOAH). Réutilisation sans modification, avec mention de la source, pour l'information et la sensibilisation ; autre usage (dont commercial) : accord écrit de l'OMSA (conditions {LU})",
    "woah-brucellose":      f"© OMSA (WOAH). Réutilisation sans modification, avec mention de la source, pour l'information et la sensibilisation ; autre usage (dont commercial) : accord écrit de l'OMSA (conditions {LU})",
    "fao-dnc-2025":         f"© FAO. Copie autorisée pour l'étude, la recherche et l'enseignement et pour des produits non commerciaux, avec mention de la FAO (conditions générales de fao.org {LU})",
}


def main():
    p = Path("sources.csv")
    if not p.exists():
        sys.exit("sources.csv introuvable : lance ce script dans le dossier assistant_elevage.")
    brut = p.read_bytes()
    bom = brut.startswith(b"\xef\xbb\xbf")
    texte = brut.decode("utf-8-sig")
    try:
        dialecte = csv.Sniffer().sniff(texte[:4000], delimiters=",;\t")
    except csv.Error:
        dialecte = csv.excel
    lecteur = csv.reader(io.StringIO(texte), dialecte)
    lignes = list(lecteur)
    entete = [h.strip().lower() for h in lignes[0]]
    col_id = next((i for i, h in enumerate(entete) if h in ("id", "identifiant", "doc_id", "source_id")), None)
    col_lic = next((i for i, h in enumerate(entete) if "licen" in h or "droits" in h), None)
    if col_id is None or col_lic is None:
        sys.exit(f"Colonnes introuvables (en-tête : {lignes[0]}). Envoie-moi l'en-tête de sources.csv.")

    changements = 0
    for ligne in lignes[1:]:
        if len(ligne) <= max(col_id, col_lic):
            continue
        doc = ligne[col_id].strip()
        if doc in NOUVELLES and ligne[col_lic].strip() != NOUVELLES[doc]:
            print(f"{doc}\n  avant : {ligne[col_lic]}\n  après : {NOUVELLES[doc]}\n")
            ligne[col_lic] = NOUVELLES[doc]
            changements += 1
    if not changements:
        sys.exit("Rien à changer (déjà à jour, ou identifiants absents).")

    shutil.copy(p, "sources.csv.bak")
    sortie = io.StringIO(newline="")
    ecrivain = csv.writer(sortie, dialecte, lineterminator="\r\n")
    ecrivain.writerows(lignes)
    p.write_bytes((b"\xef\xbb\xbf" if bom else b"") + sortie.getvalue().encode("utf-8"))
    print(f"OK : {changements} licence(s) mise(s) à jour (sauvegarde sources.csv.bak).")
    print("Étape suivante : python ingest.py")


if __name__ == "__main__":
    main()
