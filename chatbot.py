"""
================================================
  DIGITAL DETOX HUB — Python CLI Chatbot
  chatbot.py

  Converted from chatbot.js
  Uses Google Gemini API (free tier)
  Runs entirely in the terminal — no browser needed

  Run:
      python chatbot.py
================================================
"""

import os
import json
import sys
import requests
from datetime import datetime
from dotenv import load_dotenv

# ── Load .env for local development ─────────────────────────────
load_dotenv()

# ============================================================
# CONFIGURATION  (mirrors CONFIG in chatbot.js)
# ============================================================
GEMINI_API_KEY   = os.getenv("GEMINI_API_KEY", "AIzaSyAoXamtfSAq5o_933thcKzz5TPpXynukdk")
GEMINI_MODEL     = "gemini-2.5-flash"
GEMINI_URL       = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
)
MAX_HISTORY_TURNS = 20    # max conversation turns sent to API

# System persona — identical to chatbot.js / app.py
SYSTEM_PROMPT = (
    "You are a digital wellbeing assistant helping users reduce screen time, "
    "stay mindful, and build healthy tech habits. "
    "Be warm, concise, supportive, and practical. "
    "Keep responses focused on digital wellness topics. "
    "Use calm, encouraging language that matches a 'digital detox' mindset."
    "Also give users to product suggestion from digital detox hub store if they ask for product recommendation."
)

# ============================================================
# HELPERS  (mirrors helper functions in chatbot.js)
# ============================================================

def get_timestamp() -> str:
    """Return current local time as HH:MM AM/PM — mirrors getTimestamp()."""
    now = datetime.now()
    return now.strftime("%I:%M %p").lstrip("0")


def print_separator(char: str = "─", width: int = 60) -> None:
    print(char * width)


def print_bot(text: str) -> None:
    """Print an assistant message — mirrors appendMessage('bot', text)."""
    print(f"\n🌿 Assistant  [{get_timestamp()}]")
    print_separator()
    print(text)
    print()


def print_user_echo(text: str) -> None:
    """Echo the user message with timestamp — mirrors appendMessage('user', text)."""
    print(f"\n👤 You  [{get_timestamp()}]")
    print_separator()
    print(text)


def print_error(message: str) -> None:
    """Print an error bubble — mirrors appendMessage('error', message)."""
    print(f"\n⚠️  Error  [{get_timestamp()}]")
    print_separator()
    print(message)
    print()


def show_typing() -> None:
    """Typing indicator — mirrors showTyping()."""
    print("\n  🌿 Assistant is thinking...", end="", flush=True)


def hide_typing() -> None:
    """Clear typing indicator — mirrors hideTyping()."""
    # Move to new line after the indicator
    print("\r" + " " * 40 + "\r", end="", flush=True)


# ============================================================
# API — CALL GEMINI  (mirrors callGemini() in chatbot.js)
# ============================================================

def call_gemini(conversation_history: list) -> str:
    """
    Send the conversation history to Gemini and return the reply text.
    Mirrors the callGemini() async function in chatbot.js.

    Args:
        conversation_history: List of {"role": ..., "parts": [...]} dicts.

    Returns:
        str: The model's reply text.

    Raises:
        RuntimeError: On API or response-parsing errors.
    """
    # Trim to max turns — mirrors conversationHistory.slice(-CONFIG.maxHistoryTurns)
    recent_history = conversation_history[-MAX_HISTORY_TURNS:]

    request_body = {
        "system_instruction": {
            "parts": [{"text": SYSTEM_PROMPT}]
        },
        "contents": recent_history,
        "generationConfig": {
            "temperature": 0.75,
            "topP": 0.9,
            "maxOutputTokens": 600,
        },
    }

    try:
        response = requests.post(
            GEMINI_URL,
            headers={"Content-Type": "application/json"},
            data=json.dumps(request_body),
            timeout=30,
        )
    except requests.exceptions.Timeout:
        raise RuntimeError("Request to Gemini timed out. Please try again.")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Network error: {e}")

    # Handle non-200 HTTP — mirrors the !response.ok block in chatbot.js
    if not response.ok:
        try:
            err_msg = response.json().get("error", {}).get("message", "")
        except Exception:
            err_msg = ""
        raise RuntimeError(err_msg or f"API error {response.status_code}")

    # Parse response — mirrors the data.candidates validation block
    try:
        data       = response.json()
        candidates = data.get("candidates", [])

        if not candidates:
            raise RuntimeError("Received an empty response from the AI.")

        candidate     = candidates[0]
        finish_reason = candidate.get("finishReason", "")

        # Safety filter — mirrors the finishReason === "SAFETY" check
        if finish_reason == "SAFETY":
            raise RuntimeError(
                "Response blocked by Google safety filters. Please rephrase your question."
            )

        parts = candidate.get("content", {}).get("parts", [])
        if not parts or not parts[0].get("text"):
            raise RuntimeError("Received an empty response from the AI.")

        return parts[0]["text"].strip()

    except (KeyError, IndexError, ValueError) as e:
        raise RuntimeError(f"Unexpected response format from Gemini: {e}")


