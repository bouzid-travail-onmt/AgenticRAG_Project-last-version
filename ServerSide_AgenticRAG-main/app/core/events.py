from typing import Callable
import joblib
from fastapi import FastAPI
from loguru import logger
from sqlalchemy.exc import OperationalError
from app.core.config import MEMOIZATION_FLAG

# app/core/events.py
def create_start_app_handler(app):
    async def start_app():
        print("⚠️ Aucun modèle chargé (mode dev).")
    return start_app

def create_stop_app_handler(app):
    async def stop_app():
        print("🛑 Application arrêtée (mode dev).")
    return stop_app

'''
def preload_model():
    """
    In order to load model on memory to each worker
    """
    from services.predict import MachineLearningModelHandlerScore

    MachineLearningModelHandlerScore.get_model(joblib.load)


def create_start_app_handler(app: FastAPI) -> Callable:
    def start_app() -> None:
        if MEMOIZATION_FLAG:
            preload_model()
        try:
            Base.metadata.create_all(bind=engine)
        except OperationalError:
            logger.exception("failed to initialize database")

    return start_app
'''