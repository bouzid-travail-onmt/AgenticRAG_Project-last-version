from fastapi import Request, HTTPException
from sse_starlette.sse import EventSourceResponse
from datetime import datetime

from app.core.sse_security import fernet, SSE_TOKEN_STORE
from app.services.data_preprocessing import preprocess_data_pipeline_excels, preprocess_data_pipeline_pdf
from fastapi import APIRouter

router = APIRouter()

# SSE sécurisé pour les fichiers Excel
@router.get("/preprocessingexcels")
async def preprocessing_excels_sse(request: Request, sse_token: str):

    # 1️⃣ Déchiffrement du token SSE
    try:
        raw_token = fernet.decrypt(sse_token.encode()).decode()
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid SSE token")

    # 2️⃣ Validation du token
    token_data = SSE_TOKEN_STORE.get(raw_token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Unknown SSE token")

    if token_data["expires_at"] < datetime.utcnow():
        del SSE_TOKEN_STORE[raw_token]
        raise HTTPException(status_code=401, detail="Expired SSE token")

    # 3️⃣ Génération du flux SSE depuis votre pipeline Excel
    async def event_generator():
        async for msg in preprocess_data_pipeline_excels():
            yield f"data: {msg}\n\n"

    return EventSourceResponse(event_generator())


# SSE sécurisé pour les rapports PDF
@router.get("/preprocessingreports")
async def preprocessing_reports_sse(request: Request, sse_token: str):

    # 1️⃣ Déchiffrement du token SSE
    try:
        raw_token = fernet.decrypt(sse_token.encode()).decode()
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid SSE token")

    # 2️⃣ Validation du token
    token_data = SSE_TOKEN_STORE.get(raw_token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Unknown SSE token")

    if token_data["expires_at"] < datetime.utcnow():
        del SSE_TOKEN_STORE[raw_token]
        raise HTTPException(status_code=401, detail="Expired SSE token")

    # 3️⃣ Génération du flux SSE depuis votre pipeline PDF
    async def event_generator():
        async for msg in preprocess_data_pipeline_pdf():
            yield f"data: {msg}\n\n"

    return EventSourceResponse(event_generator())
