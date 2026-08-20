(() => {
  const script = document.currentScript;

  const config = {
    agentId: script?.dataset.agentId || "",
    webhookUrl: script?.dataset.webhookUrl || "",
    widgetToken: script?.dataset.widgetToken || "",
    title: script?.dataset.title || "Chat with us",
    color: script?.dataset.primaryColor || "#2563eb",
    welcomeMessage: "Hi! How can I help you today?"
  };

  function startWidget() {
    if (!config.webhookUrl || !config.widgetToken) {
      console.error("AI Chat Widget: data-webhook-url and data-widget-token are required.");
      return;
    }

    const style = document.createElement("style");
    style.textContent = `
      .ai-chat-widget {
        position: fixed; right: 20px; bottom: 20px; z-index: 999999;
        font-family: Arial, sans-serif;
      }
      .ai-chat-toggle {
        width: 58px; height: 58px; border: 0; border-radius: 50%;
        background: ${config.color}; color: white; font-size: 24px;
        cursor: pointer; box-shadow: 0 6px 20px rgba(0,0,0,.25);
        float: right;
      }
      .ai-chat-panel {
        display: none; width: 360px; height: 480px; margin-bottom: 12px;
        background: white; border-radius: 16px; overflow: hidden;
        box-shadow: 0 10px 30px rgba(0,0,0,.25); flex-direction: column;
      }
      .ai-chat-widget.open .ai-chat-panel { display: flex; }
      .ai-chat-header {
        background: ${config.color}; color: white; padding: 16px; font-weight: bold;
      }
      .ai-chat-messages {
        flex: 1; overflow-y: auto; padding: 14px; background: #f8fafc;
        display: flex; flex-direction: column; gap: 10px;
      }
      .ai-chat-message {
        max-width: 82%; padding: 10px 12px; border-radius: 12px;
        white-space: pre-wrap; word-break: break-word;
      }
      .ai-chat-bot { align-self: flex-start; background: white; border: 1px solid #e5e7eb; }
      .ai-chat-user { align-self: flex-end; background: ${config.color}; color: white; }
      .ai-chat-form { display: flex; gap: 8px; padding: 10px; border-top: 1px solid #e5e7eb; }
      .ai-chat-input { flex: 1; min-width: 0; padding: 10px; border: 1px solid #cbd5e1; border-radius: 8px; }
      .ai-chat-send { border: 0; border-radius: 8px; padding: 10px 14px; color: white; background: ${config.color}; cursor: pointer; }
      .ai-chat-send:disabled { opacity: .6; cursor: wait; }
    `;
    document.head.appendChild(style);

    const widget = document.createElement("div");
    widget.className = "ai-chat-widget";
    widget.innerHTML = `
      <div class="ai-chat-panel">
        <div class="ai-chat-header"></div>
        <div class="ai-chat-messages"></div>
        <form class="ai-chat-form">
          <input class="ai-chat-input" placeholder="Type your message..." maxlength="4000" />
          <button class="ai-chat-send" type="submit">Send</button>
        </form>
      </div>
      <button class="ai-chat-toggle" type="button">💬</button>
    `;

    document.body.appendChild(widget);

    const header = widget.querySelector(".ai-chat-header");
    const messages = widget.querySelector(".ai-chat-messages");
    const toggle = widget.querySelector(".ai-chat-toggle");
    const form = widget.querySelector(".ai-chat-form");
    const input = widget.querySelector(".ai-chat-input");
    const send = widget.querySelector(".ai-chat-send");

    header.textContent = config.title;

    const addMessage = (text, type) => {
      const message = document.createElement("div");
      message.className = `ai-chat-message ai-chat-${type}`;
      message.textContent = text;
      messages.appendChild(message);
      messages.scrollTop = messages.scrollHeight;
      return message;
    };

    addMessage(config.welcomeMessage, "bot");

    toggle.addEventListener("click", () => {
      widget.classList.toggle("open");
      if (widget.classList.contains("open")) input.focus();
    });

    form.addEventListener("submit", async (event) => {
      event.preventDefault();

      const userMessage = input.value.trim();
      if (!userMessage || send.disabled) return;

      addMessage(userMessage, "user");
      input.value = "";
      send.disabled = true;

      const replyElement = addMessage("Typing...", "bot");

      try {
        const response = await fetch(config.webhookUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Widget-Token": config.widgetToken
          },
          body: JSON.stringify({
            message: userMessage,
            conversation_id: sessionStorage.getItem(`ai-chat-conversation-${config.agentId}`),
            sender_type: "api",
            sender_origin: "website-widget"
          })
        });

        if (!response.ok) {
            throw new Error(`Request failed: ${response.status}`);
        }

        const data = await response.json();
        console.log("Chat response:", data);

        if (data.conversation_id) {
          sessionStorage.setItem(`ai-chat-conversation-${config.agentId}`, data.conversation_id);
        }

        replyElement.textContent =
            data.answer ||
            data.reply ||
            data.message ||
            data.response ||
            "No response was returned.";

      } catch (error) {
        console.error("Chat widget error:", error);
        replyElement.textContent = "Sorry, something went wrong. Please try again.";
      } finally {
        send.disabled = false;
      }
    });
  }

  if (document.body) startWidget();
  else document.addEventListener("DOMContentLoaded", startWidget);
})();
