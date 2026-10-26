# app/api/routes/admin.py
# ============================================================
# IMPORTS STANDARD
# ============================================================
import asyncio
import io
import json
from typing import List, Optional
from bson import ObjectId

from fastapi import Request
from sse_starlette.sse import EventSourceResponse
from datetime import datetime
from app.core.sse_security import fernet, SSE_TOKEN_STORE, SSE_TTL_SECONDS

from fastapi import APIRouter, Depends
from datetime import datetime, timedelta
import uuid
# ============================================================
# IMPORTS FASTAPI
# ============================================================
from fastapi import (
    APIRouter,
    UploadFile,
    Form,
    HTTPException,
    Query,
    Depends,
)
from fastapi.responses import StreamingResponse

# ============================================================
# IMPORTS DB / STORAGE
# ============================================================
import gridfs
from app.db import (
    get_mongo_client,
    get_elasticsearch,
    get_ollama,
)

# ============================================================
# IMPORTS CONFIG
# ============================================================
from app.core.config import ES_INDEX, OLLAMA_MODEL
from app.core.security import get_current_user

# ============================================================
# IMPORTS SERVICES
# ============================================================
from app.services.insert_data_db import process_and_store_data
from app.services.data_preprocessing import (
    preprocess_data_pipeline_excels,
    preprocess_data_pipeline_pdf,
)
from app.services.view_data_service import (
    fetch_files_from_db,
    fetch_recent_files_from_db,
    delete_file_from_db,
    delete_all_files_service,
    get_file_document,
    get_gridfs_file,
    list_documents_service,
    delete_document_service,
    delete_all_documents_service,
)
from app.services.request_handling_elasticsearch import search_in_elasticsearch
from app.services.vector_store import search_vector_db
from app.services.rag import query_llm_stream

# ============================================================
# ROUTER ADMIN (PROTÉGÉ)
# ============================================================
router = APIRouter(
    dependencies=[Depends(get_current_user)]
)

# ============================================================
# DB & GRIDFS (COMPORTEMENT IDENTIQUE)
# ============================================================
db = get_mongo_client()
fs_pdfs = gridfs.GridFS(db, collection="pdfs")
fs_excels = gridfs.GridFS(db, collection="excels")

# ============================================================
# 🔎 TEST / HEALTH / SEARCH
# ============================================================
@router.get("/search_es")
def search_es(query: str = Query(..., description="Texte libre à rechercher")):
    return {"query": query, "results": search_in_elasticsearch(ES_INDEX, query)}


@router.get("/healthcheck")
def healthcheck():
    result = {}

    try:
        result["mongo"] = db.command("ping")["ok"] == 1
    except Exception as e:
        result["mongo"] = str(e)

    try:
        es = get_elasticsearch()
        result["elasticsearch"] = es.ping()
    except Exception as e:
        result["elasticsearch"] = str(e)

    try:
        client = get_ollama()
        response = client.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": "ping"}]
        )
        result["ollama"] = "message" in response
    except Exception as e:
        result["ollama"] = str(e)

    return result


@router.get("/vector/search")
def vector_search(
    query: str = Query(...),
    top_k: int = Query(50),
):
    return {
        "query": query,
        "top_k": top_k,
        "results": search_vector_db(query, top_k=top_k),
    }

# ============================================================
# 📊 INDICATORS MANAGEMENT
# ============================================================
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


@router.delete("/indicators/{file_id}")
async def delete_indicator(file_id: str):
    fs_indicators = gridfs.GridFS(db, collection="training_data_indicators")
    oid = ObjectId(file_id)

    try:
        fs_indicators.get(oid)
        fs_indicators.delete(oid)
        return {"status": "success"}
    except:
        raise HTTPException(status_code=404, detail="Fichier indicateur inexistant")

# ============================================================
# 📂 FILE MANAGEMENT
# ============================================================
@router.get("/files")
async def list_files(type: str = Query(...)):
    return fetch_files_from_db(type)


@router.get("/files/recent")
async def list_recent_files(type: str = Query(...)):
    return fetch_recent_files_from_db(type)


@router.delete("/files/{file_id}")
async def delete_file(file_id: str, type: Optional[str] = Query(None)):
    if not delete_file_from_db(file_id, type):
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    return {"message": "✅ Fichier supprimé"}


@router.delete("/files/delete-all")
async def delete_all_files(type: Optional[str] = Query(None)):
    return delete_all_files_service(type)

# ============================================================
# 📥 DOWNLOAD
# ============================================================
@router.get("/files/{file_id}/download")
async def download_file(file_id: str, type: str = Query(...)):
    gf = get_gridfs_file(type, file_id)
    if not gf:
        raise HTTPException(status_code=404)

    return StreamingResponse(
        io.BytesIO(gf.read()),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename=\"{gf.filename}\""
        },
    )

# ============================================================
# 📤 UPLOAD + SSE
# ============================================================
@router.post("/upload")
async def upload_data(
    files: Optional[List[UploadFile]] = None,
    source_urls: Optional[List[str]] = Form(None),
):
    files = files or []
    urls = source_urls or []
    file_contents = []

    for f in files:
        content = await f.read()
        file_contents.append({"filename": f.filename, "content": content})

    async def generate_logs():
        async for log in process_and_store_data(file_contents, urls):
            yield f"data: {log}\n\n"

    return StreamingResponse(generate_logs(), media_type="text/event-stream")

# ============================================================
# 🔥 ELASTICSEARCH ADMIN
# ============================================================

@router.get("/es/documents")
async def list_documents(
    indicator: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    filename: Optional[str] = Query(None),
    page: Optional[int] = Query(1, gt=0),
    page_size: Optional[int] = Query(30, gt=0)
):
    return list_documents_service(
        indicator=indicator, 
        year=year, 
        filename=filename, 
        page=page,
        page_size=page_size
    )

@router.delete("/es/document/{doc_id}")
async def delete_document(doc_id: str):
    return delete_document_service(doc_id)

@router.delete("/es/documents/all")
async def delete_all_documents():
    return delete_all_documents_service()

# ============================================================
# 🧹 PREPROCESSING Excels & Reports 
# ============================================================
"""
@router.get("/preprocessingexcels")
async def preprocessing_excels():
    async def stream():
        async for msg in preprocess_data_pipeline_excels():
            yield f"data: {msg}\n\n"
    return StreamingResponse(stream(), media_type="text/event-stream")


@router.get("/preprocessingreports")
async def preprocessing_reports():
    async def stream():
        async for msg in preprocess_data_pipeline_pdf():
            yield f"data: {msg}\n\n"
    return StreamingResponse(stream(), media_type="text/event-stream")
"""


@router.post("/sse/token")
async def generate_sse_token(user=Depends(get_current_user)):
    import uuid
    from datetime import datetime, timedelta
    from app.core.sse_security import fernet, SSE_TOKEN_STORE, SSE_TTL_SECONDS

    raw_token = str(uuid.uuid4())
    encrypted_token = fernet.encrypt(raw_token.encode()).decode()

    # ⚡ Utiliser _id ou username comme identifiant
    user_id = str(user.get("_id"))  # ObjectId -> string
    # ou user.get("username") si vous préférez

    SSE_TOKEN_STORE[raw_token] = {
        "user_id": user_id,
        "expires_at": datetime.utcnow() + timedelta(seconds=SSE_TTL_SECONDS),
    }

    return {
        "sse_token": encrypted_token,
        "expires_in": SSE_TTL_SECONDS
    }

