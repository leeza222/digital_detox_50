/* ============================================
   DIGITAL DETOX HUB — CHATBOT ENGINE
   chatbot.js

   Calls Python Flask backend (app.py) → Google Gemini.
   Pure Vanilla JS, no frameworks.
   ============================================ */

(function () {
  "use strict";

  /* --------------------------------------------------
     CONFIGURATION
     -------------------------------------------------- */
  const CONFIG = {
    /**
     * URL of your Python Flask backend.
     *
     * LOCAL DEV  → python app.py  → http://localhost:5000/api/chat
     * PRODUCTION → replace with your deployed server URL:
     *   e.g. https://your-app.onrender.com/api/chat
     */
    backendUrl: "http://localhost:5000/api/chat",

    /** Maximum conversation turns kept in memory per session */
    maxHistoryTurns: 20,
  };

  /* --------------------------------------------------
     DOM REFERENCES — populated after DOMContentLoaded
     -------------------------------------------------- */
  let toggleBtn, closeBtn, chatWindow, chatMessages, chatInput, sendBtn, typingIndicator;

  /* --------------------------------------------------
     STATE
     -------------------------------------------------- */

  /**
   * Full conversation history for the current session.
   * Format follows the Gemini REST API "contents" array:
   *   { role: "user" | "model", parts: [{ text: "..." }] }
   */
  let conversationHistory = [];

  /** Whether the chat panel is currently open */
  let isOpen = false;

  /** Prevents double-sends while a request is in-flight */
  let isLoading = false;

  /* --------------------------------------------------
     HELPERS
     -------------------------------------------------- */

  /** Returns current time as "H:MM AM/PM" */
  function getTimestamp() {
    const now = new Date();
    let h = now.getHours();
    const m = String(now.getMinutes()).padStart(2, "0");
    const ampm = h >= 12 ? "PM" : "AM";
    h = h % 12 || 12;
    return h + ":" + m + " " + ampm;
  }

  /** Scrolls message area to the latest message */
  function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  /* --------------------------------------------------
     RENDER MESSAGES
     -------------------------------------------------- */

  /**
   * Appends a chat bubble.
   * @param {"user"|"bot"|"error"} sender
   * @param {string}               text
   */
  function appendMessage(sender, text) {
    const wrapper = document.createElement("div");
    wrapper.classList.add("chat-msg", sender);

    /* Bot / error icon */
    if (sender === "bot" || sender === "error") {
      const icon = document.createElement("span");
      icon.className = "msg-icon";
      icon.setAttribute("aria-hidden", "true");
      icon.textContent = sender === "error" ? "⚠️" : "🌿";
      wrapper.appendChild(icon);
    }

    const inner = document.createElement("div");

    const bubble = document.createElement("div");
    bubble.className = "msg-bubble";
    bubble.textContent = text; /* textContent = safe, pre-wrap handles newlines */
    inner.appendChild(bubble);

    const time = document.createElement("div");
    time.className = "msg-time";
    time.setAttribute("aria-hidden", "true");
    time.textContent = getTimestamp();
    inner.appendChild(time);

    wrapper.appendChild(inner);
    chatMessages.appendChild(wrapper);
    scrollToBottom();
  }

  /* --------------------------------------------------
     TYPING INDICATOR
     -------------------------------------------------- */

  function showTyping() {
    typingIndicator.classList.add("visible");
    scrollToBottom();
  }

  function hideTyping() {
    typingIndicator.classList.remove("visible");
  }

  /* --------------------------------------------------
     TOGGLE CHAT PANEL
     -------------------------------------------------- */

  function openChat() {
    isOpen = true;
    chatWindow.classList.add("chat-open");
    toggleBtn.setAttribute("aria-expanded", "true");
    toggleBtn.querySelector("i").className = "fas fa-times";
    setTimeout(function () { chatInput.focus(); }, 310);
  }

  function closeChat() {
    isOpen = false;
    chatWindow.classList.remove("chat-open");
    toggleBtn.setAttribute("aria-expanded", "false");
    toggleBtn.querySelector("i").className = "fas fa-comment-dots";
    toggleBtn.focus();
  }

  function toggleChat() {
    isOpen ? closeChat() : openChat();
  }

  /* --------------------------------------------------
     AUTO-RESIZE TEXTAREA
     -------------------------------------------------- */

  function autoResizeInput() {
    chatInput.style.height = "auto";
    chatInput.style.height = Math.min(chatInput.scrollHeight, 110) + "px";
  }

  /* --------------------------------------------------
     API — CALL PYTHON FLASK BACKEND
     -------------------------------------------------- */

  /**
   * POSTs conversation history to the Flask backend (/api/chat)
   * which proxies the request to Google Gemini server-side.
   * @returns {Promise<string>} The assistant's reply text.
   */
  async function callBackend() {
    const recentHistory = conversationHistory.slice(-CONFIG.maxHistoryTurns);

    const response = await fetch(CONFIG.backendUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: recentHistory }),
    });

    /* Always parse JSON — Flask returns JSON even for errors */
    let data;
    try {
      data = await response.json();
    } catch (_) {
      throw new Error(
        "Server returned an unexpected response (HTTP " + response.status + "). " +
        "Make sure the Python backend is running: python app.py"
      );
    }

    /* Propagate server-side error message to the UI */
    if (!response.ok) {
      throw new Error(data.error || "Server error " + response.status);
    }

    if (!data.reply || data.reply.trim() === "") {
      throw new Error("Received an empty response from the AI.");
    }

    return data.reply.trim();
  }

  /* --------------------------------------------------
     SEND MESSAGE
     -------------------------------------------------- */

  async function sendMessage() {
    const userText = chatInput.value.trim();

    /* Guard: empty input or request in-flight */
    if (!userText || isLoading) return;

    /* Render user bubble */
    appendMessage("user", userText);

    /* Clear + reset input */
    chatInput.value = "";
    chatInput.style.height = "auto";
    chatInput.focus();

    /* Lock UI */
    isLoading = true;
    sendBtn.disabled = true;
    showTyping();

    /* Add user turn to history */
    conversationHistory.push({
      role: "user",
      parts: [{ text: userText }],
    });

    try {
      const replyText = await callBackend();

      /* Add model turn to history */
      conversationHistory.push({
        role: "model",
        parts: [{ text: replyText }],
      });

      hideTyping();
      appendMessage("bot", replyText);
    } catch (err) {
      hideTyping();

      /* User-friendly error messages */
      let msg;
      if (!navigator.onLine) {
        msg = "You appear to be offline. Please check your internet connection.";
      } else if (err.message.includes("Failed to fetch") || err.message.includes("NetworkError")) {
        msg =
          "Cannot reach the chatbot server. Please make sure the Python backend is running:\n\n" +
          "  python app.py";
      } else if (err.message.length < 220) {
        msg = "Oops! " + err.message;
      } else {
        msg = "Something went wrong. Please try again in a moment.";
      }

      appendMessage("error", msg);

      /* Remove the last user turn so the user can retry */
      conversationHistory.pop();

      console.error("[Chatbot] Backend error:", err);
    } finally {
      isLoading = false;
      sendBtn.disabled = false;
    }
  }

  /* --------------------------------------------------
     WELCOME MESSAGE
     -------------------------------------------------- */

  function showWelcome() {
    const welcome = document.createElement("p");
    welcome.className = "chat-welcome";
    welcome.textContent = "🌿 Your digital wellness companion • Powered by Gemini AI";
    chatMessages.appendChild(welcome);

    appendMessage(
      "bot",
      "Hi there! 👋 I'm your Digital Wellness Assistant. I can help you:\n\n" +
        "• Reduce screen time & build better habits\n" +
        "• Find mindfulness & focus strategies\n" +
        "• Suggest healthy tech boundaries\n\n" +
        "What's on your mind today?"
    );
  }

  /* --------------------------------------------------
     EVENT LISTENERS
     -------------------------------------------------- */

  function attachListeners() {
    toggleBtn.addEventListener("click", toggleChat);
    closeBtn.addEventListener("click", closeChat);
    sendBtn.addEventListener("click", sendMessage);

    /* Enter to send, Shift+Enter for newline */
    chatInput.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });

    /* Auto-resize textarea */
    chatInput.addEventListener("input", autoResizeInput);

    /* Click outside → close */
    document.addEventListener("click", function (e) {
      if (isOpen && !e.target.closest(".chatbot-wrapper")) {
        closeChat();
      }
    });

    /* Escape → close */
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && isOpen) closeChat();
    });
  }

  /* --------------------------------------------------
     INIT
     -------------------------------------------------- */

  function init() {
    toggleBtn       = document.getElementById("chatToggleBtn");
    closeBtn        = document.getElementById("chatCloseBtn");
    chatWindow      = document.getElementById("chatWindow");
    chatMessages    = document.getElementById("chatMessages");
    chatInput       = document.getElementById("chatInput");
    sendBtn         = document.getElementById("chatSendBtn");
    typingIndicator = document.getElementById("chatTyping");

    if (!toggleBtn || !chatWindow) {
      console.warn("[Chatbot] HTML elements not found. Chatbot disabled.");
      return;
    }

    attachListeners();
    showWelcome();

    console.log(
      "%c🌿 Wellness Chatbot ready  (Flask → Gemini)",
      "color:#9DC88D;font-weight:bold;"
    );
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

})();
