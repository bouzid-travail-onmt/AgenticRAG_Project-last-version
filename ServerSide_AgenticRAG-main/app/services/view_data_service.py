# app/services/view_data_service.py
from bson import ObjectId
from urllib.parse import urlparse
from typing import Optional
from app.db import get_mongo_client,get_elasticsearch
import os
import gridfs
from datetime import datetime, timedelta
from app.core.config import ES_INDEX
db = get_mongo_client()
ES = get_elasticsearch()
# ------------------------------------------------------------
# COLLECTIONS
# ------------------------------------------------------------
COLLECTIONS = {
    "pdf": "pdfs.files",
    "excel": "excels.files",
    "urls": "urls_scraping",
    "txt": "training_data_txt.files",
    "json": "training_data_json.files",
    "indicators": "training_data_indicators.files",  # ✅ ajout cohérent
}

# ------------------------------------------------------------
# GRIDFS MAPPING
# ------------------------------------------------------------
FS_MAP = {
    "pdf": gridfs.GridFS(db, collection="pdfs"),
    "excel": gridfs.GridFS(db, collection="excels"),
    "txt": gridfs.GridFS(db, collection="training_data_txt"),
    "json": gridfs.GridFS(db, collection="training_data_json"),
    "indicators": gridfs.GridFS(db, collection="training_data_indicators"),  # ✅ cohérence
}

# ------------------------------------------------------------
# ✅ RÉCUPÉRER LES INDICATEURS STOCKÉS DANS GridFS
# ------------------------------------------------------------
def fetch_indicator_from_db():
    """
    Récupère la liste des indicateurs stockés dans la collection GridFS 'training_data_indicators'.
    Retourne un tableau de métadonnées similaires à fetch_files_from_db().
    """
    files = []
    try:
        collection_name = COLLECTIONS["indicators"]
        for f in db[collection_name].find():
            info = {
                "id": str(f["_id"]),
                "type": "indicators",
                "name": f.get("filename", "fichier_sans_nom"),
                "createdAt": str(f.get("uploadDate", datetime.utcnow())),
                "size": f.get("length", 0),
                "metadata": f.get("metadata", {}),
            }
            files.append(info)

    except Exception as e:
        print(f"[ERROR] Impossible de récupérer les indicateurs : {e}")
        return []

    return files

def delete_indicator_from_db(file_id: str):
    try:
        fs = FS_MAP["indicators"]
        fs.delete(ObjectId(file_id))
        return True
    except Exception as e:
        print("[ERROR] Delete indicator:", e)
        return False
# ------------------------------------------------------------
# UTILITAIRES
# ------------------------------------------------------------
def safe_object_id(value):
    try:
        return ObjectId(value)
    except Exception:
        return value

# ------------------------------------------------------------
# LISTER LES FICHIERS (GridFS + Mongo)
# ------------------------------------------------------------
def fetch_files_from_db(file_type: str):
    if file_type not in COLLECTIONS:
        raise ValueError("Type de fichier invalide")

    files = []

    # 🔹 Cas GridFS
    if file_type in FS_MAP:
        fs = FS_MAP[file_type]
        for f in db[COLLECTIONS[file_type]].find():
            info = {
                "id": str(f["_id"]),
                "type": file_type,
                "name": f.get("filename", "fichier_sans_nom"),
                "createdAt": str(f.get("uploadDate", datetime.utcnow())),
                "size": f.get("length", 0),
                "metadata": {},
            }
            files.append(info)
        return files

    # 🔹 Cas classique (URLs)
    collection = db[COLLECTIONS[file_type]]
    for f in collection.find():
        name = f.get("filename") or "inconnu"

        if file_type == "urls" and f.get("url"):
            try:
                parsed = urlparse(f["url"])
                name = parsed.netloc or f["url"]
            except Exception:
                name = "URL invalide"

        created_at = f.get("uploadDate") or f.get("created_at") or datetime.utcnow()
        size = f.get("length") or len(str(f.get("content", "")))

        info = {
            "id": str(f["_id"]),
            "type": file_type,
            "name": name,
            "createdAt": str(created_at),
            "size": size,
            "metadata": {},
        }

        if file_type == "urls":
            info["metadata"]["url"] = f.get("url")

        files.append(info)

    return files


# 🆕 ================================================================
# ✅ NOUVELLE METHODE : Récupère uniquement les fichiers ajoutés 
#    dans les dernières `hours` heures (par défaut : 10h)
# ==================================================================
def fetch_recent_files_from_db(file_type: str, hours: int = 10):
    if file_type not in COLLECTIONS:
        raise ValueError("Type de fichier invalide")

    files = []
    time_threshold = datetime.utcnow() - timedelta(hours=hours)

    # 🔹 Cas GridFS
    if file_type in FS_MAP:
        fs = FS_MAP[file_type]
        for f in db[COLLECTIONS[file_type]].find({"uploadDate": {"$gte": time_threshold}}):
            info = {
                "id": str(f["_id"]),
                "type": file_type,
                "name": f.get("filename", "fichier_sans_nom"),
                "createdAt": str(f.get("uploadDate", datetime.utcnow())),
                "size": f.get("length", 0),
                "metadata": {},
            }
            files.append(info)
        return files

    # 🔹 Cas classique (URLs ou autres)
    collection = db[COLLECTIONS[file_type]]
    query = {
        "$or": [
            {"uploadDate": {"$gte": time_threshold}},
            {"created_at": {"$gte": time_threshold}}
        ]
    }

    for f in collection.find(query):
        name = f.get("filename") or "inconnu"

        if file_type == "urls" and f.get("url"):
            try:
                parsed = urlparse(f["url"])
                name = parsed.netloc or f["url"]
            except Exception:
                name = "URL invalide"

        created_at = f.get("uploadDate") or f.get("created_at") or datetime.utcnow()
        size = f.get("length") or len(str(f.get("content", "")))

        info = {
            "id": str(f["_id"]),
            "type": file_type,
            "name": name,
            "createdAt": str(created_at),
            "size": size,
            "metadata": {},
        }

        if file_type == "urls":
            info["metadata"]["url"] = f.get("url")

        files.append(info)

    return files
