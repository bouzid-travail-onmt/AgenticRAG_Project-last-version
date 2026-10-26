import math
from elasticsearch import helpers
from app.db import get_mongo_client, get_elasticsearch
from app.core.config import ES_INDEX

# ----------- Helpers pour nettoyer -----------
def clean_value(val):
    if val is None:
        return None
    if isinstance(val, float):
        if math.isnan(val) or math.isinf(val):
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

# ----------- Indexation JSON seulement -----------
def index_json_files():
    mongo = get_mongo_client()
    es = get_elasticsearch()

    json_collection = mongo["json_files"]
    actions = []

    for doc in json_collection.find():
        data = doc.get("content", {})
        filename = doc.get("filename")

        # ---------- Cas dict ----------
        if isinstance(data, dict):
            data = clean_dict(data)
            year = data.get("Année") or data.get("Annee")
            milieu = data.get("Milieu", "National")

            for indicator, value in data.items():
                if indicator in ["Année", "Annee", "Milieu"]:
                    continue
                actions.append({
                    "_index": ES_INDEX,
                    "_id": f"{filename}_{indicator}_{year}_{milieu}",
                    "_source": {
                        "year": year,
                        "milieu": milieu,
                        "indicator": indicator,
                        "value": clean_numeric_value(value),
                        "filename": filename,
                        "type": "structured"
                    }
                })

        # ---------- Cas liste ----------
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    item = clean_dict(item)
                    year = item.get("Année") or item.get("Annee")
                    milieu = item.get("Milieu", "National")

                    for indicator, value in item.items():
                        if indicator in ["Année", "Annee", "Milieu"]:
                            continue
                        actions.append({
                            "_index": ES_INDEX,
                            "_id": f"{filename}_{indicator}_{year}_{milieu}",
                            "_source": {
                                "year": year,
                                "milieu": milieu,
                                "indicator": indicator,
                                "value": clean_numeric_value(value),
                                "filename": filename,
                                "type": "structured"
                            }
                        })

    # Indexer dans ES
    if actions:
        helpers.bulk(es, actions)
        es.indices.refresh(index=ES_INDEX)

    return {"indexed_json_docs": len(actions), "index": ES_INDEX}
