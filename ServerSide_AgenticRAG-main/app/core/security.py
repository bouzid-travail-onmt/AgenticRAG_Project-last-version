# app/core/security.py
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from app.db import get_mongo_client
from app.services.loginService import SECRET_KEY, ALGORITHM



oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

INACTIVITY_TIMEOUT_MINUTES = 30

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise Exception
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Jeton invalide ou expiré",
        )

    db = get_mongo_client()
    user = db["users"].find_one({"username": username})

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur introuvable"
        )

    # ✅ Vérification session unique
    if user.get("active_token") != token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session invalide ou ouverte ailleurs"
        )

    last_activity = user.get("last_activity")

    if last_activity:
        if datetime.utcnow() - last_activity > timedelta(
            minutes=INACTIVITY_TIMEOUT_MINUTES
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expirée par inactivité"
            )

    # ✅ Mise à jour activité
    db["users"].update_one(
        {"username": username},
        {"$set": {"last_activity": datetime.utcnow()}}
    )

    return user
