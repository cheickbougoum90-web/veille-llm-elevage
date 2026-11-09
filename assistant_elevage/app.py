"""Interface Gradio : question -> réponse sourcée -> bouton de lecture audio.

Lancer :  python app.py      puis ouvrir http://127.0.0.1:7860
Tout reste sur le PC (127.0.0.1 uniquement, aucune donnée envoyée sur internet).
"""
from __future__ import annotations

import gradio as gr

import config
import rag
import tts

BANNER = (
    "### 🐄 Assistant d'élevage (bovins, moutons, chèvres)\n"
    "⚠️ **Cet assistant est une intelligence artificielle. Il ne remplace pas un vétérinaire.** "
    "Ses réponses viennent uniquement des documents chargés ; en cas de doute, consultez un vétérinaire.\n\n"
    "🔒 Fonctionne sans internet : vos questions restent sur cet ordinateur."
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
