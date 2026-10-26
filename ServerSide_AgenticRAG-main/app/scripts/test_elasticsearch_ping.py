from elasticsearch import Elasticsearch
from app.core.config import ES_HOST, ES_USER, ES_PASSWORD

def get_elasticsearch():
    print("Initialisation client Elasticsearch...")
    print("ES_HOST =", ES_HOST)
    print("ES_USER =", ES_USER)
    
    es = Elasticsearch(
        ES_HOST,
        basic_auth=(ES_USER, ES_PASSWORD),
        verify_certs=False,   # obligatoire si certificat auto-signé ou HTTP
        request_timeout=30
    )
    return es

if __name__ == "__main__":
    es = get_elasticsearch()
    print("🔄 Tentative de ping...")
    
    if es.ping():
        print("✅ Elasticsearch accessible et authentifié")
    else:
        print("❌ Ping échoué, vérifie tes credentials et le protocole (http/https)")