# ============================================================
# CORE — SEND MESSAGE  (mirrors sendMessage() in chatbot.js)
# ============================================================

def send_message(user_text: str, conversation_history: list) -> list:
    """
    Process one user turn: render it, call Gemini, render reply.
    Mirrors the sendMessage() function in chatbot.js.

    Args:
        user_text:            The user's input string.
        conversation_history: The running dialogue list (mutated in place).

    Returns:
        The updated conversation_history.
    """
    if not user_text.strip():
        return conversation_history

    # Echo user message — mirrors appendMessage('user', userText)
    print_user_echo(user_text)

    # Add user turn to history — mirrors conversationHistory.push({ role: 'user', ... })
    conversation_history.append({
        "role": "user",
        "parts": [{"text": user_text}]
    })

    # Show typing indicator — mirrors showTyping()
    show_typing()

    try:
        reply_text = call_gemini(conversation_history)

        # Add model turn to history — mirrors conversationHistory.push({ role: 'model', ... })
        conversation_history.append({
            "role": "model",
            "parts": [{"text": reply_text}]
        })

        # Render bot reply — mirrors appendMessage('bot', replyText)
        hide_typing()
        print_bot(reply_text)

    except RuntimeError as err:
        hide_typing()

        # User-friendly error handling — mirrors the catch block in chatbot.js
        print_error(str(err))

        # Remove the last user turn so the user can retry
        # mirrors conversationHistory.pop()
        conversation_history.pop()

    return conversation_history


# ============================================================
# INIT — WELCOME MESSAGE  (mirrors showWelcome() in chatbot.js)
# ============================================================

def show_welcome() -> None:
    """Display the welcome message — mirrors showWelcome() in chatbot.js."""
    print()
    print_separator("═")
    print("  🌿 Digital Detox Hub — Wellness Assistant")
    print("     Powered by Google Gemini  |  Python CLI")
    print_separator("═")
    print_bot(
        "Hi there! 👋 I'm your Digital Wellness Assistant. I can help you:\n\n"
        "• Reduce screen time & build better habits\n"
        "• Find mindfulness & focus strategies\n"
        "• Suggest healthy tech boundaries\n\n"
        "What's on your mind today?\n\n"
        "(Type  'quit'  or  'exit'  to end the session.)"
    )


# ============================================================
# MAIN LOOP
# ============================================================

def main() -> None:
    """
    Main REPL loop — the CLI equivalent of the chat window's event listeners
    (keydown Enter → sendMessage) in chatbot.js.
    """
    show_welcome()

    # conversation_history mirrors the conversationHistory array in chatbot.js
    conversation_history: list = []

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            # Ctrl+C or Ctrl+D — mirrors the Escape key handler in chatbot.js
            print("\n\n🌿 Take care and stay mindful. Goodbye!\n")
            sys.exit(0)

        # Exit commands
        if user_input.lower() in {"quit", "exit", "bye", "goodbye"}:
            print("\n🌿 Take care and stay mindful. Goodbye!\n")
            sys.exit(0)

        # Skip empty input — mirrors the `if (!userText || isLoading)` guard
        if not user_input:
            continue

        conversation_history = send_message(user_input, conversation_history)


if __name__ == "__main__":
    main()
