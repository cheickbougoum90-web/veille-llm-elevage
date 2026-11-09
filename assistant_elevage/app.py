"""Interface Gradio : question -> réponse sourcée -> bouton de lecture audio.

Lancer :  python app.py      puis ouvrir http://127.0.0.1:7860
Interface accessible seulement depuis ce PC (127.0.0.1) ; les questions ne sont pas enregistrées.
"""
from __future__ import annotations

import os

# Aucune statistique envoyée par Gradio (à définir avant l'import) ; HF_HUB_OFFLINE=1 est à définir
# dans le terminal après le premier téléchargement du modèle d'embeddings (voir README).
os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")

import gradio as gr

import config
import rag
import tts

BANNER = (
    "### 🐄 Assistant d'élevage (bovins, moutons, chèvres)\n"
    "⚠️ **Vous parlez à une intelligence artificielle, pas à un vétérinaire.** "
    "Elle peut se tromper et ne donne ni diagnostic, ni traitement, ni dose. "
    "Ses réponses viennent uniquement des documents chargés, dont certains sont anciens. "
    "**En cas d'animal malade ou de doute, consultez un vétérinaire ou un agent de santé animale.**\n\n"
    "🔒 Les questions sont traitées sur cet ordinateur (modèle local) et ne sont pas enregistrées par l'application."
)

EXAMPLES = [
    "Quels animaux peuvent être touchés par la brucellose ?",
    "Comment reconnaître la peste des petits ruminants ?",
    "Comment limiter le risque de brucellose pour la famille ?",
]


def answer(question: str):
    """Générateur : met à jour la réponse au fur et à mesure (streaming)."""
    try:
        for a in rag.ask_iter(question):
            yield a.text, a.sources_markdown(), a.text if a.done and not a.refused else "", None
    except Exception as e:  # Ollama éteint, base absente, etc.
        yield f"⚠️ Erreur : {e}", "", "", None


def listen(last_answer: str):
    if not last_answer:
        gr.Info("Posez d'abord une question.")
        return None
    try:
        return tts.synthesize(tts.speakable(last_answer))
    except NotImplementedError:
        gr.Warning("La voix n'est pas encore branchée (tts.py).")
    except Exception as e:
        gr.Warning(f"Erreur audio : {e}")
    return None


with gr.Blocks(title="Assistant d'élevage") as demo:
    gr.Markdown(BANNER)
    q = gr.Textbox(label="Votre question (en français)", lines=2,
                   placeholder="Ex. : Quels sont les signes de la brucellose chez la vache ?")
    with gr.Row():
        send = gr.Button("Demander", variant="primary")
        speak = gr.Button("🔊 Écouter la réponse")
    out = gr.Markdown(label="Réponse")
    with gr.Accordion("Sources", open=True):
        src = gr.Markdown()
    audio = gr.Audio(label="Lecture", type="filepath", autoplay=True)
    last = gr.State("")
    gr.Examples(EXAMPLES, inputs=q)
    gr.Markdown(f"<small>Modèle : `{config.OLLAMA_MODEL}` · {config.DISCLAIMER}</small>")

    for trigger in (send.click, q.submit):
        trigger(answer, inputs=q, outputs=[out, src, last, audio])
    speak.click(listen, inputs=last, outputs=audio)

if __name__ == "__main__":
    demo.queue().launch(server_name="127.0.0.1", server_port=7860)
