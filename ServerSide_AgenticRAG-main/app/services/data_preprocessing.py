import os
import io
import re
import json
import math
import time
import unicodedata
from uuid import uuid4
from pathlib import Path
from datetime import datetime, timedelta
from typing import AsyncGenerator
import asyncio
import threading

import pandas as pd
import gridfs
from fastapi import UploadFile
from pymongo import MongoClient
from pymongo.database import Database
from elasticsearch import helpers
from PyPDF2 import PdfReader

from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
"""from langchain.embeddings import HuggingFaceEmbeddings"""
from langchain_huggingface import HuggingFaceEmbeddings

from app.core.config import ES_INDEX
from app.db import get_mongo_client, get_elasticsearch

# ==============================
# 🔧 Fonctions utilitaires
# ==============================

def clean_value(val):
    """Nettoyer une valeur en supprimant NaN ou inf."""
    if val is None:
        return None
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return None
    return val

def clean_dict(d):
    """Nettoyer récursivement un dictionnaire."""
    cleaned = {}
    for k, v in d.items():
        if isinstance(v, dict):
            cleaned[k] = clean_dict(v)
        elif isinstance(v, list):
            cleaned[k] = [clean_value(x) if not isinstance(x, dict) else clean_dict(x) for x in v]
        else:
            cleaned[k] = clean_value(v)
    return cleaned

