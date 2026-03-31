const messagesEl = document.getElementById("messages");
const form = document.getElementById("chat-form");
const input = document.getElementById("message-input");
const chips = document.querySelectorAll(".chips button");

function extractCodeBlock(text) {
  const fenced = text.match(/```(?:\w+)?\n([\s\S]*?)```/);
  if (fenced) {
    return fenced[1].trim();
  }
  return null;
}

function looksLikeCode(text) {
  const trimmed = text.trim();
  if (!trimmed.includes("\n")) {
    return false;
  }

  const codeHints = [
    "def ",
    "class ",
    "public ",
    "private ",
    "function ",
    "const ",
    "let ",
    "var ",
    "#include",
    "import ",
    "return ",
    "{",
    "};",
  ];

  return codeHints.some((hint) => trimmed.includes(hint));
}

function renderMessage(node, text, role) {
  node.innerHTML = "";

  const code = extractCodeBlock(text) || (role === "bot" && looksLikeCode(text) ? text.trim() : null);
  if (!code) {
    node.textContent = text;
    return;
  }

  const wrapper = document.createElement("div");
  wrapper.className = "code-card";

  const actions = document.createElement("div");
  actions.className = "code-actions";

  const button = document.createElement("button");
  button.type = "button";
  button.className = "copy-btn";
  button.textContent = "Copy code";
  button.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(code);
      button.textContent = "Copied";
      setTimeout(() => {
        button.textContent = "Copy code";
      }, 1200);
    } catch (error) {
      button.textContent = "Copy failed";
      setTimeout(() => {
        button.textContent = "Copy code";
      }, 1200);
    }
  });

  const pre = document.createElement("pre");
  const codeEl = document.createElement("code");
  codeEl.textContent = code;
  pre.appendChild(codeEl);

  actions.appendChild(button);
  wrapper.appendChild(actions);
  wrapper.appendChild(pre);
  node.appendChild(wrapper);
}

function addMessage(text, role) {
  const node = document.createElement("div");
  node.className = `msg ${role}`;
  renderMessage(node, text, role);
  messagesEl.appendChild(node);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return node;
}

async function sendMessage(message) {
  addMessage(message, "user");
  const pending = addMessage("Thinking...", "bot");

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });

    const data = await response.json();
    renderMessage(pending, data.response || "Something went wrong.", "bot");
  } catch (error) {
    renderMessage(pending, "Connection issue. Please try again.", "bot");
  }
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const message = input.value.trim();
  if (!message) return;
  input.value = "";
  await sendMessage(message);
});

chips.forEach((chip) => {
  chip.addEventListener("click", async () => {
    await sendMessage(chip.dataset.prompt);
  });
});

addMessage(
  "Hi! I talk naturally and can help with live weather, news headlines, coding questions, and health tips.",
  "bot"
);
