function ensurePreviewCard() {
  let preview = document.getElementById("next-card-preview");
  if (!preview) {
    preview = document.createElement("div");
    preview.id = "next-card-preview";
    preview.className = "person-card next-card-preview";
    preview.hidden = true;
    const personCard = document.getElementById("person-card");
    if (personCard && personCard.parentNode) {
      personCard.parentNode.insertBefore(preview, personCard);
    }
  }
  return preview;
}

async function loadCards() {
  const res = await fetch("/api/discover");
  const data = await res.json();
  return Array.isArray(data.cards) ? data.cards : [];
}

function renderCard(card) {
  if (!card) return;

  const el = document.getElementById("person-card");
  const photo = document.getElementById("card-photo");
  const name = document.getElementById("card-name");
  const age = document.getElementById("card-age");
  const city = document.getElementById("card-city");
  const bio = document.getElementById("card-bio");
  const tags = document.getElementById("card-tags");

  const fallbackPhoto = "/static/placeholder.svg";
  photo.src = card.photo || fallbackPhoto;
  photo.alt = card.name || "Profile";
  name.textContent = card.name || "Unknown";
  age.textContent = card.age ? `, ${card.age}` : "";
  city.textContent = card.city || "";
  bio.textContent = card.bio || "";

  tags.innerHTML = "";
  (Array.isArray(card.interests) ? card.interests : []).forEach((interest) => {
    const span = document.createElement("span");
    span.textContent = interest;
    tags.appendChild(span);
  });

  el.hidden = false;
  el.style.transition = "transform 0.25s ease, opacity 0.25s ease";
  el.style.transform = "translateY(0) scale(1)";
  el.style.opacity = "1";

  const nextCard = window.cards && window.cards[1];
  const stacked = ensurePreviewCard();
  if (nextCard && stacked) {
    stacked.hidden = false;
    stacked.style.transform = "translateY(12px) scale(0.97)";
    stacked.style.opacity = "0.8";
  }
}

function showEmpty() {
  document.getElementById("person-card").hidden = true;
  document.getElementById("swipe-actions").hidden = true;
  document.getElementById("empty-state").hidden = false;
}

function animateSwipe(direction) {
  const card = document.getElementById("person-card");
  if (!card) return Promise.resolve();

  const offset = direction === "left" ? -120 : 120;
  card.style.transition = "transform 0.35s ease, opacity 0.35s ease";
  card.style.transform = `translateX(${offset}%) rotate(${direction === "left" ? -12 : 12}deg)`;
  card.style.opacity = "0";

  return new Promise((resolve) => setTimeout(resolve, 350));
}

async function swipe(liked) {
  if (!window.currentCard) return;

  const direction = liked ? "right" : "left";
  const swipeAnimation = animateSwipe(direction);

  try {
    const res = await fetch("/api/swipe", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target_id: window.currentCard.id, liked }),
    });

    const data = await res.json();
    if (data.matched && data.match) {
      document.getElementById("match-name").textContent = data.match.name;
      document.getElementById("match-photo").src = data.match.photo || "/static/placeholder.svg";
      document.getElementById("match-chat").href = `/chat/${data.match.id}`;
      document.getElementById("match-modal").hidden = false;
    }
  } catch (error) {
    console.error("Swipe request failed", error);
  }

  await swipeAnimation;
  nextCard();
}

function nextCard() {
  window.cards = Array.isArray(window.cards) ? window.cards : [];
  if (window.cards.length) {
    window.cards.shift();
  }

  const card = document.getElementById("person-card");
  if (card) {
    card.style.transition = "";
    card.style.transform = "";
    card.style.opacity = "";
  }

  const stacked = document.getElementById("next-card-preview");
  if (stacked) {
    stacked.hidden = true;
  }

  if (!window.cards.length) {
    window.currentCard = null;
    showEmpty();
    return;
  }

  window.currentCard = window.cards[0];
  renderCard(window.currentCard);
}

document.getElementById("like-btn").addEventListener("click", () => swipe(true));
document.getElementById("pass-btn").addEventListener("click", () => swipe(false));
document.getElementById("match-keep").addEventListener("click", () => {
  document.getElementById("match-modal").hidden = true;
});

loadCards().then((cards) => {
  window.cards = Array.isArray(cards) ? cards : [];

  if (!window.cards.length) {
    showEmpty();
    return;
  }

  const preview = ensurePreviewCard();
  if (preview && window.cards[1]) {
    preview.hidden = false;
    preview.style.transform = "translateY(12px) scale(0.97)";
    preview.style.opacity = "0.8";
  }

  document.getElementById("swipe-actions").hidden = false;
  window.currentCard = window.cards[0];
  renderCard(window.currentCard);
});
