'''import re
import unicodedata
from elasticsearch import Elasticsearch
from app.db import get_elasticsearch
 
# =========================
# Connexion à Elasticsearch
# =========================
es = get_elasticsearch()
TOP_K_ES = 50  # nombre de résultats à retourner

# =========================
# Utilitaires de nettoyage
# =========================
def normalize(text: str) -> str:
    """Nettoyer et normaliser le texte."""
    if not isinstance(text, str):
        return ""
    t = text.lower()
    t = "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^a-z0-9%/\s\-']", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def extract_year(query: str) -> str | None:
    """Extraire une année depuis la question."""
    m = re.search(r"\b(19|20)\d{2}\b", query)
    if m:
        return m.group(0)
    return None

def get_latest_year(index: str) -> str | None:
    """Retourner la plus grande année indexée si aucune année n'est mentionnée."""
    res = es.search(
        index=index,
        body={
            "size": 0,
            "aggs": {"max_year": {"max": {"field": "Année"}}}
        }
    )
    max_year = res.get("aggregations", {}).get("max_year", {}).get("value")
    if max_year:
        return str(int(max_year))
    return None

# =========================
# Construction de la requête Elasticsearch
# =========================
def build_es_query_from_free_text(query: str, index: str) -> dict:
    """Construire une requête ES pour toutes les dimensions textuelles avec gestion de l'année."""
    normalized_query = normalize(query)
    year = extract_year(query)
    if not year:
        year = get_latest_year(index)

    must_clauses = []

    # --- Clause année obligatoire ---
    if year:
        must_clauses.append({"term": {"Année": str(year)}})

    # --- Multi_match uniquement sur champs textuels (éviter les float) ---
    must_clauses.append({
        "multi_match": {
            "query": normalized_query,
            "fields": [
                "Indicateur^3",
                "Milieu",
                "Region",
                "Categorie",
                "Genre",
                "Secteur",
                "Tranche_age",
                "_meta.filename",
                "_meta.dimensions"
            ],
            "fuzziness": "AUTO"
        }
    })

    return {
        "query": {
            "bool": {
                "must": must_clauses,
                "minimum_should_match": 1
            }
        },
        "sort": [{"_score": "desc"}]
    }

# =========================
# Recherche principale
# =========================
def search_in_elasticsearch(index: str, query: str, top_k: int = TOP_K_ES):
    """Exécuter la recherche et retourner les résultats formatés."""
    es_query = build_es_query_from_free_text(query, index)
    res = es.search(index=index, body=es_query, size=top_k)

    results = []
    for hit in res["hits"]["hits"]:
        src = hit["_source"]
        results.append({
            "Indicateur": src.get("Indicateur", "N/A"),
            "Valeur": src.get("Valeur", "N/A"),  # float OK ici, pas de fuzzy
            "Année": src.get("Année", "N/A"),
            "Milieu": src.get("Milieu", "N/A"),
            "Region": src.get("Region", "N/A"),
            "Categorie": src.get("Categorie", "N/A"),
            "Secteur": src.get("Secteur", "N/A"),
            "Genre": src.get("Genre", "N/A"),
            "Tranche_age": src.get("Tranche_age", "N/A"),
            "Score": round(hit["_score"], 3)
        })
    return results
'''


'''
import re
import unicodedata
from elasticsearch import Elasticsearch
from app.db import get_elasticsearch

# =========================
# Connexion à Elasticsearch
# =========================
es = get_elasticsearch()  # récupération de ton client existant
TOP_K_ES = 50             # nombre de résultats à retourner pour tester 

# Exemple de dictionnaire (à compléter selon ton projet)
INDICATOR_SYNONYMS = {}

def normalize(text: str) -> str:
    """Nettoyer et normaliser le texte."""
    t = text.lower()
    t = "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^a-z0-9%/\s\-']", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def extract_year(query: str) -> str | None:
    """Extraire l'année depuis une requête."""
    m = re.search(r"\b(19|20)\d{2}\b", query)
    if m:
        return m.group(0)
    m = re.search(r"\b(\d{1,2}/\d{1,2})/(\d{2}|\d{4})\b", query)
    if m:
        yy = m.group(2)
        return ("20" + yy) if len(yy) == 2 else yy
    return None

def detect_indicator(query: str) -> str | None:
    """Détecter l'indicateur (ex: chômage, population)."""
    qn = normalize(query)
    candidates = []
    for canonical, patterns in INDICATOR_SYNONYMS.items():
        for pat in patterns:
            if re.search(rf"\b{pat}\b", qn):
                candidates.append((canonical, pat, len(pat)))
                break
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[2], reverse=True)
    return candidates[0][0]

def detect_milieu(query: str) -> str:
    """Détecter le milieu (urbain/rural/national), par défaut 'National'."""
    qn = normalize(query)
    if "urbain" in qn:
        return "Urbain"
    elif "rural" in qn:
        return "Rural"
    elif "national" in qn:
        return "National"
    return "National"   # ✅ fallback par défaut

def build_es_query_from_free_text(query: str) -> dict:
    """Construire la requête ES à partir d'un texte libre."""
    indicator = detect_indicator(query)
    year = extract_year(query)
    milieu = detect_milieu(query) or "National"   # <= si None, alors "National"
    must_clauses = []
    if indicator:
        must_clauses.append({"match_phrase": {"indicator": indicator}})
    if year:
        must_clauses.append({"term": {"year": str(year)}})
    if milieu:
        must_clauses.append({"match_phrase": {"milieu": milieu}})

    if not must_clauses:
        # fallback full-text
        return {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["indicator^2", "value", "milieu", "content"],
                    "fuzziness": "AUTO"
                }
            }
        }

    return {"query": {"bool": {"must": must_clauses}}}


def search_in_elasticsearch(index: str, query: str, top_k: int = TOP_K_ES):
    """Exécuter une recherche dans Elasticsearch et retourner les résultats formatés."""
    es_query = build_es_query_from_free_text(query)
    res = es.search(index=index, body=es_query, size=top_k)

    results = []
    for hit in res["hits"]["hits"]:
        src = hit["_source"]
        results.append({
            "source": src.get("source", "N/A"),
            "indicator": src.get("indicator", "N/A"),
            "value": src.get("value", "N/A"),
            "year": src.get("year", "N/A"),
            "milieu": src.get("milieu", "N/A")
        })
    return results
'''

