# app/api/routes/rag_indicator_public.py
from fastapi import APIRouter, Depends, Query, HTTPException
from app.services.rag import query_llm_stream
import json
import gridfs
from app.db import get_mongo_client
from app.services.rag import query_llm_stream

db = get_mongo_client()
router = APIRouter()
@router.get("/rag/ask")
async def ask_stream(query: str = Query(..., description="Votre question")):
    """
    Poser une question à l'LLM avec contexte FAISS + Elasticsearch.
    Réponse en streaming SSE.

    Exemple: /api/llm/ask?query=Quel%20est%20le%20taux%20de%20chomage%20en%202022%20?
    """
    # ⚡ ATTENTION : il faut await la coroutine
    return await query_llm_stream(query)

@router.get("/indicators")
async def list_indicators():
    """
    📊 Récupère et retourne le contenu complet des fichiers d'indicateurs JSON
    stockés dans GridFS ('training_data_indicators').
    - Lis chaque fichier JSON
    - Fusionne leur contenu dans une seule réponse
    - Inclut les métadonnées : nom du fichier source, nombre total d'indicateurs, etc.
    """
    #db = get_mongo_client()
    #from app.db import get_mongo_client
    try:
        fs_indicators = gridfs.GridFS(db, collection="training_data_indicators")
        all_indicators = []
        meta_list = []

        for f in db["training_data_indicators.files"].find():
            file_id = f["_id"]
            filename = f.get("filename", "fichier_sans_nom")

            try:
                # 📥 Lecture du contenu du fichier JSON depuis GridFS
                file_data = fs_indicators.get(file_id).read().decode("utf-8")

                # 🧩 Conversion JSON
                json_content = json.loads(file_data)

                # 🔢 Extraire les indicateurs (selon structure)
                if isinstance(json_content, dict):
                    indicators = json_content.get("indicators") or json_content
                elif isinstance(json_content, list):
                    indicators = json_content
                else:
                    indicators = []

                all_indicators.extend(indicators)

                # 🧾 Ajouter les métadonnées
                meta_list.append({
                    "filename": filename,
                    "total_indicators": len(indicators),
                    "createdAt": str(f.get("uploadDate")),
                    "id": str(file_id),
                })

            except Exception as e:
                print(f"[WARN] Impossible de lire {filename} : {e}")
                continue

        return {
            "count": len(all_indicators),
            "files": meta_list,
            "data": all_indicators,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des indicateurs : {e}")