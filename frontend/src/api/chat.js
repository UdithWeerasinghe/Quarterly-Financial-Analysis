// frontend/src/api/chat.js
export async function sendChatMessage(message) {
    const response = await fetch("http://localhost:5000/api/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: message })
    });
    if (!response.ok) {
      throw new Error("Failed to get response from backend");
    }
    const data = await response.json();
    return data.response;
  }