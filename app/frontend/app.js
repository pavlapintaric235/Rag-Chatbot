const API_BASE_URL = "https://nietzsche-rag-bot.onrender.com";

const backendUrlEl = document.getElementById("backend-url");
const healthStatusEl = document.getElementById("health-status");

backendUrlEl.textContent = API_BASE_URL;

async function checkBackendHealth() {
  try {
    const response = await fetch(`${API_BASE_URL}/health`, {
      method: "GET",
    });

    if (!response.ok) {
      healthStatusEl.textContent = `Backend responded with HTTP ${response.status}`;
      return;
    }

    const data = await response.json();

    if (data.status === "ok") {
      healthStatusEl.textContent = "Backend is healthy.";
      return;
    }

    healthStatusEl.textContent = "Backend responded, but status was unexpected.";
  } catch (error) {
    healthStatusEl.textContent = "Could not reach backend.";
    console.error("Health check failed:", error);
  }
}

checkBackendHealth();