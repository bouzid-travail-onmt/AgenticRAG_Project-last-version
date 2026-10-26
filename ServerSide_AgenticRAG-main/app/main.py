from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
import os
from time import time
from app.core.config import API_PREFIX, DEBUG, PROJECT_NAME, VERSION
from app.core.events import create_start_app_handler, create_stop_app_handler
from app.api.routes.api import router as api_router  # tes routes principales
from app.api.routes import login, admin, rag_indicator_public,preprocessing # import des routeurs


def get_application() -> FastAPI:
    application = FastAPI(title=PROJECT_NAME, debug=DEBUG, version=VERSION)

    # Autoriser le frontend React
    origins = [
        "https://onmt-ai-assistant.emploi.gov.ma",    
    ]

    # CORS pour autoriser ton frontend
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,  # utiliser la liste des origines
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"],  # Exposer l'en-tête pour les téléchargements
    )
    # Routes principales
    application.include_router(api_router, prefix=API_PREFIX)
    # LLM routes
    application.include_router(rag_indicator_public.router, prefix="/api/public", tags=["LLM", "RAG","indicators"])
    # ✅ Ajout du routeur de Login (authentification utilisateur)
    application.include_router(login.router, prefix="/api/auth", tags=["auth","logout"])
    # --- Inclusion du router admin ---
    application.include_router(admin.router, prefix="/api/admin", tags=["auth", "Data Preprocessing", "View Data", "ElasticSearch Management", "Indicators Management", "System Admin"])
    application.include_router(preprocessing.router, prefix="/api/admin", tags=["auth", "Data Preprocessing", "View Data", "ElasticSearch Management", "Indicators Management", "System Admin"])
    # --- Fin inclusion router admin (Toutes les features de l'admin dans ce router) ---
    # Event handlers
    application.add_event_handler("startup", create_start_app_handler(application))
    application.add_event_handler("shutdown", create_stop_app_handler(application))
    return application
# Instanciation de l'application FastAPI
app = get_application()
# ------------------------------------------------------------------
# 🔥 FIREWALL APPLICATIF SIMPLE (ANTI ABUS / BRUTE FORCE)
# ------------------------------------------------------------------

REQUEST_LIMIT = 100      # requêtes max
WINDOW_SECONDS = 60      # fenêtre de temps (secondes)
ip_requests = {}

@app.middleware("http")
async def simple_firewall(request: Request, call_next):
    ip = request.client.host
    now = time()

    records = ip_requests.get(ip, [])
    records = [t for t in records if now - t < WINDOW_SECONDS]
    records.append(now)
    ip_requests[ip] = records

    if len(records) > REQUEST_LIMIT:
        return JSONResponse(
            status_code=429,
            content={"detail": "Trop de requêtes, réessayez plus tard"}
        )

    return await call_next(request)
