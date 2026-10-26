from cryptography.fernet import Fernet
from datetime import datetime, timedelta
import os

FERNET_KEY = os.getenv("SSE_FERNET_KEY") or Fernet.generate_key()
fernet = Fernet(FERNET_KEY)

SSE_TOKEN_STORE = {}  # Redis recommandé en prod
SSE_TTL_SECONDS = 3600  # 1 heure
