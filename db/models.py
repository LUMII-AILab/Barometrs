import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP, Float
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector

from .base import Base

"""
CREATE TABLE raw_comments
(
    id            SERIAL PRIMARY KEY,
    region        VARCHAR(10),
    article_id    INT,
    user_nickname VARCHAR(255),
    encoded_ip    VARCHAR(255),
    timestamp     TIMESTAMP,
    comment_text  TEXT,
    comment_lang  VARCHAR(255)
);
"""
class RawComment(Base):
    __tablename__ = "raw_comments"

    id = Column(Integer, primary_key=True)
    region = Column(String)
    article_id = Column(Integer, index=True)
    user_nickname = Column(String)
    encoded_ip = Column(String)
    timestamp = Column(TIMESTAMP, index=True)
    comment_text = Column(String)
    comment_lang = Column(String, index=True)

    # Add a relationship to the predicted_comments table
    predicted_comments = relationship("PredictedComment", back_populates="raw_comments")

"""
CREATE TABLE raw_articles
(
    id            SERIAL PRIMARY KEY,
    region        VARCHAR(10),
    article_id    INT,
    headline      TEXT,
    headline_lang VARCHAR(255),
    pub_timestamp TIMESTAMP,
    url           TEXT
);
"""
class RawArticle(Base):
    __tablename__ = "raw_articles"

    article_id = Column(Integer, primary_key=True)
    region = Column(String)
    headline = Column(String)
    headline_lang = Column(String, index=True)
    pub_timestamp = Column(TIMESTAMP, index=True)
    embedding = Column(Vector(768))
    url = Column(String)

    predicted_comments = relationship("PredictedComment", back_populates="raw_articles")

"""
CREATE TABLE predicted_comments
(
    id              SERIAL PRIMARY KEY,
    comment_id      INT,
    text            TEXT,
    text_lang       VARCHAR(255),
    model_name      VARCHAR(255),
    prediction_type VARCHAR(255),
    prediction      JSONB,
    CONSTRAINT fk_raw_comments FOREIGN KEY (comment_id) REFERENCES raw_comments (id)
);
"""
class PredictedComment(Base):
    __tablename__ = "predicted_comments"

    id = Column(Integer, primary_key=True)
    comment_id = Column(Integer, ForeignKey('raw_comments.id'), index=True)
    comment_timestamp = Column(TIMESTAMP, index=True)
    article_id = Column(Integer, ForeignKey('raw_articles.article_id'), index=True)
    text = Column(String)
    text_lang = Column(String, index=True)
    normal_prediction_json = Column(JSONB)
    normal_prediction_emotion = Column(String, index=True)
    normal_prediction_score = Column(Float)
    ekman_prediction_json = Column(JSONB)
    ekman_prediction_emotion = Column(String, index=True)
    ekman_prediction_score = Column(Float)

    # Add a foreign key constraint
    raw_comments = relationship("RawComment", back_populates="predicted_comments")
    raw_articles = relationship("RawArticle", back_populates="predicted_comments")

"""
CREATE TABLE log_raw_articles_imports
(
    import_id              SERIAL PRIMARY KEY,
    file_name              VARCHAR(255),
    import_timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status                 VARCHAR(100),
    notes                  TEXT
);
"""
class LogRawArticlesImport(Base):
    __tablename__ = "log_raw_articles_imports"

    import_id = Column(Integer, primary_key=True)
    file_name = Column(String, index=True)
    import_timestamp = Column(TIMESTAMP, default=datetime.datetime.now)
    status = Column(String, index=True)
    notes = Column(String)

"""
CREATE TABLE log_raw_comments_imports
(
    import_id              SERIAL PRIMARY KEY,
    file_name              VARCHAR(255),
    import_timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status                 VARCHAR(100),
    notes                  TEXT
);
"""
class LogRawCommentsImport(Base):
    __tablename__ = "log_raw_comments_imports"

    import_id = Column(Integer, primary_key=True)
    file_name = Column(String, index=True)
    import_timestamp = Column(TIMESTAMP, default=datetime.datetime.now)
    status = Column(String, index=True)
    notes = Column(String)

def register_models():
    # This function does nothing but ensures Python executes the model definitions
    pass