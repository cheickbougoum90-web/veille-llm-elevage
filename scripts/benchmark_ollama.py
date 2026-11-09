#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
benchmark_ollama.py
Outil du travail de veille : assistant d'élevage en local sur GPU.

Trois commandes :
  verifier   contrôle qu'Ollama répond et que les modèles sont installés
  bench      mesure la vitesse, la VRAM et le temps de chargement de chaque modèle
  repondre   fait répondre chaque modèle aux questions, puis anonymise les réponses
             pour la notation en aveugle

Prérequis : Windows 11, Ollama lancé, Python 3.10 ou plus, puis : pip install requests

Exemples :
  python benchmark_ollama.py verifier
  python benchmark_ollama.py bench
  python benchmark_ollama.py bench --modeles qwen3.5:9b --essais 1
  python benchmark_ollama.py repondre --questions questions.csv

Les fichiers CSV produits suivent le format Excel français (séparateur point-virgule,
virgule décimale) pour s'ouvrir directement dans Excel.
"""

import argparse
import csv
import random
import statistics
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

# ------------------------------ PARAMÈTRES À ADAPTER ------------------------------
OLLAMA = "http://localhost:11434"
# Vérifier les noms exacts avec la commande `ollama list` (ou sur ollama.com/library).
MODELES = ["qwen3.5:9b", "gemma4:e4b", "gemma4:12b"]
CONTEXTES = [4096, 8192]     # tailles de contexte testées (en tokens)
ESSAIS = 3                   # nombre d'essais par mesure
TEMPERATURE = 0.2            # identique pour tous les modèles
SEED = 42                    # rend les essais reproductibles
PAUSE_S = 3                  # pause après le déchargement d'un modèle (secondes)
MAX_TOKENS_BENCH = 300       # longueur maximale des réponses du benchmark
MAX_TOKENS_REPONSE = 400     # longueur maximale des réponses aux 30 questions
# ----------------------------------------------------------------------------------

SYSTEME = (
    "Tu es un assistant d'aide à l'élevage (bovins, ovins, caprins) destiné à des éleveurs. "
    "Réponds en français, de façon claire, simple et prudente. "
    "Si la situation semble grave ou incertaine, recommande de consulter un vétérinaire. "
    "N'invente jamais de dose de médicament. Si tu ne sais pas, dis-le."
)

PROMPTS = {
    "court": "Quels sont les signes d'une fièvre aphteuse chez un bovin et que faire en premier ?",
    "moyen": ("Explique en dix lignes comment organiser un calendrier de vaccination pour un troupeau "
              "de 30 bovins et 50 moutons pendant la saison sèche."),
}

PASSAGE = (
    "La vaccination du troupeau suit un calendrier précis défini avec le vétérinaire. "
    "Les animaux malades sont isolés, les abreuvoirs sont nettoyés régulièrement et les naissances "
    "sont notées dans un carnet. En saison sèche, l'alimentation est complétée par du fourrage "
    "conservé et des compléments minéraux. "
)

TYPES = ("court", "moyen", "long")


def prompt_pour(type_prompt, num_ctx):
    """Construit le prompt. Le type 'long' remplit environ 60 % du contexte (estimation : 4 caractères par token)."""
    if type_prompt != "long":
        return PROMPTS[type_prompt]
    cible_caracteres = int(num_ctx * 0.6) * 4
    repetitions = max(1, cible_caracteres // len(PASSAGE))
    return ("Voici un document :\n" + PASSAGE * repetitions +
            "\nQuestion : résume en trois phrases les points clés de ce document.")


# ------------------------------ ACCÈS À OLLAMA ------------------------------

def requete(methode, chemin, timeout=900, **kw):
    try:
        return requests.request(methode, OLLAMA + chemin, timeout=timeout, **kw)
    except requests.exceptions.ConnectionError:
        sys.exit("Ollama ne répond pas. Lance l'application Ollama, puis recommence.")


def modeles_installes():
    r = requete("GET", "/api/tags", timeout=15)
    r.raise_for_status()
    return [m["name"] for m in r.json().get("models", [])]


def verifier(modeles):
    dispo = modeles_installes()
    print("Modèles installés :", ", ".join(dispo) if dispo else "aucun")
    ok = True
    for m in modeles:
        if m not in dispo and f"{m}:latest" not in dispo:
            ok = False
            print(f"ATTENTION : {m} est introuvable. Corrige son nom dans MODELES, "
                  f"ou télécharge-le avec : ollama pull {m}")
    if ok:
        print("Tous les modèles demandés sont installés.")
    return ok


def generer(modele, prompt, num_ctx, max_tokens, systeme=None):
    charge = {
        "model": modele, "prompt": prompt, "stream": False, "keep_alive": "10m",
        "think": False,  # désactive le mode raisonnement pour mesurer des réponses directes
        "options": {"temperature": TEMPERATURE, "seed": SEED,
                    "num_ctx": num_ctx, "num_predict": max_tokens},
    }
    if systeme:
        charge["system"] = systeme
    r = requete("POST", "/api/generate", json=charge)
    if r.status_code == 400 and "think" in r.text.lower():
        charge.pop("think")  # certains modèles n'ont pas de mode raisonnement
        r = requete("POST", "/api/generate", json=charge)
    r.raise_for_status()
    return r.json()


def decharger(modele):
    """Décharge le modèle de la mémoire pour pouvoir mesurer un vrai temps de chargement."""
    requete("POST", "/api/generate", json={"model": modele, "keep_alive": 0}, timeout=60)
    time.sleep(PAUSE_S)


def part_gpu(modele):
    """Retourne (taille du modèle en Go, part chargée sur le GPU en %). 100 % = tout en VRAM."""
    r = requete("GET", "/api/ps", timeout=15)
    for m in r.json().get("models", []):
        if m.get("name", "").startswith(modele) or m.get("model", "").startswith(modele):
            taille, vram = m.get("size", 0), m.get("size_vram", 0)
            return round(taille / 1e9, 2), (round(100 * vram / taille, 1) if taille else None)
    return None, None


def vram_utilisee_mo():
    """Mémoire GPU utilisée au total, lue avec nvidia-smi (None si indisponible)."""
    try:
        sortie = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10).stdout
        return int(sortie.strip().splitlines()[0])
    except Exception:
        return None


def par_seconde(nombre, duree_ns):
    return round(nombre / (duree_ns / 1e9), 2) if nombre and duree_ns else 0.0


# ------------------------------ FICHIERS CSV ------------------------------

def formater(valeur):
    if isinstance(valeur, float):
        return str(valeur).replace(".", ",")
    return "" if valeur is None else valeur


def ecrire_csv(chemin, lignes, champs):
    with open(chemin, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=champs, delimiter=";")
        w.writeheader()
        for ligne in lignes:
            w.writerow({c: formater(ligne.get(c)) for c in champs})
    print(f"Fichier écrit : {chemin}")


def lire_csv(chemin):
    texte = Path(chemin).read_text(encoding="utf-8-sig")
    entete = texte.splitlines()[0]
    delimiteur = ";" if entete.count(";") >= entete.count(",") else ","
    with open(chemin, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f, delimiter=delimiteur))


# ------------------------------ COMMANDE : bench ------------------------------

CHAMPS_DETAIL = ["horodatage", "modele", "num_ctx", "type_prompt", "essai", "chargement_s",
                 "tokens_prompt", "tokens_generes", "tok_s_generation", "tok_s_prompt",
                 "vram_totale_mo", "vram_ajoutee_mo", "taille_modele_go", "part_gpu_pct"]

CHAMPS_RESUME = ["modele", "num_ctx", "type_prompt", "tok_s_generation_moy", "tok_s_generation_ecart",
                 "tok_s_prompt_moy", "vram_totale_max_mo", "vram_ajoutee_max_mo", "part_gpu_min_pct",
                 "chargement_s", "essais"]


def commande_bench(a):
    if not verifier(a.modeles):
        sys.exit("Corrige d'abord les modèles manquants.")
    detail = []
    for modele in a.modeles:
        for ctx in a.contextes:
            print(f"\n=== {modele} | contexte {ctx} ===")
            decharger(modele)
            base = vram_utilisee_mo()
            try:
                echauffement = generer(modele, "Bonjour", ctx, 8)
            except requests.HTTPError as erreur:
                print("Échec du chargement :", erreur)
                continue
            chargement = round(echauffement.get("load_duration", 0) / 1e9, 2)
            print(f"Chargement : {chargement} s")
            for type_prompt in TYPES:
                prompt = prompt_pour(type_prompt, ctx)
                for essai in range(1, a.essais + 1):
                    r = generer(modele, prompt, ctx, MAX_TOKENS_BENCH)
                    taille, pct = part_gpu(modele)
                    vram = vram_utilisee_mo()
                    ligne = {
                        "horodatage": datetime.now().isoformat(timespec="seconds"),
                        "modele": modele, "num_ctx": ctx, "type_prompt": type_prompt, "essai": essai,
                        "chargement_s": chargement,
                        "tokens_prompt": r.get("prompt_eval_count", 0),
                        "tokens_generes": r.get("eval_count", 0),
                        "tok_s_generation": par_seconde(r.get("eval_count"), r.get("eval_duration")),
                        "tok_s_prompt": par_seconde(r.get("prompt_eval_count"), r.get("prompt_eval_duration")),
                        "vram_totale_mo": vram,
                        "vram_ajoutee_mo": (vram - base) if (vram is not None and base is not None) else None,
                        "taille_modele_go": taille, "part_gpu_pct": pct,
                    }
                    detail.append(ligne)
                    print(f"{type_prompt:6} essai {essai} : {ligne['tok_s_generation']} tok/s, "
                          f"GPU {pct} %, VRAM {vram} Mo")
        decharger(modele)

    sortie = Path(a.sortie)
    sortie.mkdir(exist_ok=True)
    ecrire_csv(sortie / "resultats_detail.csv", detail, CHAMPS_DETAIL)

    groupes = {}
    for ligne in detail:
        groupes.setdefault((ligne["modele"], ligne["num_ctx"], ligne["type_prompt"]), []).append(ligne)
    resume = []
    for (modele, ctx, type_prompt), lignes in groupes.items():
        vitesses = [l["tok_s_generation"] for l in lignes]
        vrams = [l["vram_totale_mo"] for l in lignes if l["vram_totale_mo"] is not None]
        ajoutees = [l["vram_ajoutee_mo"] for l in lignes if l["vram_ajoutee_mo"] is not None]
        parts = [l["part_gpu_pct"] for l in lignes if l["part_gpu_pct"] is not None]
        resume.append({
            "modele": modele, "num_ctx": ctx, "type_prompt": type_prompt,
            "tok_s_generation_moy": round(statistics.mean(vitesses), 2),
            "tok_s_generation_ecart": round(statistics.pstdev(vitesses), 2),
            "tok_s_prompt_moy": round(statistics.mean(l["tok_s_prompt"] for l in lignes), 2),
            "vram_totale_max_mo": max(vrams) if vrams else None,
            "vram_ajoutee_max_mo": max(ajoutees) if ajoutees else None,
            "part_gpu_min_pct": min(parts) if parts else None,
            "chargement_s": lignes[0]["chargement_s"], "essais": len(lignes),
        })
    ecrire_csv(sortie / "resultats_resume.csv", resume, CHAMPS_RESUME)
    print("\nLecture : 'part_gpu_min_pct' à 100 % = le modèle tient entièrement dans la VRAM. "
          "En dessous, une partie tourne sur le processeur et la vitesse chute.")


# ------------------------------ COMMANDE : repondre ------------------------------

def commande_repondre(a):
    questions = lire_csv(a.questions)  # colonnes attendues : id, question (categorie facultative)
    if not questions or "question" not in questions[0] or "id" not in questions[0]:
        sys.exit("Le fichier de questions doit avoir les colonnes : id ; question")
    if not verifier(a.modeles):
        sys.exit("Corrige d'abord les modèles manquants.")

    brutes = []
    for modele in a.modeles:
        print(f"\n=== {modele} ===")
        decharger(modele)
        for q in questions:
            r = generer(modele, q["question"], a.contexte, MAX_TOKENS_REPONSE, systeme=SYSTEME)
            brutes.append({"modele": modele, "id_question": q["id"], "question": q["question"],
                           "reponse": r.get("response", "").strip()})
            print(f"{q['id']} : {len(brutes[-1]['reponse'])} caractères")
        decharger(modele)

    sortie = Path(a.sortie)
    sortie.mkdir(exist_ok=True)
    ecrire_csv(sortie / "reponses_brutes_NE_PAS_MONTRER.csv", brutes,
               ["modele", "id_question", "question", "reponse"])

    melange = brutes[:]
    random.Random(SEED).shuffle(melange)
    anonymes, cle = [], []
    for i, ligne in enumerate(melange, start=1):
        code = f"R{i:03d}"
        anonymes.append({"code": code, "id_question": ligne["id_question"],
                         "question": ligne["question"], "reponse": ligne["reponse"]})
        cle.append({"code": code, "modele": ligne["modele"]})
    ecrire_csv(sortie / "reponses_anonymes.csv", anonymes, ["code", "id_question", "question", "reponse"])
    ecrire_csv(sortie / "cle_modeles.csv", cle, ["code", "modele"])
    print("\nDonne reponses_anonymes.csv aux évaluateurs. Garde cle_modeles.csv de côté "
          "jusqu'à la fin de la notation.")


# ------------------------------ PROGRAMME PRINCIPAL ------------------------------

def main():
    p = argparse.ArgumentParser(description="Benchmark Ollama pour le travail de veille")
    sp = p.add_subparsers(dest="commande", required=True)

    v = sp.add_parser("verifier", help="contrôle Ollama et les modèles")
    v.add_argument("--modeles", nargs="+", default=MODELES)

    b = sp.add_parser("bench", help="mesure vitesse, VRAM et chargement")
    b.add_argument("--modeles", nargs="+", default=MODELES)
    b.add_argument("--contextes", nargs="+", type=int, default=CONTEXTES)
    b.add_argument("--essais", type=int, default=ESSAIS)
    b.add_argument("--sortie", default="resultats")

    r = sp.add_parser("repondre", help="réponses aux questions, anonymisées")
    r.add_argument("--questions", required=True, help="fichier CSV avec les colonnes id ; question")
    r.add_argument("--modeles", nargs="+", default=MODELES)
    r.add_argument("--contexte", type=int, default=4096)
    r.add_argument("--sortie", default="reponses")

    a = p.parse_args()
    if a.commande == "verifier":
        sys.exit(0 if verifier(a.modeles) else 1)
    elif a.commande == "bench":
        commande_bench(a)
    else:
        commande_repondre(a)


if __name__ == "__main__":
    main()