# ========================================================================
# 📌 Handling the request based on Rule-based system for Elasticsearch
# ========================================================================

import re
import unicodedata
from datetime import datetime
from elasticsearch import Elasticsearch
from fastapi import HTTPException
import json
import gridfs
from threading import Lock
from typing import Optional
from app.db import get_elasticsearch, get_mongo_client
from difflib import SequenceMatcher   # <--- NEW : matching sémantique
import math

# =========================
# ⚙️ Connexion à Elasticsearch
# =========================
es = get_elasticsearch()
TOP_K_ES = 12  # Nombre de résultats à retourner

# ======================================================================
# 🧼 NORMALISATION ULTRA-RENFORCÉE
# ======================================================================
import re
import unicodedata

def normalize(text: str) -> str:
    """
    Normalisation légère pour maximiser la similarité syntaxique :
    - lowercase
    - remove accents
    - remove punctuation except (% / - ')
    - keep stopwords
    - remove duplicated spaces
    """
    if not text:
        return ""

    # 1️⃣ Minuscule
    text = text.lower()

    # 2️⃣ Suppression des accents
    text = "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )

    # 3️⃣ Autoriser uniquement :
    #    - lettres
    #    - chiffres
    #    - % / - '
    #    - espaces
    text = re.sub(r"[^a-z0-9%/\s\-']", " ", text)

    # 4️⃣ Compactage des espaces
    text = re.sub(r"\s+", " ", text).strip()

    return text
# ======================================================================
# 📅 Extraction robuste de l’année
# ======================================================================
def extract_year(query: str) -> str | None:
    """Extraction très robuste des années"""
    if not query:
        return None

    # Format classique
    m = re.search(r"\b(19|20)\d{2}\b", query)
    if m:
        return m.group(0)

    # Format jj/mm/yy
    m = re.search(r"\b(\d{1,2}/\d{1,2})/(\d{2}|\d{4})\b", query)
    if m:
        yy = m.group(2)
        return "20" + yy if len(yy) == 2 else yy

    return None


def get_latest_year(index: str) -> str:
    """Retourne l'année max de tout l'index (tous fichiers inclus)."""
    try:
        res = es.search(
            index=f"{index}*",
            body={"size": 0, "aggs": {"max_year": {"max": {"field": "year"}}}},
        )
        value = res["aggregations"]["max_year"]["value"]
        return str(int(value)) if value else str(datetime.now().year)
    except:
        return str(datetime.now().year)


# ======================================================================
# 🧠 DÉTECTION SÉMANTIQUE D’INDICATEURS (BOOSTÉE)
# ======================================================================
_INDICATORS_CACHE = None
_CACHE_LOCK = Lock()

def load_indicators_data():
    """Chargement des indicateurs depuis GridFS"""
    try:
        db = get_mongo_client()
        fs_indicators = gridfs.GridFS(db, collection="training_data_indicators")
        all_items = []

        for f in db["training_data_indicators.files"].find():
            file_id = f["_id"]

            try:
                file_data = fs_indicators.get(file_id).read().decode("utf-8")
                json_content = json.loads(file_data)
                if isinstance(json_content, dict):
                    items = json_content.get("indicators") or list(json_content.values())
                else:
                    items = json_content
                all_items.extend(items)

            except:
                continue

        return all_items

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du chargement : {e}"
        )

def semantic_similarity(a: str, b: str) -> float:
    """Score de similarité sémantique"""
    return SequenceMatcher(None, a, b).ratio()