# ------------------------------------------------------------
# SUPPRIMER UN FICHIER
# ------------------------------------------------------------
def delete_file_from_db(file_id: str, type: Optional[str] = None) -> bool:
    if type in FS_MAP:
        try:
            FS_MAP[type].delete(ObjectId(file_id))
            return True
        except Exception:
            pass

    if type in COLLECTIONS and type not in FS_MAP:
        coll = db[COLLECTIONS[type]]
        id_value = safe_object_id(file_id)
        doc = coll.find_one({"_id": id_value})
        if not doc:
            return False

        if doc.get("path") and os.path.exists(doc["path"]):
            try:
                os.remove(doc["path"])
            except Exception:
                pass

        res = coll.delete_one({"_id": id_value})
        return bool(res.deleted_count)

    for coll_name in COLLECTIONS.values():
        coll = db[coll_name]
        id_value = safe_object_id(file_id)
        doc = coll.find_one({"_id": id_value})
        if doc:
            coll.delete_one({"_id": id_value})
            return True

    return False



# ----------------------------Cet feature de supprimer toutes les fichiers de type json,txt,pdf,excel,indicators-----------------------------------------
# SUPPRIMER TOUS LES FICHIERS D'UN TYPE DONNÉ



from typing import Optional
import gridfs 
def delete_all_files_service(file_type: Optional[str] = None) -> dict:
    '''
    🗑️ DROP complet selon le type
    - GridFS : drop files + chunks
    - Collections classiques : drop collection
    '''

    if not file_type:
        raise ValueError("file_type est obligatoire")

    file_type = file_type.strip().lower()

    if file_type not in COLLECTIONS:
        raise ValueError(f"Type invalide : {file_type}")

    # ======================================================
    # 🔥 CAS GRIDFS (pdf, excel, txt, json, indicators)
    # ======================================================
    if file_type in FS_MAP:
        fs = FS_MAP[file_type]

        files_coll = fs._GridFS__files
        chunks_coll = fs._GridFS__chunks

        try:
            deleted_count = files_coll.count_documents({})

            # 🔥 DROP réel (schema + data)
            files_coll.drop()
            chunks_coll.drop()

            return {
                "status": "success",
                "type": file_type,
                "deleted": deleted_count,
            }

        except Exception as e:
            raise RuntimeError(f"GridFS DROP failed ({file_type}): {e}")

    # ======================================================
    # 🔥 CAS COLLECTION CLASSIQUE (urls)
    # ======================================================
    coll_name = COLLECTIONS[file_type]
    coll = db[coll_name]

    try:
        deleted_count = coll.count_documents({})

        # 🔥 DROP collection
        coll.drop()

        return {
            "status": "success",
            "type": file_type,
            "deleted": deleted_count,
        }

    except Exception as e:
        raise RuntimeError(f"Mongo DROP failed ({file_type}): {e}")



#------------------------------------------------------------------------------------------------------------------------------------------------























# ------------------------------------------------------------
# RÉCUPÉRER UN DOCUMENT (URLs)
# ------------------------------------------------------------
def get_file_document(file_id: str):
    oid = safe_object_id(file_id)
    for coll_name in COLLECTIONS.values():
        coll = db[coll_name]
        doc = coll.find_one({"_id": oid})
        if doc:
            return doc
    return None

# ------------------------------------------------------------
# RÉCUPÉRER UN FICHIER GRIDFS (pdf/excel/txt/json)
# ------------------------------------------------------------
def get_gridfs_file(file_type: str, file_id: str):
    if file_type not in FS_MAP:
        return None
    try:
        return FS_MAP[file_type].get(ObjectId(file_id))
    except Exception:
        return None
   
# ------------------------------------------------------------
# ElasticSearch Management
# 🔍 Lister + Filtrer
def list_documents_service(indicator=None, year=None, filename=None, page=1, page_size=100):
    query = {"match_all": {}}
    must = []

    if indicator:
        must.append({"match_phrase": {"indicator": indicator}})

    if year:
        must.append({"term": {"year": year}})

    if filename:
        must.append({"match_phrase": {"filename": filename}})

    if must:
        query = {"bool": {"must": must}}

    # 👉 Pagination
    start = (page - 1) * page_size 

    res = ES.search(
        index=ES_INDEX,
        query=query,
        size=page_size,   # nombre d’items par page
        from_=start       # offset
    )

    items = [
        {
            "_id": hit["_id"],
            **hit["_source"],
        }
        for hit in res["hits"]["hits"]
    ]

    return {
        "total": res["hits"]["total"]["value"],
        "page": page,
        "page_size": page_size,
        "items": items,
    }


# ❌ Supprimer un document
def delete_document_service(doc_id: str):
    ES.delete(index=ES_INDEX, id=doc_id)
    return {"status": "deleted", "id": doc_id}


# 🔥 Supprimer tous les documents
def delete_all_documents_service():
    ES.delete_by_query(index=ES_INDEX, body={"query": {"match_all": {}}})
    return {"status": "all_deleted"}
# ------------------------------------------------------------

