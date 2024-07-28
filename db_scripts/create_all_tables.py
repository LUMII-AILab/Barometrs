from db.base import Base
from db.models import register_models
from db.database import engine

register_models()
Base.metadata.create_all(engine, checkfirst=True)