def detect_indicator(query: str) -> Optional[str]:
    """Détection ultra fuzzy + sémantique + matching exact"""
    global _INDICATORS_CACHE

    if _INDICATORS_CACHE is None:
        with _CACHE_LOCK:
            if _INDICATORS_CACHE is None:
                raw_list = load_indicators_data()
                _INDICATORS_CACHE = set(normalize(ind) for ind in raw_list)

    nq = normalize(query)
    best_match = None
    best_score = -1

    for ind in _INDICATORS_CACHE:
        score = 0

        # 🟢 Matching exact dans la phrase
        if ind in nq:
            score += 3.0

        # 🟢 Matching mot à mot
        if re.search(rf"\b{re.escape(ind)}\b", nq):
            score += 5.0

        # 🟢 Similarité sémantique (NOUVEAU)
        score += semantic_similarity(nq, ind) * 10

        if score > best_score:
            best_score = score
            best_match = ind

    return best_match


# ======================================================================
# 🎯 Détection des autres dimensions (boostée + normalisation)
# ======================================================================
def detect_milieu(query: str) -> str:
    t = normalize(query)
    if "urbain" in t:
        return "Urbain"
    if "rural" in t:
        return "Rural"
    if "national" in t:
        return "National"
    return "Nan"

def detect_genre(query: str) -> str | None:
    t = normalize(query)
    if "homme" in t:
        return "Homme"
    if "femme" in t:
        return "Femme"
    return None

def detect_category(query: str, categories=["A", "B", "C"]) -> str | None:
    t = normalize(query)
    for cat in categories:
        if re.search(rf"\b{cat.lower()}\b", t):
            return cat
    return None

def detect_secteur(query: str) -> str | None:
    t = normalize(query)
    secteurs = {
    "Agriculture, forêt et pêche": ["Agriculture, forêt et pêche", "peche", "foret", "pêche"],
    "BTP": ["btp", "construction", "batiment", "bâtiment"],
    "Commerce": ["commerce", "vente", "magasin"],
    "Enseignement": ["enseignement", "education", "éducation", "professeur"],
    "Hébergement et restauration": ["Hébergement et restauration", "hébergement", "restauration", "hotel", "hôtel", "restaurant"],
    "Industries": ["industries", "industriel", "manufacture"],
    "Santé humaine et action sociale": ["Santé humaine et action sociale", "santé", "social", "hopital", "hôpital"],
    "Services": ["services", "services", "banque", "assurance"],
    "Transport": ["transport", "logistique", "transportation"],
    "Non déterminé": ["Non déterminé", "autre", "unknown", "nd"]
}
    for label, keys in secteurs.items():
        if any(k in t for k in keys):
            return label
    return None

def detect_tranche_age(query: str) -> str | None:
    t = normalize(query)
    tranches = {
        "15-24 ans": [r"15[ -]?24"],
        "25-34 ans": [r"25[ -]?34"],
        "35-44 ans": [r"35[ -]?44"],
        "45 ans et plus": ["45+", "plus de 45"],
    }
    for name, p_list in tranches.items():
        for p in p_list:
            if re.search(p, t):
                return name
    return None

# ======================================================================
# 🔎 Recherche ultra robuste dans tout ES (tous fichiers)
# ======================================================================
def search_in_elasticsearch(index: str, query: str, top_k: int = TOP_K_ES):
    """
    Recherche améliorée :
    - multi_match intelligent
    - fuzzy auto
    - recherche sur TOUS fichiers (index=data_index)
    """

    TEXT_FIELDS = [
        "indicator", "indicator.keyword",
        "milieu", "region", "categorie",
        "secteur", "genre", "tranche_age",
        "dimensions", "filename"
    ]

    normalized_query = normalize(query)
    must_queries = []

    # *******************************
    # 1️⃣ Fuzzy multi-match global
    # *******************************
    must_queries.append({
        "multi_match": {
            "query": normalized_query,
            "fields": TEXT_FIELDS,
            "type": "best_fields",
            "fuzziness": "AUTO"
        }
    })

    # *******************************
    # 2️⃣ Year exact (jamais fuzzy)
    # *******************************
    year = extract_year(query)
    if year:
        must_queries.append({"term": {"year": int(year)}})

    es_query = {
        "query": {
            "bool": {"must": must_queries}
        }
    }

    try:
        res = es.search(
            index=index,
            body=es_query,
            size=top_k
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la recherche : {e}"
        )

    results = []
    for hit in res["hits"]["hits"]:
        src = hit["_source"]
        results.append({
            "indicator": src.get("indicator", "N/A"),
            "value": src.get("value", "N/A"),
            "year": src.get("year", "N/A"),
            "milieu": src.get("milieu", "N/A"),
            "region": src.get("region", "N/A"),
            "categorie": src.get("categorie", "N/A"),
            "secteur": src.get("secteur", "N/A"),
            "genre": src.get("genre", "N/A"),
            "tranche_age": src.get("tranche_age", "N/A"),
            "source": src.get("source", "N/A"),
            "filename": src.get("filename", "N/A"),
            "dimensions": src.get("dimensions", "N/A"),
            "_score": round(hit["_score"], 3)
        })

    results.sort(key=lambda x: x["_score"], reverse=True)
    return results
