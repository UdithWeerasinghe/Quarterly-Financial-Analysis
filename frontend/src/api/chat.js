// frontend/src/api/chat.js
export async function sendChatMessage(message) {
    const response = await fetch("http://127.0.0.1:5000/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message })
    });
    if (!response.ok) {
      throw new Error("Failed to get response from backend");
    }
    const data = await response.json();
    return data.response;
  }