"""
================================================
  DIGITAL DETOX HUB — Python Flask Chatbot Backend
  app.py

  Proxies conversation to Google Gemini API.
  Keeps the API key safely on the server side.

  Run locally:
      python app.py

  Production deploy: Render / Railway / Heroku
      Set the GEMINI_API_KEY environment variable.
================================================
"""

import os
import json
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# ── Load .env file (for local development) ──────────────────────
load_dotenv()

# ── Create Flask app ─────────────────────────────────────────────
app = Flask(__name__)

# Allow all origins during development.
# In production, restrict to your Vercel domain:
#   CORS(app, origins=["https://digital-detox-by-leeza-2231.vercel.app"])
CORS(app)

# ── Configuration ────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyAoXamtfSAq5o_933thcKzz5TPpXynukdk")
GEMINI_MODEL   = "gemini-2.5-flash"
GEMINI_URL     = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
)

SYSTEM_PROMPT = (
    "You are a digital wellbeing assistant helping users reduce screen time, "
    "stay mindful, and build healthy tech habits. "
    "Be warm, concise, supportive, and practical. "
    "Keep responses focused on digital wellness topics. "
    "Use calm, encouraging language that matches a 'digital detox' mindset."
)

# Maximum number of conversation turns forwarded to Gemini
MAX_HISTORY_TURNS = 20


# ── Health-check route ────────────────────────────────────────────
@app.route("/", methods=["GET"])
def index():
    """Simple health-check endpoint."""
    return jsonify({"status": "ok", "message": "Digital Detox Chatbot API is running 🌿"})


# ── Main chat endpoint ────────────────────────────────────────────
@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Accepts a POST request with a JSON body:
        {
            "messages": [
                { "role": "user",  "parts": [{ "text": "..." }] },
                { "role": "model", "parts": [{ "text": "..." }] },
                ...
            ]
        }

    Returns:
        { "reply": "<assistant response text>" }
    Or on error:
        { "error": "<message>" }, HTTP 4xx/5xx
    """
    # ── Validate Content-Type ──────────────────────────────────────
    if not request.is_json:
        return jsonify({"error": "Request must be JSON."}), 400

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid JSON body."}), 400

    messages = data.get("messages", [])
    if not isinstance(messages, list) or len(messages) == 0:
        return jsonify({"error": "messages array is required and must not be empty."}), 400

    # ── Trim history to keep token cost low ───────────────────────
    recent_messages = messages[-MAX_HISTORY_TURNS:]

    # ── Build Gemini REST request body ────────────────────────────
    gemini_payload = {
        "system_instruction": {
            "parts": [{"text": SYSTEM_PROMPT}]
        },
        "contents": recent_messages,
        "generationConfig": {
            "temperature": 0.75,
            "topP": 0.9,
            "maxOutputTokens": 600,
        },
    }

    # ── Call Gemini API ───────────────────────────────────────────
    try:
        response = requests.post(
            GEMINI_URL,
            headers={"Content-Type": "application/json"},
            data=json.dumps(gemini_payload),
            timeout=30,          # seconds before giving up
        )
    except requests.exceptions.Timeout:
        return jsonify({"error": "Request to Gemini timed out. Please try again."}), 504
    except requests.exceptions.RequestException as exc:
        app.logger.error("Network error calling Gemini: %s", exc)
        return jsonify({"error": "Could not reach Gemini API. Check server connectivity."}), 502

    # ── Handle non-200 from Gemini ────────────────────────────────
    if not response.ok:
        try:
            err_body = response.json()
            err_msg  = err_body.get("error", {}).get("message", "Unknown Gemini error.")
        except Exception:
            err_msg = f"Gemini returned HTTP {response.status_code}."
        app.logger.error("Gemini API error: %s", err_msg)
        return jsonify({"error": err_msg}), response.status_code

    # ── Parse Gemini response ─────────────────────────────────────
    try:
        result      = response.json()
        candidates  = result.get("candidates", [])

        if not candidates:
            finish_reason = "UNKNOWN"
            return jsonify({
                "error": f"Gemini returned no candidates (finishReason: {finish_reason})."
            }), 500

        candidate = candidates[0]
        finish_reason = candidate.get("finishReason", "")

        # Safety filter triggered
        if finish_reason == "SAFETY":
            return jsonify({
                "error": "Response blocked by Google safety filters. Please rephrase."
            }), 422

        parts = candidate.get("content", {}).get("parts", [])
        if not parts or not parts[0].get("text"):
            return jsonify({"error": "Received an empty response from the AI."}), 500

        reply_text = parts[0]["text"].strip()
        return jsonify({"reply": reply_text})

    except (KeyError, IndexError, ValueError) as exc:
        app.logger.error("Error parsing Gemini response: %s", exc)
        return jsonify({"error": "Unexpected response format from Gemini."}), 500


# ── Entry point ───────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug_mode = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    print(f"\n🌿 Digital Detox Chatbot API running on http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
