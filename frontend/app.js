const chatForm = document.getElementById("chat-form");
const messageInput = document.getElementById("message-input");
const sendButton = document.getElementById("send-button");
const formStatus = document.getElementById("form-status");
const chatFeed = document.getElementById("chat-feed");

const userTemplate = document.getElementById("user-message-template");
const assistantTemplate = document.getElementById("assistant-message-template");
const suggestionButtons = document.querySelectorAll(".suggestion-chip");

async function sendChatMessage(message) {
  const response = await fetch("/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ message }),
  });

  if (!response.ok) {
    throw new Error(`Chat request failed with HTTP ${response.status}`);
  }

  return response.json();
}

function scrollFeedToBottom() {
  chatFeed.scrollTop = chatFeed.scrollHeight;
}

function createParagraphsFromText(text) {
  const fragment = document.createDocumentFragment();
  const paragraphs = String(text)
    .split(/\n\s*\n/)
    .map((part) => part.trim())
    .filter(Boolean);

  if (paragraphs.length === 0) {
    const p = document.createElement("p");
    p.textContent = text;
    fragment.appendChild(p);
    return fragment;
  }

  paragraphs.forEach((part) => {
    const p = document.createElement("p");
    p.textContent = part;
    fragment.appendChild(p);
  });

  return fragment;
}

function renderUserMessage(message) {
  const node = userTemplate.content.firstElementChild.cloneNode(true);
  const textEl = node.querySelector(".user-message-text");
  textEl.textContent = message;
  chatFeed.appendChild(node);
  scrollFeedToBottom();
}

function renderMatchedCards(container, matchedCardIds) {
  if (!Array.isArray(matchedCardIds) || matchedCardIds.length === 0) {
    return;
  }

  const section = document.createElement("section");
  section.className = "meta-block";

  const title = document.createElement("h3");
  title.className = "meta-title";
  title.textContent = "Matched cards";
  section.appendChild(title);

  const list = document.createElement("div");
  list.className = "chip-list";

  matchedCardIds.forEach((cardId) => {
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.textContent = cardId;
    list.appendChild(chip);
  });

  section.appendChild(list);
  container.appendChild(section);
}

function renderCitations(container, citations) {
  if (!Array.isArray(citations) || citations.length === 0) {
    return;
  }

  const section = document.createElement("section");
  section.className = "meta-block";

  const title = document.createElement("h3");
  title.className = "meta-title";
  title.textContent = "Citations";
  section.appendChild(title);

  const list = document.createElement("div");
  list.className = "citation-list";

  citations.forEach((citation) => {
    const item = document.createElement("article");
    item.className = "citation-item";

    const sourceLine = document.createElement("p");
    sourceLine.className = "citation-source";

    const work = citation.work || "Unknown work";
    const sectionName = citation.section ? ` · ${citation.section}` : "";
    const sourceId = citation.source_id ? ` · ${citation.source_id}` : "";
    sourceLine.textContent = `${work}${sectionName}${sourceId}`;

    const excerpt = document.createElement("p");
    excerpt.className = "citation-excerpt";
    excerpt.textContent = citation.text_excerpt || "";

    item.appendChild(sourceLine);
    item.appendChild(excerpt);
    list.appendChild(item);
  });

  section.appendChild(list);
  container.appendChild(section);
}

function renderAssistantMessage(payload) {
  const node = assistantTemplate.content.firstElementChild.cloneNode(true);

  const answerEl = node.querySelector(".assistant-answer");
  const cardsEl = node.querySelector(".assistant-cards");
  const citationsEl = node.querySelector(".assistant-citations");

  answerEl.appendChild(createParagraphsFromText(payload.answer || ""));
  renderMatchedCards(cardsEl, payload.matched_card_ids || []);
  renderCitations(citationsEl, payload.citations || []);

  chatFeed.appendChild(node);
  scrollFeedToBottom();
}

function setBusyState(isBusy) {
  sendButton.disabled = isBusy;
  messageInput.disabled = isBusy;
  sendButton.textContent = isBusy ? "Thinking..." : "Send";

  suggestionButtons.forEach((button) => {
    button.disabled = isBusy;
  });
}

suggestionButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const prompt = button.dataset.prompt || "";
    messageInput.value = prompt;
    messageInput.focus();
    messageInput.setSelectionRange(messageInput.value.length, messageInput.value.length);
  });
});

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const message = messageInput.value.trim();

  if (!message) {
    formStatus.textContent = "Write a message first.";
    return;
  }

  formStatus.textContent = "";
  renderUserMessage(message);
  messageInput.value = "";
  setBusyState(true);

  try {
    const payload = await sendChatMessage(message);
    renderAssistantMessage(payload);
  } catch (error) {
    const fallback = {
      answer: "The request failed before a grounded reply could be returned.",
      matched_card_ids: [],
      citations: [],
    };

    renderAssistantMessage(fallback);
    formStatus.textContent = error instanceof Error ? error.message : "Request failed.";
  } finally {
    setBusyState(false);
    messageInput.focus();
  }
});