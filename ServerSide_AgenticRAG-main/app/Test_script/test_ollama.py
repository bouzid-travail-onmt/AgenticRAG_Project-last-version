# test_ollama_requests_stream_clean.py
import requests
import json
from app.core.config import OLLAMA_HOST, OLLAMA_MODEL

def test_ollama_stream(prompt: str):
    url = f"{OLLAMA_HOST}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": True
    }

    print("✅ Début du streaming Ollama ...\n")
    final_text = ""

    with requests.post(url, json=payload, stream=True) as r:
        for line in r.iter_lines():
            if line:
                try:
                    data = json.loads(line.decode("utf-8"))
                    if "response" in data:
                        final_text += data["response"]
                        print(data["response"], end="", flush=True)  # affichage en direct
                except json.JSONDecodeError:
                    continue

    print("\n\n✅ Réponse finale :")
    print(final_text)

if __name__ == "__main__":
    test_ollama_stream("Bonjour, peux-tu tester le streaming et répondre clairement ?")
# Pour exécuter ce script, assurez-vous que le serveur Ollama est en cours d'exécution
# et que les variables d'environnement OLLAMA_HOST et OLLAMA_MODEL sont correctement défin