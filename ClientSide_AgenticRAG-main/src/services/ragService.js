const BASE_URL = "/api/public";
/**
 * Envoie une question au backend et reçoit la réponse en streaming (chunk par chunk)
 * @param {string} query - La question posée par l'utilisateur
 * @param {function} onMessageChunk - Callback pour chaque morceau de texte reçu
 * @returns {Promise<string>} - Réponse complète
 */
export async function askQuestion(query, onMessageChunk) {
  try {
    const response = await fetch(`${BASE_URL}/rag/ask?query=${encodeURIComponent(query)}`);
    if (!response.ok) throw new Error(`Erreur serveur: ${response.status}`);

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let result = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      result += chunk;
      if (onMessageChunk) {
        onMessageChunk(chunk); // streaming en temps réel
      }
    }

    return result;
  } catch (error) {
    console.error("Erreur streaming:", error);
    return "❌ Erreur serveur, veuillez réessayer.";
  }
}
