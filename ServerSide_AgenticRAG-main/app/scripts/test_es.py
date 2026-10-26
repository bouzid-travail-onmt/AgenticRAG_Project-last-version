# test_es.py
import sys
import os
import traceback
from elasticsearch import Elasticsearch, exceptions

# ⚠️ Ajouter le chemin racine pour les imports du projet
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from app.core.config import ES_HOST, ES_USER, ES_PASSWORD
except Exception as e:
    print("❌ Erreur import config:", e)
    sys.exit(1)

ES_INDEX = "data_index"

print("🔹 Initialisation Elasticsearch...")
try:
    es = Elasticsearch(
        ES_HOST,
        basic_auth=(ES_USER, ES_PASSWORD),
        verify_certs=False,
        request_timeout=60  # 1 minute
    )
except Exception as e:
    print("❌ Erreur connexion ES:", e)
    sys.exit(1)

print("🔹 Vérification de la connexion à Elasticsearch...")
try:
    if es.ping():
        print("✅ Elasticsearch est joignable")
    else:
        print("❌ Elasticsearch ne répond pas")
        sys.exit(1)
except exceptions.ConnectionError as e:
    print("❌ Impossible de se connecter à Elasticsearch:", e)
    sys.exit(1)

print(f"🔹 Vérification de l'existence de l'index '{ES_INDEX}'...")
try:
    if not es.indices.exists(index=ES_INDEX):
        print(f"ℹ Index '{ES_INDEX}' non trouvé → création...")
        es.indices.create(index=ES_INDEX)
        print(f"✅ Index '{ES_INDEX}' créé avec succès")
    else:
        print(f"✅ Index '{ES_INDEX}' existe déjà")
except Exception as e:
    print("❌ Erreur vérification/création index:", e)
    traceback.print_exc()

print("🔹 Test terminé")
