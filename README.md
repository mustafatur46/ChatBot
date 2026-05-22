# 🤖 Portfolio Chatbot

Ein RAG-basierter Chatbot, der Recruitern und Interviewern Fragen zu meinem Werdegang,
Skills und Projekten beantwortet. Deployed auf Vercel.

**Live:** [https://DEIN-PROJEKT.vercel.app](https://DEIN-PROJEKT.vercel.app)

---

## Wie es funktioniert

```
User-Frage
  → Gemini text-embedding-004 (RETRIEVAL_QUERY)
  → Cosine Similarity vs. data/embeddings.json (Numpy)
  → Top-3 relevante Chunks
  → Gemini 2.0 Flash (RAG-Prompt mit Kontext)
  → Antwort
```

**Offline (einmalig lokal):** `scripts/build_index.py` liest `data/profile.md`,
teilt den Text in Chunks auf und generiert Embeddings via Gemini API → speichert
alles in `data/embeddings.json`.

**Online (pro Request):** `api/chat.py` (Vercel Serverless Function) lädt die
Embeddings beim Cold Start, bettet die User-Frage ein, führt eine Cosine-Similarity-
Suche durch und ruft Gemini 2.0 Flash zur Antwortgenerierung auf.

---

## Tech-Stack


| Komponente   | Technologie                         |
| ------------ | ----------------------------------- |
| LLM          | Gemini 2.0 Flash (Google AI Studio) |
| Embeddings   | Gemini text-embedding-004           |
| Vektorsearch | NumPy Cosine Similarity             |
| Backend      | Python + Flask (Vercel Serverless)  |
| Frontend     | Vanilla HTML/CSS/JS + Showdown.js   |
| Hosting      | Vercel (kostenlos)                  |
| CI/CD        | GitHub → Vercel Auto-Deploy         |


---

## Lokale Entwicklung

```powershell
# 1. Abhängigkeiten installieren
pip install -r requirements.txt

# 2. Gemini API Key setzen (kostenlos: https://aistudio.google.com/app/apikey)
$env:GEMINI_API_KEY = "dein_key"

# 3. data/profile.md mit deinen echten Daten befüllen

# 4. Embedding-Index bauen
python scripts/build_index.py

# 5. API lokal starten
python api/chat.py
# → http://localhost:8000

# 6. Frontend öffnen (in einem anderen Terminal)
python -m http.server 3000 -d public
# → http://localhost:3000
# Hinweis: API_URL in app.js auf "http://localhost:8000/api/chat" ändern für lokalen Test
```

---

## Deployment auf Vercel

```bash
# 1. GitHub Repo erstellen und Code pushen (inkl. data/embeddings.json!)
git init
git add .
git commit -m "Initial portfolio chatbot"
git remote add origin https://github.com/DEIN_USERNAME/portfolio-chatbot.git
git push -u origin main

# 2. Vercel: https://vercel.com → "Add New Project" → Repo importieren
#    - Framework Preset: "Other"
#    - Environment Variable: GEMINI_API_KEY = dein_key
#    → Deploy klicken
```

---

## Profil aktualisieren

```powershell
# data/profile.md editieren, dann:
python scripts/build_index.py
git add data/profile.md data/embeddings.json
git commit -m "Update profile"
git push
# → Vercel deployed automatisch in ~30 Sekunden
```

---

## Kosten


| Ressource          | Free Tier                         |
| ------------------ | --------------------------------- |
| Gemini 2.0 Flash   | 1.000.000 Tokens/Tag              |
| text-embedding-004 | 1.500 Requests/Tag                |
| Vercel Hosting     | Kostenlos (100GB Bandwidth/Monat) |


Für ein Portfolio-Projekt: **faktisch kostenlos** 🎉