"""Réglages centraux du RAG. Tout se change ici ou par variable d'environnement."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DOCS_DIR = BASE_DIR / "docs"            # PDF / TXT / MD des documents vétérinaires
SOURCES_CSV = BASE_DIR / "sources.csv"  # fiche des sources (source, date, licence)
DB_DIR = BASE_DIR / "chroma_db"         # base vectorielle locale (créée par ingest.py)
COLLECTION = "elevage"

# --- Embeddings : sur processeur, pour ne pas occuper la VRAM du modèle ---
# Alternative plus précise mais plus lourde : "BAAI/bge-m3"
EMBED_MODEL = os.getenv("EMBED_MODEL", "intfloat/multilingual-e5-small")
EMBED_DEVICE = "cpu"

# --- Découpage (en mots) ---
CHUNK_WORDS = 400      # cible par passage (le sujet demande 300 à 500)
CHUNK_MIN_WORDS = 300  # on ne coupe pas avant d'avoir au moins ça
CHUNK_MAX_WORDS = 500
OVERLAP_WORDS = 60     # recouvrement entre deux passages
DROP_BELOW_WORDS = 40  # passages trop courts ignorés

# --- Recherche ---
TOP_K = int(os.getenv("TOP_K", "4"))
# Au plus N passages du même document dans les passages donnés au modèle (0 = pas de limite)
MAX_PER_DOC = int(os.getenv("MAX_PER_DOC", "3"))

# Plafond particulier par document : la thèse Vaudaux (90 passages) est limitée à 1 passage par réponse.
# Les autres documents suivent MAX_PER_DOC.
MAX_PER_DOC_BY_ID = {"vaudaux-mali-2008": 1}


# Pages sans contenu vétérinaire, écartées de la recherche : elles sortaient en tête pour presque toutes
# les questions (constat par hubs.py). (identifiant du document, numéro de page)
EXCLUDE_PAGES = {
    ("vaudaux-mali-2008", "7"),     # remerciements
    ("vaudaux-mali-2008", "115"),   # guide de questions d'enquête (annexe)
}


# Distance cosinus (0 = identique). Au-delà de ce seuil, on refuse de répondre
# SANS appeler le modèle. À calibrer avec eval_citations.py (voir README).
MAX_DISTANCE = float(os.getenv("MAX_DISTANCE", "0.17"))

# --- Modèle (Ollama) ---
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
# Le nom exact du tag doit être vérifié avec `ollama list` sur le PC.
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:9b")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.2"))  # identique pour tous les modèles
NUM_CTX = int(os.getenv("NUM_CTX", "4096"))
REQUEST_TIMEOUT = 300

DISCLAIMER = (
    "Cet assistant est une aide d'information : il ne remplace pas un vétérinaire. "
    "En cas de doute ou d'animal malade, consultez un vétérinaire ou un agent de santé animale."
)
REFUSAL = (
    "Je ne sais pas : les documents dont je dispose ne contiennent pas cette information. "
    "Je préfère ne pas inventer de réponse. Consultez un vétérinaire ou un agent de santé animale."
)