def clean_numeric_value(value):
    """Nettoyer et convertir proprement les valeurs numériques."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if isinstance(value, str):
        cleaned_value_str = value.replace("\u202f", "").replace(",", ".")
        try:
            return float(cleaned_value_str)
        except (ValueError, TypeError):
            return None
    return None

def normalize_key(key: str) -> str:
    """Normaliser les clés: sans accents, minuscules, espaces nettoyés."""
    if not isinstance(key, str):
        return key
    key = key.strip().lower()
    key = unicodedata.normalize("NFD", key)
    key = "".join(c for c in key if unicodedata.category(c) != "Mn")
    key = key.replace(" ", "").replace("-", "")
    return key

def get_value_case_insensitive(row: dict, key: str):
    """Récupère une valeur sans tenir compte de la casse ni des accents."""
    target = normalize_key(key)
    for k, v in row.items():
        if normalize_key(k) == target:
            return v
    return None

def get_collections(db: Database):
    """Retourner les collections MongoDB (GridFS inclus)."""
    return {
        "pdfs": gridfs.GridFS(db, collection="pdfs"),
        "excels": gridfs.GridFS(db, collection="excels"),
        "urls": db["urls_scraping"],
        "txt": gridfs.GridFS(db, collection="training_data_txt"),
        "json": gridfs.GridFS(db, collection="training_data_json"),
        "indicators": gridfs.GridFS(db, collection="training_data_indicators")
    }

# ===================================
# 🧩 Pipeline de preprocessing Excel
# ===================================

DIMENSION_VALUES = {
    "Année", "Annee", "Milieu", "Region",
    "Categorie", "Genre", "Secteur", "Tranche_age"
}

def remove_nan_fields(record: dict) -> dict:
    cleaned = {}
    for key, value in record.items():
        if value is None:
            continue
        if isinstance(value, str) and value.strip() == "":
            continue
        if isinstance(value, str) and value.strip().lower() == "nan":
            continue
        if isinstance(value, float) and math.isnan(value):
            continue
        try:
            if str(value).strip().lower() == "nan":
                continue
        except:
            pass
        if key not in DIMENSION_VALUES:
            try:
                if float(value) == 0:
                    continue
            except:
                pass
        cleaned[key] = value
    return cleaned

def convert_to_year(series):
    s = series.astype(str).str.strip()

    # 1) ESSAYER COMME DATE
    dt = pd.to_datetime(s, errors="coerce")
    years = dt.dt.year

    # Si au moins 30% sont valides → on considère que c'est une date
    if years.notna().mean() >= 0.3:
        return years.astype("Int64")

    # 2) SINON → TRAITER COMME NUMÉRIQUE
    nums = pd.to_numeric(
        s.str.replace(r"\s+", "", regex=True).str.replace(",", ".", regex=False),
        errors="coerce"
    )

    return nums.astype("Int64")


async def preprocess_data_pipeline_excels() -> AsyncGenerator[str, None]:

    db = get_mongo_client()
    es = get_elasticsearch()
     # 🔐 Vérifier que l’index Elasticsearch existe, sinon le créer
    """if not es.indices.exists(index=ES_INDEX):
        es.indices.create(
            index=ES_INDEX,
            body={
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0
                },
                "mappings": {
                    "properties": {
                        "year": {"type": "keyword"},
                        "milieu": {"type": "keyword"},
                        "region": {"type": "keyword"},
                        "categorie": {"type": "keyword"},
                        "genre": {"type": "keyword"},
                        "secteur": {"type": "keyword"},
                        "tranche_age": {"type": "keyword"},
                        "indicator": {"type": "keyword"},
                        "value": {"type": "double"},
                        "filename": {"type": "keyword"},
                        "dimensions": {"type": "keyword"},
                        "metadata": {"type": "object"}
                    }
                }
            }
        ) """
    collections = get_collections(db)

    yield "🚀 Début: prétraitement des fichiers Excels\n"

    now = datetime.utcnow()
    since = now - timedelta(hours=10)

    yield "📥 Chargement des fichiers Excels récents depuis MongoDB...\n"

    excel_files = []
    fs = collections["excels"]
    for f in db["excels.files"].find({"uploadDate": {"$gte": since}}):
        excel_files.append({
            "id": str(f["_id"]),
            "filename": f.get("filename", "unknown.xlsx"),
            "uploadDate": f.get("uploadDate"),
            "file_data": fs.get(f["_id"]).read()
        })

    yield f"📊 {len(excel_files)} fichiers Excels à traiter\n"

    DIMENSION_KEYS = {
        "annee": "Année",
        "milieu": "Milieu",
        "region": "Region",
        "categorie": "Categorie",
        "genre": "Genre",
        "secteur": "Secteur",
        "trancheage": "Tranche_age"
    }

    normalized_dimensions = {normalize_key(v): v for v in DIMENSION_KEYS.values()}

    for doc in excel_files:
        try:
            filename = doc.get("filename", "unknown.xlsx")
            content = doc.get("file_data")

            df = pd.read_excel(io.BytesIO(content))
            df.columns = [str(col).strip() for col in df.columns]

            # Corrigé : Année détectée même avec accents/variantes
            for c in df.columns:
                if "anne" in normalize_key(c):  
                     df[c] = convert_to_year(df[c])
                     
            colonnes_norm = [normalize_key(c) for c in df.columns]

            dimensions_detectees = [
                normalized_dimensions[key]
                for key in normalized_dimensions.keys()
                if key in colonnes_norm
            ]

            if not dimensions_detectees:
                dimensions_detectees = ["Année"]

            yield f"📊 Dimensions détectées: {dimensions_detectees} pour {filename}\n"

            records = df.to_dict(orient="records")
            records = [remove_nan_fields(r) for r in records]

            json_bytes = json.dumps(records, ensure_ascii=False, indent=2).encode("utf-8")

            collections["json"].put(
                json_bytes,
                filename=f"{os.path.splitext(filename)[0]}.json",
                created_at=datetime.utcnow(),
                source="excel",
                dimensions=dimensions_detectees,
                metadata={
                    "rows": len(records),
                    "filename": filename,
                    "ingest_date": datetime.utcnow().isoformat()
                }
            )

            # Extraction des indicateurs
            all_indicators = [
                col for col in df.columns
                if normalize_key(col) not in normalized_dimensions
            ]

            if all_indicators:
                indicators_json = json.dumps(sorted(set(all_indicators)), ensure_ascii=False, indent=2).encode("utf-8")
                collections["indicators"].put(
                    indicators_json,
                    filename=f"{os.path.splitext(filename)[0]}_indicators.json",
                    created_at=datetime.utcnow(),
                    source="excel",
                    metadata={
                        "total_indicators": len(all_indicators),
                        "filename": filename,
                        "ingest_date": datetime.utcnow().isoformat()
                    }
                )
                yield f"🧩 {len(all_indicators)} indicateurs détectés et sauvegardés pour {filename}\n"

            # ==============================================
            # 🔥 Correction principale : indexation correcte
            # ==============================================

            actions = []

            for row in records:

                year = get_value_case_insensitive(row, "Année") or get_value_case_insensitive(row, "Annee")
                milieu = get_value_case_insensitive(row, "Milieu")
                region = get_value_case_insensitive(row, "Région") or get_value_case_insensitive(row, "Region")
                categorie = get_value_case_insensitive(row, "Catégorie") or get_value_case_insensitive(row, "Categorie")
                genre = get_value_case_insensitive(row, "Genre")
                secteur = get_value_case_insensitive(row, "Secteur")
                tranche_age = get_value_case_insensitive(row, "Tranche_age")

                # IMPORTANT: boucle intérieur → indexation ligne par ligne
                for indicator, value in row.items():

                    # Correction : détecter les dimensions insensibles à la casse/accents
                    if normalize_key(indicator) in normalized_dimensions:
                        continue

                    actions.append({
                        "_index": ES_INDEX,
                        "_id": f"{filename}_{indicator}_{year}_{uuid4().hex}",
                        "_source": {
                            "year": year,
                            "milieu": milieu,
                            "region": region,
                            "categorie": categorie,
                            "genre": genre,
                            "secteur": secteur,
                            "tranche_age": tranche_age,
                            "indicator": indicator,
                            "value": clean_numeric_value(value),
                            "filename": filename,
                            "dimensions": dimensions_detectees,
                            "metadata": {
                                "row_data": row,  # ✔ visible dans Kibana
                                "ingest_date": datetime.utcnow().isoformat()
                            }
                        }
                    })

            if actions:
                helpers.bulk(es, actions)
                es.indices.refresh(index=ES_INDEX)
                yield f"🔍 {len(actions)} enregistrements indexés dans Elasticsearch depuis {filename}\n"

            yield f"✅ Excel traité et indexé → {filename} ({len(records)} lignes)\n"

        except Exception as e:
            yield f"❌ Erreur Excel {doc.get('filename')} : {e}\n"

    yield "🏁 Fin du pipeline Excel (prétraitement + indexation terminés)\n"

#================================== Preprocessing PDF + Build FAISS =============================================
async def preprocess_data_pipeline_pdf() -> AsyncGenerator[str, None]:
    FAISS_INDEX_PATH = "app/models/faiss_index"
    EMBEDDING_MODEL = "dangvantuan/sentence-camembert-base"

    db = get_mongo_client()
    collections = get_collections(db)

    yield "🚀 Début : prétraitement complet (PDF → TXT → FAISS)\n"

    # ---------------------------
    # Étape 1 — PDFs récents
    # ---------------------------
    now = datetime.utcnow()
    since = now - timedelta(hours=10)

    yield "📥 Recherche des PDF uploadés récemment...\n"

    fs_pdfs = gridfs.GridFS(db, collection="pdfs")
    fs_txt  = gridfs.GridFS(db, collection="training_data_txt")

    pdf_files = list(db["pdfs.files"].find({"uploadDate": {"$gte": since}}))
    yield f"📄 {len(pdf_files)} PDF trouvés\n"

    if not pdf_files:
        yield "⚠️ Aucun PDF trouvé. Passage direct à la construction FAISS...\n"
    else:
        yield "📚 Début extraction du texte...\n"

        # ---------------------------
        # Étape 2 — Extraction PDF → TXT
        # ---------------------------
        for pdf_info in pdf_files:
            file_id = pdf_info["_id"]
            filename = pdf_info.get("filename", "unknown.pdf")
            filedata = fs_pdfs.get(file_id).read()

            yield f"➡️ Traitement : {filename}\n"

            try:
                reader = PdfReader(io.BytesIO(filedata))
                full_text = ""

                for i, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if text:
                        text = re.sub(r"\s+", " ", text).strip()
                        full_text += text + "\n"

                    if i % 3 == 0:
                        yield f"   📝 Pages analysées : {i+1}/{len(reader.pages)}\n"

                metadata = reader.metadata or {}
                meta_clean = {
                    "Author": metadata.get("/Author", ""),
                    "pages_count": len(reader.pages),
                    "original_filename": filename,
                    "processing_date": datetime.utcnow().isoformat(),
                }

                metadata_str = "\n".join([f"{k}: {v}" for k, v in meta_clean.items()])
                final_txt = metadata_str + "\n\n" + full_text

                fs_txt.put(
                    final_txt.encode("utf-8"),
                    filename=filename.replace(".pdf", ".txt"),
                    **meta_clean,
                    uploadDate=datetime.utcnow(),
                )

                yield f"✅ PDF traité et stocké : {filename}\n"

            except Exception as e:
                yield f"❌ Erreur sur {filename} : {str(e)}\n"

        yield "🎉 Fin du preprocessing PDF.\n"

    # =====================================================================================
    # ===         PARTIE 2 : Chargement TXT + Construction FAISS                         ===
    # =====================================================================================

    yield "📥 Chargement des fichiers TXT depuis MongoDB...\n"

    fs_txt = gridfs.GridFS(db, collection="training_data_txt")
    txt_files = []

    for file_info in db["training_data_txt.files"].find():
        fid = file_info["_id"]
        fname = file_info.get("filename", "unknown.txt")
        content = fs_txt.get(fid).read().decode("utf-8", errors="ignore")

        txt_files.append({"filename": fname, "content": content})

    yield f"📄 {len(txt_files)} fichiers TXT trouvés.\n"

    # ---------------------------
    # Chunking
    # ---------------------------
    yield "🪓 Découpage en chunks...\n"

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
        length_function=len
    )

    chunks = []
    metadatas = []

    for i, file in enumerate(txt_files):
        filename = file["filename"]
        text = file["content"].strip()

        if not text:
            yield f"⚠️ Fichier TXT vide ignoré : {filename}\n"
            continue

        item_chunks = text_splitter.split_text(text)
        chunks.extend(item_chunks)

        match = re.search(r"(\d{4})", filename)
        year = match.group(1) if match else "N/A"

        for _ in item_chunks:
            metadatas.append({"source": filename, "Année": year, "page": "N/A"})

        if i % 3 == 0:
            yield f"📦 Chunks générés : {len(chunks)}...\n"

    yield f"📦 Total final chunks : {len(chunks)}\n"

    # ---------------------------
    # Embeddings
    # ---------------------------
    yield "🧠 Chargement du modèle embeddings ... \n"
    hf_embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    yield "✅ Chargement du modèle embeddings terminée\n"
    # =====================================================================================
    # ===                ⚡ Nouvelle version : Construction FAISS                        ===
    # =====================================================================================

    def format_duration(seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def build_faiss_async(result):
        result["vectorstore"] = FAISS.from_texts(
            chunks,
            embedding=hf_embeddings,
            metadatas=metadatas
        )
    yield "******************** Construction de l’index FAISS ********************\n"

    start_time = time.time()
    result = {"vectorstore": None}

    t = threading.Thread(target=build_faiss_async, args=(result,), daemon=True)
    t.start()

    while t.is_alive():
        elapsed = format_duration(time.time() - start_time)
        yield f"⏳ Construction FAISS en cours... {elapsed}\n"
        await asyncio.sleep(1)

    vectorstore = result["vectorstore"]
    total = format_duration(time.time() - start_time)
    yield f"✅ Construction FAISS terminée en {total}\n"
    # ---------------------------
    # Sauvegarde FAISS
    # ---------------------------
    os.makedirs(FAISS_INDEX_PATH, exist_ok=True)
    vectorstore.save_local(FAISS_INDEX_PATH)
    yield f"🎉 Index FAISS sauvegardé dans : {FAISS_INDEX_PATH}\n"
    yield "✅ Pipeline complet terminé.\n"
    



'''import os
import io
import re
import json
import math
import pandas as pd
import requests
import html2text
import gridfs
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from deep_translator import GoogleTranslator
from fastapi import UploadFile
from pymongo.database import Database
from app.db import get_mongo_client, get_elasticsearch
from app.core.config import ES_INDEX
from elasticsearch import helpers
from PyPDF2 import PdfReader
from typing import AsyncGenerator
import unicodedata

# =====================
# 🔧 Fonctions utilitaires
# =====================
def get_collections(db: Database):
    return {
        "pdfs": gridfs.GridFS(db, collection="pdfs"),
        "excels": gridfs.GridFS(db, collection="excels"),
        "urls": db["urls_scraping"],
        "txt": gridfs.GridFS(db, collection="training_data_txt"),
        "json": gridfs.GridFS(db, collection="training_data_json"),
    }

def clean_text(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9\s.,;:%\-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def translate_to_french(text: str, source_lang='auto') -> str:
    try:
        translator = GoogleTranslator(source=source_lang, target='fr')
        return translator.translate(text)
    except Exception:
        return text

def clean_value(val):
    if val is None:
        return None
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return None
    return val

def clean_dict(d):
    cleaned = {}
    for k, v in d.items():
        if isinstance(v, dict):
            cleaned[k] = clean_dict(v)
        elif isinstance(v, list):
            cleaned[k] = [clean_value(x) if not isinstance(x, dict) else clean_dict(x) for x in v]
        else:
            cleaned[k] = clean_value(v)
    return cleaned

def clean_numeric_value(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if isinstance(value, str):
        cleaned_value_str = value.replace("\u202f", "").replace(",", ".")
        try:
            return float(cleaned_value_str)
        except (ValueError, TypeError):
            return None
    return None

# =====================
# 🧩 Pipeline de preprocessing Excel
# =====================
async def preprocess_data_pipeline_excels() -> AsyncGenerator[str, None]:
    db = get_mongo_client()
    es = get_elasticsearch()
    collections = get_collections(db)

    yield "🚀 Début: prétraitement des fichiers Excels\n"

    now = datetime.utcnow()
    since = now - timedelta(hours=12)
    yield "📥 Chargement des fichiers Excels récents depuis MongoDB...\n"

    # 🔹 Récupération fichiers Excel récents depuis GridFS (uploadDate)
    excel_files = []
    fs = collections["excels"]
    for f in db["excels.files"].find({"uploadDate": {"$gte": since}}):
        excel_files.append({
            "id": str(f["_id"]),
            "filename": f.get("filename", "unknown.xlsx"),
            "uploadDate": f.get("uploadDate"),
            "file_data": fs.get(f["_id"]).read()
        })
    yield f"📊 {len(excel_files)} fichiers Excels à traiter\n"

    def normalize_key(key: str) -> str:
        if not isinstance(key, str):
            return key
        key = unicodedata.normalize("NFKD", key).encode("ascii", "ignore").decode("utf-8")
        key = re.sub(r"[^a-z0-9]+", "_", key.lower()).strip("_")
        return key

    DIMENSION_KEYS = {
        "annee": "Année",
        "milieu": "Milieu",
        "region": "Region",
        "categorie": "Categorie",
        "genre": "Genre",
        "secteur": "Secteur",
        "tranche_age": "Tranche_age"
    }

    DIMENSIONS = [
        ["Année"],
        ["Année", "Milieu"],
        ["Année", "Milieu", "Region", "Categorie"],
        ["Année", "Secteur"],
        ["Année", "Region", "Categorie"],
        ["Année", "Genre", "Milieu", "Categorie"],
        ["Année", "Milieu", "Tranche_age", "Genre"]
    ]

    # --- Traitement Excel ---
    for doc in excel_files:
        try:
            content = doc.get("file_data")
            filename = doc.get("filename", "unknown.xlsx")
            df = pd.read_excel(io.BytesIO(content))

            df.columns = [str(col).strip() for col in df.columns]
            if "Année" in df.columns or "Annee" in df.columns:
                col_annee = "Année" if "Année" in df.columns else "Annee"
                df[col_annee] = pd.to_datetime(df[col_annee], errors='coerce').dt.year.astype("Int64")

            # ✅ Nouvelle détection flexible des dimensions
            colonnes_norm = [normalize_key(c) for c in df.columns]
            possible_dims = list(DIMENSION_KEYS.keys())

            dimensions_detectees = [
                DIMENSION_KEYS[key]
                for key in possible_dims
                if key in colonnes_norm
            ]

            if not dimensions_detectees:
                dimensions_detectees = ["Année"]

            yield f"📊 Dimensions détectées: {dimensions_detectees} pour {filename}\n"

            records = df.to_dict(orient="records")
            json_bytes = json.dumps(records, ensure_ascii=False, indent=2).encode("utf-8")

            # 💾 Sauvegarde JSON dans MongoDB
            collections["json"].put(
                json_bytes,
                filename=f"{os.path.splitext(filename)[0]}.json",
                created_at=datetime.utcnow(),
                source="excel",
                dimensions=dimensions_detectees,
                metadata={
                    "rows": len(records),
                    "filename": filename,
                    "ingest_date": datetime.utcnow().isoformat()
                }
            )

            # 📦 Indexation Elasticsearch
            actions = []
            for row in records:
                row = clean_dict(row)
                normalized_row = {normalize_key(k): v for k, v in row.items()}
                source_doc = {}
                for norm_key, standard_name in DIMENSION_KEYS.items():
                    value = normalized_row.get(norm_key)
                    if value not in [None, "", "NaN"]:
                        source_doc[standard_name] = value

                for col, val in row.items():
                    norm_col = normalize_key(col)
                    if norm_col not in DIMENSION_KEYS and norm_col not in ["annee"]:
                        doc_source = {
                            **{k: v for k, v in source_doc.items() if v not in [None, ""]},
                            "Indicateur": col.strip(),
                            "Valeur": clean_numeric_value(val),
                            "_meta": {
                                "filename": filename,
                                "dimensions": dimensions_detectees,
                                "indexed_at": datetime.utcnow().isoformat(),
                                "source_type": "excel",
                            }
                        }
                        doc_source = clean_dict(doc_source)
                        actions.append({
                            "_index": ES_INDEX,
                            "_id": f"{filename}_{col}_{source_doc.get('Année', 'NA')}",
                            "_source": doc_source
                        })

            if actions:
                helpers.bulk(es, actions)
                es.indices.refresh(index=ES_INDEX)
                yield f"🔍 {len(actions)} enregistrements indexés dans Elasticsearch depuis {filename}\n"

            yield f"✅ Excel traité et indexé → {filename} ({len(records)} lignes)\n"

        except Exception as e:
            yield f"❌ Erreur Excel {doc.get('filename')} : {e}\n"

    yield "🏁 Fin du pipeline Excel (prétraitement + indexation terminés)\n"
'''