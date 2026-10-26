# app/routes/login_router.py
from fastapi import APIRouter, HTTPException, status, Depends, Response
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta, datetime
from app.services import loginService
from app.core.security import get_current_user
from app.db import get_mongo_client
router = APIRouter()


@router.post("/login")
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """Authentifie un utilisateur et renvoie un token JWT"""

    # 🔹 Vérification des identifiants
    user = loginService.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nom d'utilisateur ou mot de passe invalide",
        )

    # 🔹 Création du token JWT
    access_token_expires = timedelta(minutes=loginService.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = loginService.create_access_token(
        data={"sub": user["username"], "role": user["role"]},
        expires_delta=access_token_expires,
    )

    # 🔹 Enregistrement du token actif et de la dernière activité
    db = get_mongo_client()
    db["users"].update_one(
        {"username": user["username"]},
        {"$set": {"active_token": access_token, "last_activity": datetime.utcnow()}}
    )

    # 🔹 COOKIE SÉCURISÉ
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,          # ⚠️ True en HTTPS (prod)
        samesite="Strict",
        max_age=loginService.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

    # 🔹 Retour JSON (React utilise encore le token côté frontend)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user["username"],
        "role": user["role"],
    }


@router.post("/logout")
def logout(user=Depends(get_current_user)):
    """Déconnexion : supprime le token actif"""
    db = get_mongo_client()
    db["users"].update_one(
        {"username": user["username"]},
        {"$unset": {"active_token": ""}}
    )
    return {"message": "Déconnexion réussie"}

# Exemple de route protégée
