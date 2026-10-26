from sqlalchemy import Column, Integer, Text

from app.db import  get_mongo_client, get_elasticsearch


class RequestLog():
    __tablename__ = "request_logs"

    id = Column(Integer, primary_key=True, index=True)
    request = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
