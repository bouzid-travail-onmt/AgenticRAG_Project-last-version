import logging
import sys
from app.core.logging import InterceptHandler
from loguru import logger
from starlette.config import Config
from starlette.datastructures import Secret
# Charger les variables d'environnement depuis le fichier .env
config = Config(".env")
# --- MongoDB ---
MONGO_URI: str = config("MONGO_URI", default="mongodb://localhost:27017")
MONGO_DB: str = config("MONGO_DB", default="chatbot_db")
# --- Elasticsearch ---
ES_HOST: str = config("ES_HOST", default="http://localhost:9200")
ES_USER: str = config("ES_USER", default="elastic")
ES_PASSWORD: str = config("ES_PASSWORD", default="changeme")
ES_INDEX: str = config("ES_INDEX", default="data_index")  # <-- nouvel index par défaut
# --- Ollama ---
OLLAMA_MODEL: str = config("OLLAMA_MODEL", default="gpt-oss:120b-cloud")
OLLAMA_HOST: str = config("OLLAMA_HOST", default="http://localhost:11434")
# --- preprocessing var ---
FAISS_INDEX_PATH = "app/models/faiss_index"
EMBEDDING_MODEL = "dangvantuan/sentence-camembert-base"
# --- Application ---
API_PREFIX = "/api"
VERSION = "0.1.0"
DEBUG: bool = config("DEBUG", cast=bool, default=False)
MAX_CONNECTIONS_COUNT: int = config("MAX_CONNECTIONS_COUNT", cast=int, default=10)
MIN_CONNECTIONS_COUNT: int = config("MIN_CONNECTIONS_COUNT", cast=int, default=10)
SECRET_KEY: Secret = config("SECRET_KEY", cast=Secret, default="")
MEMOIZATION_FLAG: bool = config("MEMOIZATION_FLAG", cast=bool, default=True)
PROJECT_NAME: str = config("PROJECT_NAME", default="Chatbot-project")
# --- Logging configuration ---
LOGGING_LEVEL = logging.DEBUG if DEBUG else logging.INFO
logging.basicConfig(
    handlers=[InterceptHandler(level=LOGGING_LEVEL)], level=LOGGING_LEVEL
)
logger.configure(handlers=[{"sink": sys.stderr, "level": LOGGING_LEVEL}])
# --- Machine learning model ---
MODEL_PATH = config("MODEL_PATH", default="./ml/model/")
MODEL_NAME = config("MODEL_NAME", default="FASISS")
INPUT_EXAMPLE = config("INPUT_EXAMPLE", default="./ml/model/examples/example.json")
