# Musti's Chatbot 🤖

**Live:** [chat-bot-mustafa.vercel.app](https://chat-bot-mustafa.vercel.app)

Ein persönlicher Portfolio-Chatbot, den ich gebaut habe, damit Recruiter und Interessierte mich und meinen Werdegang besser kennenlernen können — ohne dass ich bei jedem Gespräch von vorne anfangen muss. Der Chatbot beantwortet Fragen zu meinen Projekten, Skills und meiner Erfahrung.

Technisch gesehen ist es ein RAG-System (Retrieval-Augmented Generation): mein Profil wird in Chunks aufgeteilt, als Embeddings gespeichert, und bei jeder Frage werden die relevantesten Abschnitte rausgezogen und an Gemini weitergegeben. Kein Finetuning, kein Datenbankserver — einfach eine JSON-Datei und etwas Numpy.

---

## Wie's funktioniert

```
Deine Frage
  → wird zu einem Vektor (Gemini Embedding)
  → Cosine Similarity gegen alle gespeicherten Profil-Chunks
  → Top 3 relevanteste Abschnitte
  → Gemini 2.5 Flash bekommt: System Prompt + Kontext + deine Frage
  → Antwort
```

Das Embeddings-File (`data/embeddings.json`) wird lokal gebaut und ins Repo committed. Vercel liest es beim Start — kein Datenbankserver, keine laufenden Kosten, keine Komplexität.

---

## Tech-Stack

| Komponente   | Technologie                          |
|--------------|--------------------------------------|
| LLM          | Gemini 2.5 Flash (Google AI Studio)  |
| Embeddings   | Gemini Embedding 001                 |
| Vektorsearch | NumPy Cosine Similarity              |
| Backend      | Python + Flask (Vercel Serverless)   |
| Frontend     | Vanilla HTML/CSS/JS + Showdown.js    |
| Hosting      | Vercel Free Tier                     |
| CI/CD        | GitHub → Vercel Auto-Deploy          |

---

## Lokal laufen lassen

```powershell
# Repo klonen und venv erstellen
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# .env anlegen (siehe .env.example)
# GEMINI_API_KEY=dein_key_von_aistudio.google.com

# Embedding-Index bauen (einmalig, nach Änderungen an profile.md)
python scripts/build_index.py

# API starten
python api/chat.py
# → http://localhost:8000
```

---

## Profil aktualisieren

```powershell
# profile.md editieren, dann:
python scripts/build_index.py
git add data/profile.md data/embeddings.json
git commit -m "Update profile"
git push
# Vercel deployed automatisch
```

---

## Deployment

Vercel → New Project → GitHub Repo importieren → Framework: **Other** → Environment Variable `GEMINI_API_KEY` setzen → Deploy.

Das war's. Kein Server, kein Setup, kein Aufwand.

---

Gebaut von [Mustafa Turhal](https://github.com/mustafatur46) — Feedback und Fragen gerne per Mail: mustafa.turhal08@gmail.com
