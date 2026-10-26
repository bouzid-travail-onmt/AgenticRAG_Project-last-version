# backend/app/scripts/seed_user.py
 #python -m app.scripts.login_data

import sys
from datetime import datetime
from passlib.context import CryptContext
from pymongo.errors import ConnectionFailure
from app.db import get_mongo_client  # ✅ ta fonction de connexion centralisée

# Configuration du hashage
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def seed_admin_user():
    """
    Crée un utilisateur administrateur (si inexistant) dans MongoDB.
    """
    try:
        db = get_mongo_client()
        users = db["users"]

        username = "onmt@emploi.gov.ma"
        password = "onmt2025"

        # Vérifier si l'utilisateur existe déjà
        if users.find_one({"username": username}):
            print(f"⚠️  L'utilisateur '{username}' existe déjà.")
            return

        # Créer le document utilisateur
        user_doc = {
            "username": username,
            "password": pwd_context.hash(password),
            "role": "admin",
            "created_at": datetime.utcnow(),
        }

        users.insert_one(user_doc)
        print(f"✅ Utilisateur administrateur '{username}' ajouté avec succès !")

    except ConnectionFailure as e:
        print("❌ Erreur de connexion à MongoDB :", e)
        sys.exit(1)

    except Exception as e:
        print("❌ Erreur inattendue :", e)
        sys.exit(1)


if __name__ == "__main__":
    seed_admin_user()
