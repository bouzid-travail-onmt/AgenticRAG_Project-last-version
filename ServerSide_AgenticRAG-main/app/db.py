# --- MongoDB setup ---
# --- Elasticsearch setup ---
from pymongo import MongoClient
from elasticsearch import Elasticsearch
from app.core.config import MONGO_URI, MONGO_DB, ES_HOST, ES_USER, ES_PASSWORD, OLLAMA_HOST, OLLAMA_MODEL
from ollama import Client  # ⚠️ Assurez-vous que le package Ollama est installé

# Fonction pour récupérer la base MongoDB
def get_mongo_client():
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    return db

# Fonction pour récupérer Elasticsearch
def get_elasticsearch():
    es = Elasticsearch(
        [ES_HOST],
        verify_certs=False, 
        request_timeout=30,
        basic_auth=(ES_USER, ES_PASSWORD)
    )
    return es
# Fonction pour récupérer le client Ollama

def get_ollama():
    """
    Retourne un client Ollama prêt à l'emploi pour le streaming.
    """
    client = Client(host=OLLAMA_HOST)
    return client
