"""Point d'accroche pour la voix (étudiant C).

Contrat : synthesize(text) reçoit du texte en français déjà nettoyé et renvoie le chemin
d'un fichier audio (.wav) ou None. L'interface (app.py) appelle uniquement cette fonction.
Remplacer le corps de `synthesize` par le synthétiseur choisi (hors ligne, sur processeur).
"""
from __future__ import annotations

import re


def speakable(answer_text: str) -> str:
    """Prépare le texte pour la lecture : retire [S1], le markdown et les listes de sources."""
    t = re.sub(r"\[S\d+\]", "", answer_text)
    t = re.sub(r"[*_`#>]+", "", t)
    t = re.sub(r"\s+([,.;:!?])", r"\1", t)
    return re.sub(r"\s+", " ", t).strip()


def synthesize(text: str) -> str | None:
    """À IMPLÉMENTER par C. Exemple d'esprit : appeler le synthétiseur, écrire un .wav, renvoyer le chemin."""
    raise NotImplementedError("Synthèse vocale pas encore branchée (voir tts.py).")
