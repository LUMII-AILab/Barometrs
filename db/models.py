import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP, Float
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector

from .base import Base

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

# TODO: @see db/crud/predicted_comments.py::get_predicted_comments_max_emotion_chart_data
# Use aggregation to make data preparation for aggregation charts faster
class PredictedCommentAggregations(Base):
    __tablename__ = "predicted_comment_aggregations"

    id = Column(Integer, primary_key=True)
    date = Column(TIMESTAMP, index=True)
    scope_type = Column(Integer, index=True, comment="1 - day, 2 - week, 3 - month")
    language = Column(String, index=True)
    prediction_type = Column(Integer, index=True, comment="1 - normal, 2 - ekman")
    emotion = Column(String, index=True)
    count = Column(Integer)

class LogRawArticlesImport(Base):
    __tablename__ = "log_raw_articles_imports"

    import_id = Column(Integer, primary_key=True)
    file_name = Column(String, index=True)
    import_timestamp = Column(TIMESTAMP, default=datetime.datetime.now)
    status = Column(String, index=True)
    notes = Column(String)

class LogRawCommentsImport(Base):
    __tablename__ = "log_raw_comments_imports"

    import_id = Column(Integer, primary_key=True)
    file_name = Column(String, index=True)
    import_timestamp = Column(TIMESTAMP, default=datetime.datetime.now)
    status = Column(String, index=True)
    notes = Column(String)

class EmotionKeywordsByDay(Base):
    __tablename__ = "emotion_keywords_by_day"

    id = Column(Integer, primary_key=True)
    date = Column(TIMESTAMP, index=True)
    language = Column(String, index=True)
    prediction_type = Column(String, index=True)
    keywords_json = Column(JSONB)

def register_models():
    # This function does nothing but ensures Python executes the model definitions
    pass