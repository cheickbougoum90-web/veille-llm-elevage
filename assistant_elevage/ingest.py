"""Étapes 2 et 3 du RAG : nettoyer les documents, les découper, créer la base vectorielle.

Usage :  python ingest.py
Les fichiers de docs/ doivent être décrits dans sources.csv (colonne `fichier`).
"""
from __future__ import annotations

import csv
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

import config

# Console Windows (cp1252) : ne jamais planter sur un caractère d'affichage
for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(errors="replace")

SENT_MAX_WORDS = 100  # une unité de découpe ne dépasse jamais ça
SENT_SPLIT = re.compile(r"(?<=[.!?;:])\s+(?=[A-ZÀÂÉÈÊÎÔÙÛÇ«\"(\d•\-])")


# ---------------------------------------------------------------- lecture ----
def read_pdf(path: Path) -> list[tuple[int, str]]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages = [(i + 1, (p.extract_text() or "")) for i, p in enumerate(reader.pages)]
    return _drop_repeated_lines(pages)


def read_text(path: Path) -> list[tuple[int, str]]:
    return [(1, path.read_text(encoding="utf-8", errors="ignore"))]


def _drop_repeated_lines(pages: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """Supprime en-têtes / pieds de page : lignes courtes répétées sur > 40 % des pages,
    cherchées seulement dans les 2 premières et 2 dernières lignes de chaque page."""
    if len(pages) < 4:
        return pages
    norm = lambda ln: re.sub(r"\d+", "#", ln.strip())  # "Page 3 sur 6" == "Page 4 sur 6"

    def edges(txt: str) -> list[tuple[int, str]]:
        lines = [ln for ln in txt.splitlines() if ln.strip()]
        idx = set(range(min(2, len(lines)))) | set(range(max(0, len(lines) - 2), len(lines)))
        return [(i, ln) for i, ln in enumerate(lines) if i in idx and len(ln.strip()) < 90]

    counts: Counter[str] = Counter()
    for _, txt in pages:
        for key in {norm(ln) for _, ln in edges(txt)}:
            counts[key] += 1
    repeated = {k for k, c in counts.items() if c > 0.4 * len(pages)}

    out = []
    for n, txt in pages:
        lines = [ln for ln in txt.splitlines() if ln.strip()]
        drop = {i for i, ln in edges(txt) if norm(ln) in repeated}
        out.append((n, "\n".join(ln for i, ln in enumerate(lines) if i not in drop)))
    return out


# --------------------------------------------------------------- nettoyage ---
def clean(text: str) -> str:
    text = text.replace("­", "").replace("\xa0", " ")
    text = re.sub(r"(\w)-[ \t]*\n[ \t]*([a-zà-ÿ])", r"\1\2", text)  # mots coupés en fin de ligne
    text = re.sub(r"\n{2,}", "\n\n", text)                 # garde les paragraphes
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)           # lignes simples -> espace
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


# ------------------------------------------------------------- découpage -----
def _sentences(text: str) -> list[str]:
    out: list[str] = []
    for para in text.split("\n\n"):
        out += [s.strip() for s in SENT_SPLIT.split(para) if s.strip()]
    return out


def _wc(s: str) -> int:
    return len(s.split())


def chunk_pages(pages: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """Retourne [(page_de_départ, texte)] ; passages de ~300-500 mots avec recouvrement."""
    units: list[tuple[int, str]] = []  # (page, phrase)
    for page, raw in pages:
        for s in _sentences(clean(raw)):
            # phrase géante (tableau mal extrait...) : on la coupe par mots
            words = s.split()
            for i in range(0, len(words), SENT_MAX_WORDS):
                units.append((page, " ".join(words[i:i + SENT_MAX_WORDS])))

    chunks: list[tuple[int, str]] = []
    cur: list[tuple[int, str]] = []
    n = 0
    for page, s in units:
        w = _wc(s)
        # on ferme le passage quand il atteint la cible, ou s'il dépasserait le maximum
        if cur and (n >= config.CHUNK_WORDS or n + w > config.CHUNK_MAX_WORDS):
            chunks.append((cur[0][0], " ".join(x for _, x in cur)))
            # recouvrement : on repart des dernières phrases (~OVERLAP_WORDS mots)
            keep: list[tuple[int, str]] = []
            k = 0
            for item in reversed(cur):
                if k + _wc(item[1]) > 2 * config.OVERLAP_WORDS:
                    break
                keep.insert(0, item)
                k += _wc(item[1])
                if k >= config.OVERLAP_WORDS:
                    break
            cur, n = keep, sum(_wc(x) for _, x in keep)
        cur.append((page, s))
        n += w
    if cur:
        tail = " ".join(x for _, x in cur)
        if chunks and _wc(tail) < config.DROP_BELOW_WORDS * 2:
            pass  # reste trop court : déjà couvert par le recouvrement du passage précédent
        else:
            chunks.append((cur[0][0], tail))
    return [(p, t) for p, t in chunks if _wc(t) >= config.DROP_BELOW_WORDS]


# --------------------------------------------------------------- sources -----
def load_sources() -> dict[str, dict]:
    if not config.SOURCES_CSV.exists():
        sys.exit(f"Fiche des sources introuvable : {config.SOURCES_CSV}")
    with config.SOURCES_CSV.open(encoding="utf-8-sig", newline="") as f:
        return {row["fichier"].strip(): row for row in csv.DictReader(f) if row.get("fichier")}


def build(reset: bool = True) -> int:
    import chromadb

    from embeddings import embed_passages

    sources = load_sources()
    files = sorted(p for p in config.DOCS_DIR.iterdir()
                   if p.suffix.lower() in {".pdf", ".txt", ".md"})
    if not files:
        sys.exit(f"Aucun document dans {config.DOCS_DIR}. Ajoutez des PDF/TXT puis relancez.")

    if reset and config.DB_DIR.exists():
        shutil.rmtree(config.DB_DIR)
    client = chromadb.PersistentClient(path=str(config.DB_DIR))
    col = client.get_or_create_collection(config.COLLECTION, metadata={"hnsw:space": "cosine"})

    total = 0
    for path in files:
        meta = sources.get(path.name)
        if meta is None:
            print(f"  ! {path.name} absent de sources.csv -> ignoré (source, date et licence obligatoires)")
            continue
        pages = read_pdf(path) if path.suffix.lower() == ".pdf" else read_text(path)
        chunks = chunk_pages(pages)
        if not chunks:
            print(f"  ! {path.name} : aucun texte extrait (PDF scanné ? il faudrait de l'OCR)")
            continue
        base = {k: (meta.get(k) or "") for k in ("id", "titre", "organisme", "date", "licence", "url")}
        ids = [f"{base['id']}-{i:03d}" for i in range(len(chunks))]
        metas = [{**base, "fichier": path.name, "page": p} for p, _ in chunks]
        docs = [t for _, t in chunks]
        col.add(ids=ids, documents=docs, metadatas=metas, embeddings=embed_passages(docs))
        words = [_wc(t) for t in docs]
        print(f"  OK  {path.name}: {len(chunks)} passages (mots : min {min(words)}, max {max(words)})")
        total += len(chunks)

    print(f"Base créée : {total} passages dans {config.DB_DIR}")
    return total


if __name__ == "__main__":
    build()
