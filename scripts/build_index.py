"""
build_index.py — Läuft NUR lokal, nie auf Vercel.

Liest data/profile.md, erstellt Text-Chunks, generiert Gemini-Embeddings
und speichert alles in data/embeddings.json.

Ausführen:
    $env:GEMINI_API_KEY = "dein_key"   # PowerShell
    python scripts/build_index.py

Voraussetzungen:
    pip install google-genai
"""

import json
import os
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# Windows Terminal auf UTF-8 setzen (für Emoji-Output)
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
from google import genai

# .env laden (falls vorhanden)
load_dotenv()

# ── Konfiguration ─────────────────────────────────────────────────────────────
ROOT         = Path(__file__).parent.parent
PROFILE_PATH = ROOT / "data" / "profile.md"
OUTPUT_PATH  = ROOT / "data" / "embeddings.json"

EMBED_MODEL      = "gemini-embedding-001"
MAX_WORDS        = 400   # Maximale Wörter pro Chunk
OVERLAP_LINES    = 2     # Zeilen Überlappung bei langen Sektionen
RATE_LIMIT_DELAY = 0.15  # Sekunden zwischen API-Calls (Free Tier: 1500 req/Tag)

# ── Gemini Client ─────────────────────────────────────────────────────────────
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise EnvironmentError(
        "GEMINI_API_KEY nicht gesetzt!\n"
        "Entweder in .env eintragen: GEMINI_API_KEY=dein_key\n"
        "Oder PowerShell: $env:GEMINI_API_KEY = 'dein_key'"
    )

client = genai.Client(api_key=api_key)


# ── Chunking ──────────────────────────────────────────────────────────────────
def chunk_markdown(text: str) -> list[str]:
    """
    Teilt Markdown bei ## und ### Überschriften auf.
    Lange Sektionen werden mit Sliding Window weiter aufgeteilt.
    """
    # Split bei Level-2 und Level-3 Überschriften (Überschrift bleibt im Chunk)
    sections = re.split(r"(?=^#{2,3} )", text, flags=re.MULTILINE)
    chunks = []

    for section in sections:
        section = section.strip()
        if not section:
            continue

        words = section.split()

        if len(words) <= MAX_WORDS:
            chunks.append(section)
        else:
            # Sliding Window für lange Sektionen
            lines = section.splitlines()
            window: list[str] = []
            word_count = 0

            for line in lines:
                line_words = len(line.split())
                if word_count + line_words > MAX_WORDS and window:
                    chunks.append("\n".join(window))
                    # Letzten OVERLAP_LINES Zeilen behalten für Kontext-Kontinuität
                    window = window[-OVERLAP_LINES:]
                    word_count = sum(len(l.split()) for l in window)

                window.append(line)
                word_count += line_words

            if window:
                chunks.append("\n".join(window))

    return chunks


# ── Embedding ─────────────────────────────────────────────────────────────────
def embed_chunks(chunks: list[str]) -> list[list[float]]:
    """
    Generiert Gemini text-embedding-004 Embeddings für jeden Chunk.
    task_type=RETRIEVAL_DOCUMENT optimiert für spätere Query-Suche.
    """
    embeddings = []
    total = len(chunks)

    for i, chunk in enumerate(chunks):
        preview = chunk[:60].replace("\n", " ").strip()
        print(f"  [{i+1}/{total}] Embedding: {preview!r}...")

        result = client.models.embed_content(
            model=EMBED_MODEL,
            contents=chunk,
            config={"task_type": "RETRIEVAL_DOCUMENT"},
        )
        embeddings.append(result.embeddings[0].values)

        # Rate Limiting für Free Tier
        if i < total - 1:
            time.sleep(RATE_LIMIT_DELAY)

    return embeddings


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print(f"📄 Lese {PROFILE_PATH}...")
    if not PROFILE_PATH.exists():
        raise FileNotFoundError(f"{PROFILE_PATH} nicht gefunden. Bitte zuerst data/profile.md befüllen.")

    text = PROFILE_PATH.read_text(encoding="utf-8")
    if len(text.strip()) < 100:
        raise ValueError("data/profile.md scheint leer oder zu kurz zu sein. Bitte befüllen!")

    print("✂️  Chunking...")
    chunks = chunk_markdown(text)
    print(f"   → {len(chunks)} Chunks erstellt\n")

    for i, c in enumerate(chunks):
        word_count = len(c.split())
        print(f"   Chunk {i+1:02d} ({word_count} Wörter): {c[:80].replace(chr(10), ' ')!r}")
    print()

    print("🤖 Generiere Embeddings via Gemini API...")
    embeddings = embed_chunks(chunks)

    # Validierung
    assert len(chunks) == len(embeddings), "Chunks und Embeddings stimmen nicht überein!"
    embedding_dim = len(embeddings[0])
    print(f"\n   ✅ {len(chunks)} Embeddings, Dimension: {embedding_dim}")

    # Speichern
    output = {
        "chunks": chunks,
        "embeddings": embeddings,
        "meta": {
            "model": EMBED_MODEL,
            "chunk_count": len(chunks),
            "embedding_dim": embedding_dim,
        },
    }
    OUTPUT_PATH.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"\n💾 Gespeichert: {OUTPUT_PATH}")
    print(f"   Dateigröße: {size_kb:.1f} KB")
    print("\n✅ Fertig! data/embeddings.json committen nicht vergessen.")


if __name__ == "__main__":
    main()
