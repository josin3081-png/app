const otherId = window.SPARK_CHAT.otherId;
const thread = document.getElementById("thread");
const form = document.getElementById("composer");
const input = document.getElementById("message-input");
let lastId = 0;

const typingIndicator = document.createElement("div");
typingIndicator.className = "typing-indicator";
typingIndicator.textContent = "Other user is typing…";
typingIndicator.hidden = true;
typingIndicator.style.fontSize = "0.8rem";
typingIndicator.style.opacity = "0.75";
typingIndicator.style.fontStyle = "italic";
typingIndicator.style.margin = "0.5rem 0";
thread.appendChild(typingIndicator);

function setTypingIndicator(isTyping) {
  typingIndicator.hidden = !isTyping;
  if (isTyping) {
    thread.scrollTop = thread.scrollHeight;
  }
}

function formatTimestamp(value) {
  const ts = value ?? new Date().toISOString();
  const date = new Date(ts);

  if (Number.isNaN(date.getTime())) {
    return "";
  }

  return date.toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit",
  });
}

function addMessage(msg) {
  setTypingIndicator(false);

  const bubble = document.createElement("div");
  bubble.className = `bubble${msg.mine ? " mine" : ""}`;

  const text = document.createElement("div");
  text.textContent = msg.body;
  bubble.appendChild(text);

  const timestamp = document.createElement("div");
  timestamp.className = "timestamp";
  timestamp.textContent = formatTimestamp(
    msg.created_at || msg.createdAt || msg.timestamp || new Date().toISOString()
  );
  timestamp.style.fontSize = "0.7rem";
  timestamp.style.opacity = "0.7";
  timestamp.style.marginTop = "0.25rem";
  bubble.appendChild(timestamp);

  thread.appendChild(bubble);
  thread.scrollTop = thread.scrollHeight;
}

async function setOwnTypingState(isTyping) {
  try {
    const res = await fetch(`/api/messages/${otherId}/typing`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ typing: isTyping }),
    });

    if (!res.ok) {
      return;
    }
  } catch (error) {
    // Ignore if the typing endpoint is not implemented yet.
  }
}

let typingTimer = null;
input.addEventListener("input", () => {
  const isTyping = input.value.trim().length > 0;
  setOwnTypingState(isTyping);

  if (typingTimer) {
    clearTimeout(typingTimer);
  }

  if (isTyping) {
    typingTimer = setTimeout(() => {
      setOwnTypingState(false);
    }, 2000);
  }
});

async function pull() {
  const res = await fetch(`/api/messages/${otherId}?after=${lastId}`);
  const data = await res.json();
  const typing = Boolean(
    data.typing || data.otherTyping || data.typingState || data.other_user_typing
  );

  setTypingIndicator(typing);

  (data.messages || []).forEach((msg) => {
    lastId = msg.id;
    addMessage(msg);
  });
}
form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const body = input.value.trim();
  if (!body) return;
  input.value = "";
  await setOwnTypingState(false);
  await fetch(`/api/messages/${otherId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ body }),
  });
  await pull();
});
pull();
setInterval(pull, 2000);