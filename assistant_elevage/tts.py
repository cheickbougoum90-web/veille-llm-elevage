"""Synthèse vocale française hors ligne pour l'assistant d'élevage (rôle C).

Moteur : Piper (CPU, aucune VRAM). Voix : fr_FR-siwis-medium (licence CC BY 4.0 selon sa fiche :
à vérifier dans MODEL_CARD avant le livrable, attribution à citer).

Installation :  pip install piper-tts
Modèle (une seule fois, avec internet) : placer dans le dossier voices/ les deux fichiers
  fr_FR-siwis-medium.onnx  et  fr_FR-siwis-medium.onnx.json
  (dépôt Hugging Face rhasspy/piper-voices, dossier fr/fr_FR/siwis/medium)
  ou :  python -m piper.download_voices fr_FR-siwis-medium --data-dir voices

Interface attendue par app.py :  speakable(text) puis synthesize(text) -> chemin .wav
"""
import os
import re
import shutil
import sys
import tempfile
import time
import wave
from pathlib import Path

VOICE_DIR = Path(os.environ.get("TTS_VOICE_DIR", Path(__file__).parent / "voices"))
VOICE_NAME = os.environ.get("TTS_VOICE", "fr_FR-siwis-medium")

_voice = None

# Prononciation : le moteur épelle mal les sigles ; on les remplace par une forme lisible.
# À compléter après l'écoute des 20 phrases de test.
PRONONCIATION = {
    r"\bPPCB\b": "péripneumonie contagieuse bovine",
    r"\bPPR\b": "peste des petits ruminants",
    r"\bDNC\b": "dermatose nodulaire contagieuse",
    r"\bFAO\b": "F A O",
    r"\bOMSA\b": "O M S A",
}


def speakable(text: str) -> str:
    """Nettoie le texte avant lecture (même rôle que celui annoncé dans app.py)."""
    t = re.sub(r"\[S\d+\]", "", text)            # citations [S1]
    t = re.sub(r"[*_`#>]+", "", t)               # markdown
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"\s+([,.;:!?])", r"\1", t)         # espace laissée par une citation retirée
    for motif, remplacement in PRONONCIATION.items():
        t = re.sub(motif, remplacement, t)
    return t


def _load():
    global _voice
    if _voice is None:
        from piper import PiperVoice
        modele = VOICE_DIR / f"{VOICE_NAME}.onnx"
        if not modele.exists():
            raise FileNotFoundError(f"Voix introuvable : {modele}")
        _voice = PiperVoice.load(str(modele))
    return _voice


def synthesize(text: str) -> str:
    """Retourne le chemin d'un fichier .wav contenant le texte lu à voix haute."""
    text = speakable(text)
    if not text:
        raise ValueError("Texte vide")
    voice = _load()
    out = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    with wave.open(out, "wb") as wav:
        try:
            voice.synthesize_wav(text, wav)      # piper-tts récent
        except AttributeError:
            voice.synthesize(text, wav)          # anciennes versions
    return out


PHRASES_TEST = [
    "La fièvre aphteuse est une maladie très contagieuse des bovins.",
    "La brucellose peut se transmettre à l'homme par le lait cru.",
    "La peste des petits ruminants touche les moutons et les chèvres.",
    "La péripneumonie contagieuse bovine provoque de la toux et de la fièvre.",
    "La dermatose nodulaire contagieuse se reconnaît aux nodules sur la peau.",
    "Isolez les animaux malades et contactez un vétérinaire.",
    "Je ne sais pas : les documents ne contiennent pas cette information.",
    "Cet assistant ne remplace pas un vétérinaire.",
    "Vaccinez vos animaux selon les conseils du service vétérinaire.",
    "Les ampoules dans la bouche sont un signe de fièvre aphteuse.",
    "Un avortement peut avoir plusieurs causes.",
    "Ne consommez pas la viande d'un animal mort de maladie.",
    "La vache laitière a besoin d'eau, d'énergie et de minéraux.",
    "Limitez les déplacements du troupeau pendant l'épidémie.",
    "Les ovins et les caprins sont des petits ruminants.",
    "Le vétérinaire confirmera le diagnostic par un examen de laboratoire.",
    "Source : Organisation mondiale de la santé animale.",
    "La quarantaine dure plusieurs semaines avant l'introduction d'un nouvel animal.",
    "Le lait doit être bouilli ou pasteurisé avant d'être consommé.",
    "En cas de doute, appelez le service vétérinaire le plus proche.",
]


if __name__ == "__main__" and "--test" in sys.argv:
    dossier = Path("audio_test"); dossier.mkdir(exist_ok=True)
    for i, p in enumerate(PHRASES_TEST, 1):
        t0 = time.time()
        chemin = synthesize(p)
        shutil.move(chemin, str(dossier / f"phrase_{i:02d}.wav"))   # move : le dossier temporaire est sur un autre disque
        print(f"{i:02d} OK ({time.time() - t0:.1f} s) {p}")
    print("Écouter les fichiers dans audio_test/ et noter chaque phrase (clarté, prononciation).")
