from db.database import engine
from db.base import Base
from db.models import register_models

def drop_tables():
    Base.metadata.drop_all(engine)

def create_tables():
    Base.metadata.create_all(engine)

if __name__ == "__main__":
    pass
    # register_models()
    # drop_tables()
    # create_tables()