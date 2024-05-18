from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import os

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", None)

engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_size=10, max_overflow=20)

def get_session():
    with Session(engine) as session:
        yield session