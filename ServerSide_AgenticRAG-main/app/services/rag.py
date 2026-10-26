from fastapi.responses import StreamingResponse
import requests
import json
import asyncio
from app.services.vector_store import search_vector_db
from app.services.request_handling_elasticsearch import search_in_elasticsearch
from app.core.config import ES_INDEX, OLLAMA_HOST, OLLAMA_MODEL
'''
def build_prompt(query: str, results_faiss: list, results_es: list) -> str:
    es_context = ""
    if results_es:
        es_context = "=== Données Excel ===\n"
        for r in results_es:
            es_context += (
                f"[Source: {r.get('source','N/A')} | "
                f"Année: {r.get('year','N/A')} | "
                f"Indicateur: {r.get('indicator','N/A')} | "
                f"Milieu: {r.get('milieu','N/A')}]\n"
                f"Valeur: {r.get('value','N/A')}\n\n"
            )

    faiss_context = ""
    if results_faiss:
        faiss_context = "=== Rapports et Web Scraping ===\n"
        for r in results_faiss:
            faiss_context += f"[Source: {r.get('source','?')}]\n{r.get('chunk','')}\n\n"

    prompt = f"""
Vous êtes un assistant expert en économie et en indicateurs socio-économiques marocains.
Votre rôle est de fournir une réponse finale unique, claire, bien formulée, bien structurée et sourcée.

Contexte issu des Données excel :
{es_context if es_context else "⚠️ Aucune donnée trouvée"}

Contexte issu des Rapports de l'observatoire & Web Scraping :
{faiss_context if faiss_context else "⚠️ Aucune donnée trouvée"}

Question posée :
{query}

Instructions obligatoires :
1. Si les Données excel fournit des données, commencez par les analyser en priorité.

2. Si les Rapports de l'observatoire & Web Scraping fournit des données et que les Données excel est vide, utilisez uniquement les Rapports de l'observatoire & Web Scraping.

3. Si les deux sources sont disponibles, comparez-les :
   - Vérifiez si les chiffres / informations sont cohérents.
   - Si elles divergent, expliquez brièvement la différence et tranchez en faveur de la source la plus fiable (les Données excel > Rapports & Web Scraping).
   - Reformulez ensuite une seule réponse claire.

4. Mentionnez explicitement la ou les sources utilisées ("Source : Données excel", "Source : Rapports", ou "Sources croisées").

5. Absence de données concrètes
Si aucune information n’est disponible, que ce soit dans les rapports ou dans les fichiers Excel, vous pouvez répondre en indiquant que vous ne disposez pas de données suffisantes pour répondre à la question.

6. colorer les chiffres en gras dans la réponse finale et aussi les sources utilisées.

7. La réponse doit être bien formulées,bien structurées, bien présentées,bien rédigées et organisées, concise, en français, sous la forme :
   - **Réponse finale** :  Chiffres ou informations claires .
   - **Analyse** : raisonnement logique et rigoureux ou comparaison des sources comme un expert en indicateurs socio-économiques .
   - **Source(s)** : citer les sources en detail.
"""
    return prompt
'''
def build_prompt(query: str, results_faiss: list, results_es: list) -> str:
    """Construire un prompt complet, riche en métadonnées et hiérarchisé,
    à partir des résultats FAISS (rapports/web) et Elasticsearch (Excel/HCP/CNSS)."""

    # ======================
    # 🔹 Contexte Elasticsearch — Données structurées (Excel / HCP)
    # ======================
    if results_es:
        es_context = "=== 📊 Données structurées Excels ===\n"
        for r in results_es:
             es_context += (
            f"**Fichier :** {r.get('filename', 'N/A')}\n"
            f"**Source :** {r.get('source', 'Inconnue')}\n"
            f"**Année :** {r.get('year', 'N/A')}\n"
            f"**Indicateur :** {r.get('indicator', 'N/A')}\n"
            f"**Région :** {r.get('region', 'N/A')}\n"
            f"**Milieu :** {r.get('milieu', 'N/A')}\n"
            f"**Genre :** {r.get('genre', 'N/A')}\n"
            f"**Secteur :** {r.get('secteur', 'N/A')}\n"
            f"**Catégorie :** {r.get('categorie', 'N/A')}\n"
            f"**Tranche d’âge :** {r.get('tranche_age', 'N/A')}\n"
            f"**Valeur :** {r.get('value', 'N/A')}\n"
            f"───────────────────────────────\n"
        )
    else:
        es_context = "⚠️ Aucune donnée trouvée\n"

    # ======================
    # 🔹 Contexte FAISS — Rapports et Web Scraping
    # ======================
    if results_faiss:
        faiss_context = "=== 📚 Rapports et Web Scraping ===\n"
        for r in results_faiss:
            faiss_context += (
                f"🗂 **Source :** {r.get('source', 'Inconnue')}\n"
                f"🧾 **Extrait de texte :**\n{r.get('chunk', '').strip()}\n"
                f"───────────────────────────────\n"
            )
    else:
        faiss_context = "⚠️ Aucun extrait de rapport ou contenu web trouvé\n"

    # ======================
    # 🧠 Prompt principal — Rédaction de la réponse
    # ======================
    prompt = f"""
Vous êtes un **assistant expert en économie et en indicateurs socio-économiques marocains**.
Votre objectif est de formuler une **réponse finale unique, claire, rigoureuse et sourcée**, à partir des informations disponibles ci-dessous.

───────────────────────────────
📈 **Contexte issu des Données structurées (Excel)** :
{es_context}

📘 **Contexte issu des Rapports & Web Scraping** :
{faiss_context}

❓ **Question posée** :
{query}
───────────────────────────────

La réponse doit être fournie sous cette forme structurée :

Réponse finale : une réponse finale structurée, bien formulée ,claire et raffinée  toujours (mettez les valeurs importantes en gras).

Analyse : explication économique, comparaison des tendances, comparaison par analogie ou interprétation.

Source(s) : liste claire et hiérarchisée des sources utilisées, en utilisant les métadonnées pour préciser exactement le fichier source, le rapport ou la section.

Sous conditions suivantes :
1. Priorité et fiabilité des sources

Les données Excel constituent la source la plus fiable.

Les rapports PDF et contenus web ne doivent être utilisés qu’en complément ou pour comparaison avec les données structurées.

Mentionnez toujours l’origine exacte de chaque donnée utilisée.

2. Comparaison et cohérence

Si plusieurs sources donnent des valeurs différentes, comparez-les.

Expliquez les divergences possibles (différence d’année, de méthodologie, de périmètre géographique…).

3. Cas d’absence ou d’incertitude

Si les données sont manquantes ou contradictoires, indiquez-le clairement.

Fournissez une réponse prudente, contextualisée.

Évitez d’utiliser des données vides ou nulles.

Si l'indicateur ou la question n'est pas préciser l'année de l'indicateur, il faut retourner l'année la plus récente disponible dans les données par rapport à l'année actuelle.

4. Style et rigueur

Langue : français professionnel, clair et fluide.

Ton : analytique, précis, cohérent avec le vocabulaire socio-économique marocain.

Présentation : structurée, avec une hiérarchie visuelle lisible et ne depasse pas 10 lignes.
"""
    return prompt

async def query_llm_stream(query: str, top_k_faiss: int = 10, top_k_es: int = 30):
    loop = asyncio.get_event_loop()

    # 1️⃣ FAISS et Elasticsearch en parallèle
    results_faiss_task = loop.run_in_executor(None, search_vector_db, query, top_k_faiss)
    results_es_task = loop.run_in_executor(None, search_in_elasticsearch, ES_INDEX, query, top_k_es)
    results_faiss, results_es = await asyncio.gather(results_faiss_task, results_es_task)

    # 2️⃣ Construire le prompt
    prompt = build_prompt(query, results_faiss, results_es)

    # 3️⃣ Fonction génératrice pour le streaming
    def generate():
        url = f"{OLLAMA_HOST}/api/generate"
        payload = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": True}

        try:
            with requests.post(url, json=payload, stream=True) as r:
                for line in r.iter_lines():
                    if line:
                        try:
                            data = json.loads(line.decode("utf-8"))
                            if "response" in data:
                                yield data["response"]
                        except Exception:
                            continue
        except Exception as e:
            yield f"❌ Erreur Ollama: {str(e)}"

    # 4️⃣ Retourner la réponse en streaming
    return StreamingResponse(generate(), media_type="text/plain")
