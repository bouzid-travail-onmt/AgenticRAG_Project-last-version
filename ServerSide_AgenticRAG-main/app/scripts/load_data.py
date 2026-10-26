import os
import gridfs
from app.db import get_mongo_client

# --- Connexion MongoDB via ton utilitaire ---
db = get_mongo_client()

# --- GridFS pour PDF ---
fs_pdfs = gridfs.GridFS(db, collection="pdfs")

# --- Collection brute pour Excels ---
excels_collection = db["excels"]

# --- Chemins des données ---
BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "Data")
pdf_folder = os.path.join(BASE_DIR, "rapports")
excel_folder = os.path.join(BASE_DIR, "excels")

# --- Upload des PDFs ---
for filename in os.listdir(pdf_folder):
    if filename.endswith(".pdf"):
        file_path = os.path.join(pdf_folder, filename)
        with open(file_path, "rb") as f:
            if not fs_pdfs.exists({"filename": filename}):
                fs_pdfs.put(f, filename=filename)
                print(f"✅ PDF inséré : {filename}")
            else:
                print(f"⚠️ PDF déjà présent : {filename}")

# --- Upload des Excels ---
for filename in os.listdir(excel_folder):
    if filename.endswith((".xlsx", ".xls")):
        file_path = os.path.join(excel_folder, filename)
        with open(file_path, "rb") as f:
            if excels_collection.count_documents({"filename": filename}) == 0:
                excels_collection.insert_one({
                    "filename": filename,
                    "file_data": f.read()
                })
                print(f"✅ Excel inséré : {filename}")
            else:
                print(f"⚠️ Excel déjà présent : {filename}")

print("🚀 Upload terminé avec succès")
