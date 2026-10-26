import os
import json
from app.db import get_mongo_client


# --- Connexion MongoDB ---
db = get_mongo_client()
# --- Collections ---
json_collection = db["json_files"]
txt_collection = db["txt_files"]

# --- Dossier racine ---
BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "Data_after_preprocessing")

# --- Sous-dossiers ---
json_folder = os.path.join(BASE_DIR, "excel_json")
txt_folder = os.path.join(BASE_DIR, "pdf_txt")

# --- Upload des JSON ---
for filename in os.listdir(json_folder):
    if filename.endswith(".json"):
        file_path = os.path.join(json_folder, filename)
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if json_collection.count_documents({"filename": filename}) == 0:
                json_collection.insert_one({
                    "filename": filename,
                    "content": data
                })
                print(f"✅ JSON inséré : {filename}")
            else:
                print(f"⚠️ JSON déjà présent : {filename}")

# --- Upload des TXT ---
for filename in os.listdir(txt_folder):
    if filename.endswith(".txt"):
        file_path = os.path.join(txt_folder, filename)
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            if txt_collection.count_documents({"filename": filename}) == 0:
                txt_collection.insert_one({
                    "filename": filename,
                    "content": content
                })
                print(f"✅ TXT inséré : {filename}")
            else:
                print(f"⚠️ TXT déjà présent : {filename}")

print("🚀 Upload des données prétraitées terminé avec succès")
