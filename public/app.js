/* ═══════════════════════════════════════════════════════════════════════════
   Portfolio Chatbot — app.js
   ═══════════════════════════════════════════════════════════════════════════ */

// ── Markdown-Renderer ─────────────────────────────────────────────────────
const md = new showdown.Converter({
  tables:             true,
  strikethrough:      true,
  openLinksInNewWindow: true,
  simplifiedAutoLink: true,
});

// ── DOM-Referenzen ────────────────────────────────────────────────────────
const chatWindow  = document.getElementById("chatWindow");
const inputField  = document.getElementById("inputField");
const sendBtn     = document.getElementById("sendBtn");
const suggestions = document.getElementById("suggestions");

// ── State ─────────────────────────────────────────────────────────────────
let isLoading = false;

// ── Nachrichten anzeigen ──────────────────────────────────────────────────
function appendMessage(role, htmlContent) {
  const msgEl    = document.createElement("div");
  msgEl.className = `message ${role}`;

  const bubble   = document.createElement("div");
  bubble.className = "bubble";
  bubble.innerHTML = htmlContent;

  msgEl.appendChild(bubble);
  chatWindow.appendChild(msgEl);
  scrollToBottom();
  return bubble;
}

function scrollToBottom() {
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

// ── Typing-Indikator ──────────────────────────────────────────────────────
function showTypingIndicator() {
  const msgEl    = document.createElement("div");
  msgEl.className = "message assistant";
  msgEl.id       = "typingIndicator";

  const bubble   = document.createElement("div");
  bubble.className = "bubble typing-indicator";
  bubble.innerHTML = "<span></span><span></span><span></span>";

  msgEl.appendChild(bubble);
  chatWindow.appendChild(msgEl);
  scrollToBottom();
}

function removeTypingIndicator() {
  document.getElementById("typingIndicator")?.remove();
}

// ── Ladezustand ───────────────────────────────────────────────────────────
function setLoading(loading) {
  isLoading            = loading;
  sendBtn.disabled     = loading;
  inputField.disabled  = loading;
}

// ── Textarea auto-resize ──────────────────────────────────────────────────
inputField.addEventListener("input", () => {
  inputField.style.height = "auto";
  inputField.style.height = Math.min(inputField.scrollHeight, 130) + "px";
});

// ── Keyboard-Shortcuts ────────────────────────────────────────────────────
// Enter = Senden, Shift+Enter = Zeilenumbruch
inputField.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

sendBtn.addEventListener("click", sendMessage);

// ── Suggestion Chips ──────────────────────────────────────────────────────
suggestions.addEventListener("click", (e) => {
  const chip = e.target.closest(".chip");
  if (!chip || isLoading) return;

  inputField.value = chip.dataset.q;

  // Chips nach erster Nutzung verstecken (gibt Platz für den Chat)
  suggestions.style.display = "none";

  sendMessage();
});

// ── XSS-Schutz für User-Input ─────────────────────────────────────────────
function escapeHtml(str) {
  return str
    .replace(/&/g,  "&amp;")
    .replace(/</g,  "&lt;")
    .replace(/>/g,  "&gt;")
    .replace(/"/g,  "&quot;")
    .replace(/'/g,  "&#039;");
}

// ── API-Endpunkt ──────────────────────────────────────────────────────────
// Im lokalen Test auf http://localhost:8000/api/chat ändern.
const API_URL = "/api/chat";

// ── Hauptfunktion: Nachricht senden ───────────────────────────────────────
async function sendMessage() {
  const text = inputField.value.trim();
  if (!text || isLoading) return;

  // User-Nachricht anzeigen
  appendMessage("user", escapeHtml(text));

  // Eingabefeld leeren und zurücksetzen
  inputField.value       = "";
  inputField.style.height = "auto";

  setLoading(true);
  showTypingIndicator();

  try {
    const response = await fetch(API_URL, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ message: text }),
    });

    removeTypingIndicator();

    if (!response.ok) {
      // Server-Fehler: versuche JSON zu lesen, sonst Fallback
      let errMsg = `HTTP ${response.status}`;
      try {
        const err = await response.json();
        if (err.error) errMsg = err.error;
      } catch (_) { /* JSON-Parse-Fehler ignorieren */ }
      throw new Error(errMsg);
    }

    const data = await response.json();

    if (!data.reply) {
      throw new Error("Leere Antwort vom Server.");
    }

    // Antwort als Markdown rendern
    const html = md.makeHtml(data.reply);
    appendMessage("assistant", html);

  } catch (err) {
    removeTypingIndicator();
    appendMessage(
      "assistant",
      `<em>⚠️ Fehler: ${escapeHtml(err.message)} — bitte versuch es nochmal.</em>`
    );
    console.error("[ChatBot] Fehler:", err);
  } finally {
    setLoading(false);
    inputField.focus();
  }
}
