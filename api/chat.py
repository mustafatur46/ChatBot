"""
api/chat.py — Vercel Python Serverless Function

Vercel erwartet eine Flask-WSGI-App in der Variable `app`.
Route: POST /api/chat  →  {"message": "..."}  →  {"reply": "..."}

RAG-Pipeline:
  1. User-Query → Gemini text-embedding-004 (RETRIEVAL_QUERY)
  2. Cosine Similarity vs. vorberechnete Embeddings (numpy, module-level gecacht)
  3. Top-3 Chunks → System Prompt + Kontext → Gemini 2.0 Flash
  4. Antwort zurückgeben
"""

import json
import os
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from google import genai

# .env lokal laden (auf Vercel passiert das automatisch über das Dashboard)
load_dotenv()

# ── Flask App ─────────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)  # Erlaubt Requests vom statischen Frontend

# ── Gemini Client (module-level → bleibt bei Warm Invocations erhalten) ───────
_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# ── Embedding-Index laden (einmalig beim Cold Start) ──────────────────────────
_DATA_PATH = Path(__file__).parent.parent / "data" / "embeddings.json"


def _load_index():
    with open(_DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    chunks = data["chunks"]

    # Matrix vorberechnen und normalisieren:
    # Cosine Similarity = Dot Product zweier normalisierter Vektoren → schnell & einfach
    matrix = np.array(data["embeddings"], dtype=np.float32)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    matrix = matrix / np.where(norms == 0, 1.0, norms)

    print(f"[chat.py] Index geladen: {len(chunks)} Chunks, Dim {matrix.shape[1]}")
    return chunks, matrix


_CHUNKS, _EMBEDDING_MATRIX = _load_index()

# ── Konfiguration ─────────────────────────────────────────────────────────────
EMBED_MODEL    = "gemini-embedding-001"
GENERATE_MODEL = "gemini-2.0-flash"
TOP_K          = 3
MAX_MSG_LEN    = 1000

SYSTEM_PROMPT = """Du bist Mustafas persönlicher Portfolio-Assistent auf seiner Portfolio-Website.
Deine EINZIGE Aufgabe ist es, Fragen über Mustafa Turhal zu beantworten — seinen Werdegang,
seine Ausbildung, Projekte, Skills und Interessen.

Regeln:
1. Antworte in 2–4 Sätzen, recruiter-freundlich. Sprich über Mustafa in der dritten Person
   ("Er hat...", "Seine Erfahrung umfasst...", "In seinem Projekt hat er...").
2. Erfinde KEINE Skills oder Erfahrungen, die nicht im Kontext stehen.
3. Wenn der Kontext nicht ausreicht, sag das ehrlich und empfehle direkten Kontakt per E-Mail.
4. Antworte immer in der Sprache der Frage (Deutsch → Deutsch, Englisch → Englisch, etc.).
5. GUARDRAIL: Wenn die Frage NICHTS mit Mustafa zu tun hat (z.B. allgemeines Wissen,
   Politik, Coding-Hilfe, Rezepte, Witze etc.), antworte mit einer freundlichen, leicht
   spielerischen Ablehnung IN DER SPRACHE DER FRAGE. Variiere die Formulierung, sei nie
   roboterhaft. Beispiele:
   - "Hey, damit hab ich nichts zu tun 😄 Ich bin nur hier, um Fragen über Mustafa
     zu beantworten — frag mich was über seinen Werdegang!"
   - "Haha, gute Frage — aber ich bin kein Google 😅 Stell mir lieber was über
     Mustafas Projekte oder Skills!"
   - "Das liegt etwas außerhalb meines Aufgabenbereichs 😄 Ich kenne mich nur mit
     Mustafa aus. Was möchtest du über ihn wissen?"
   - "That's a bit outside my lane 😅 I'm only here to talk about Mustafa —
     ask me something about his experience or projects!"
   - "Ha, good question — but I'm no Google! 😄 I only know things about Mustafa.
     Anything you'd like to know about him?"
"""


# ── Hilfsfunktionen ───────────────────────────────────────────────────────────
def _embed_query(text: str) -> np.ndarray:
    """Bettet die User-Query ein. task_type=RETRIEVAL_QUERY für bessere Retrieval-Qualität."""
    result = _client.models.embed_content(
        model=EMBED_MODEL,
        contents=text,
        config={"task_type": "RETRIEVAL_QUERY"},
    )
    vec = np.array(result.embeddings[0].values, dtype=np.float32)
    norm = np.linalg.norm(vec)
    return vec / (norm if norm > 0 else 1.0)


def _retrieve(query_vec: np.ndarray, k: int = TOP_K) -> list[str]:
    """Findet die k ähnlichsten Chunks via Cosine Similarity (= Dot Product bei Unit-Vektoren)."""
    scores = _EMBEDDING_MATRIX @ query_vec
    top_indices = np.argsort(scores)[::-1][:k]
    return [_CHUNKS[i] for i in top_indices]


def _generate(user_message: str, context_chunks: list[str]) -> str:
    """Generiert eine Antwort via Gemini 2.0 Flash mit RAG-Kontext."""
    context_block = "\n\n---\n\n".join(context_chunks)
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"=== KONTEXT AUS MUSTAFAS PROFIL ===\n"
        f"{context_block}\n"
        f"=== ENDE KONTEXT ===\n\n"
        f"Frage: {user_message}"
    )
    response = _client.models.generate_content(
        model=GENERATE_MODEL,
        contents=prompt,
    )
    return response.text


# ── Route ─────────────────────────────────────────────────────────────────────
@app.route("/api/chat", methods=["POST", "OPTIONS"])
def chat():
    # OPTIONS wird von Flask-CORS automatisch behandelt
    if request.method == "OPTIONS":
        return jsonify({}), 200

    # Request validieren
    body = request.get_json(force=True, silent=True)
    if not body or "message" not in body:
        return jsonify({"error": "Fehlendes Feld 'message'"}), 400

    user_message = str(body["message"]).strip()
    if not user_message:
        return jsonify({"error": "Leere Nachricht"}), 400
    if len(user_message) > MAX_MSG_LEN:
        return jsonify({"error": f"Nachricht zu lang (max {MAX_MSG_LEN} Zeichen)"}), 400

    try:
        # RAG-Pipeline
        query_vec      = _embed_query(user_message)
        context_chunks = _retrieve(query_vec)
        reply          = _generate(user_message, context_chunks)
        return jsonify({"reply": reply})

    except Exception as e:
        print(f"[chat.py] ERROR: {e}")
        return jsonify({"error": "Etwas ist schiefgelaufen. Bitte versuche es erneut."}), 500


# ── Lokaler Entwicklungsserver ────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, port=8000)
