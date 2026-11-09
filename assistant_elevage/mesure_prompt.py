# -*- coding: utf-8 -*-
"""
mesure_prompt.py : mesure la taille réelle (en tokens) des prompts envoyés au modèle par le RAG.

Pourquoi : le RAG envoie le message système + 4 passages de 300 à 500 mots + la question.
Si le total (plus la réponse) dépasse NUM_CTX (config.py), Ollama peut tronquer le prompt sans erreur
et fausser toute l'évaluation. Ce script vérifie la marge AVANT de lancer run_eval.py.

À placer à côté de rag.py et config.py. Ollama doit tourner, la base (ingest.py) doit exister.

Usage :
  python mesure_prompt.py
  python mesure_prompt.py --modele gemma4:12b
  python mesure_prompt.py --questions Partie_C_questions_et_grille.xlsx
"""
import argparse
import re
import statistics
import sys

import requests
from openpyxl import load_workbook

import config
import rag

MARGE_REPONSE = 400  # tokens à garder pour la réponse du modèle


def lire_questions(chemin):
    ws = load_workbook(chemin, data_only=True)["Questions"]
    return [(r[0], r[2]) for r in ws.iter_rows(min_row=2, values_only=True)
            if r[0] and re.fullmatch(r"Q\d+", str(r[0]))]


def compter_tokens(modele, messages):
    """Taille exacte du prompt pour ce modèle (contexte élargi à 8192 pour ne pas voir une valeur tronquée)."""
    charge = {"model": modele, "messages": messages, "stream": False, "think": False,
              "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 1}}
    url = f"{config.OLLAMA_URL}/api/chat"
    try:
        r = requests.post(url, json=charge, timeout=config.REQUEST_TIMEOUT)
        if r.status_code == 400 and "think" in r.text.lower():
            charge.pop("think")
            r = requests.post(url, json=charge, timeout=config.REQUEST_TIMEOUT)
        r.raise_for_status()
    except requests.ConnectionError:
        sys.exit("Ollama ne répond pas. Lance Ollama, puis recommence.")
    return r.json().get("prompt_eval_count")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--modele", default=config.OLLAMA_MODEL)
    p.add_argument("--questions", default="Partie_C_questions_et_grille.xlsx")
    a = p.parse_args()

    questions = lire_questions(a.questions)
    print(f"Modèle : {a.modele} | NUM_CTX = {config.NUM_CTX} | MAX_DISTANCE = {config.MAX_DISTANCE} | TOP_K = {config.TOP_K}\n")
    print(f"{'id':<5} {'distance':>8}  {'tokens':>7}  statut")
    tailles, refus = [], 0
    for qid, texte in questions:
        passages = rag.retrieve(texte)
        dist = passages[0].distance if passages else None
        if not passages or dist > config.MAX_DISTANCE:
            refus += 1
            print(f"{qid:<5} {dist if dist is None else round(dist, 3):>8}  {'-':>7}  refus par le seuil (le modèle n'est pas appelé)")
            continue
        n = compter_tokens(a.modele, rag.build_messages(texte, passages))
        tailles.append(n)
        etat = "OK" if n + MARGE_REPONSE <= config.NUM_CTX else "TROP LONG pour NUM_CTX"
        print(f"{qid:<5} {round(dist, 3):>8}  {n:>7}  {etat}")

    print("\n--- Résumé ---")
    print(f"Questions refusées par le seuil de distance : {refus}/{len(questions)}")
    if tailles:
        mx = max(tailles)
        print(f"Taille du prompt (tokens) : min {min(tailles)}, moyenne {round(statistics.mean(tailles))}, max {mx}")
        print(f"Place nécessaire dans le contexte (max + {MARGE_REPONSE} pour la réponse) : {mx + MARGE_REPONSE} sur NUM_CTX = {config.NUM_CTX}")
        trop = sum(1 for t in tailles if t + MARGE_REPONSE > config.NUM_CTX)
        if trop:
            print(f"ATTENTION : {trop} prompt(s) risquent d'être tronqués. Réduire TOP_K ou CHUNK_WORDS, ou passer NUM_CTX à 8192.")
        else:
            print("Marge suffisante : NUM_CTX convient.")


if __name__ == "__main__":
    main()
