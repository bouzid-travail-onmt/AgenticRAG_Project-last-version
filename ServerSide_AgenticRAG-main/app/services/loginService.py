# app/services/loginService.py
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
from app.db import get_mongo_client

SECRET_KEY = "super_secret_key_2025_change_me"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    """Vérifie si le mot de passe correspond"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})

    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    # ✅ Enregistrer le token actif (1 session max)
    db = get_mongo_client()
    db["users"].update_one(
        {"username": data["sub"]},
        {
            "$set": {
                "active_token": token,
                "last_login": datetime.utcnow()
            }
        }
    )

    return token


def authenticate_user(username: str, password: str):
    """Vérifie les identifiants dans la base MongoDB"""
    db = get_mongo_client()
    user = db["users"].find_one({"username": username})
    if not user or not verify_password(password, user["password"]):
        return None
    return user
