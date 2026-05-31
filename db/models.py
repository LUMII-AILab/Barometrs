import datetime
from sqlalchemy import Column, Index, Integer, String, ForeignKey, TIMESTAMP, Float, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from .base import Base

class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = (
        Index('idx_comments_lang_website_id', 'comment_lang', 'website', 'id'),
    )

    id = Column(Integer, primary_key=True)
    region = Column(String)
    article_id = Column(Integer, index=True)
    user_nickname = Column(String)
    encoded_ip = Column(String)
    timestamp = Column(TIMESTAMP, index=True)
    comment_text = Column(String)
    comment_lang = Column(String, index=True)
    website = Column(String, index=True)

    predicted_comments = relationship("PredictedComment", back_populates="comment")

class Article(Base):
    __tablename__ = "articles"

    article_id = Column(Integer, primary_key=True)
    region = Column(String)
    headline = Column(String)
    headline_lang = Column(String, index=True)
    pub_timestamp = Column(TIMESTAMP, index=True)
    url = Column(String)
    website = Column(String, index=True)

    predicted_comments = relationship("PredictedComment", back_populates="article")

class PredictedComment(Base):
    __tablename__ = "predicted_comments"
    __table_args__ = (
        Index('idx_predicted_comments_ts_lang_ekman', 'comment_timestamp', 'text_lang', 'ekman_prediction_emotion'),
    )

    id = Column(Integer, primary_key=True)
    comment_id = Column(Integer, ForeignKey('comments.id'), index=True)
    comment_timestamp = Column(TIMESTAMP, index=True)
    article_id = Column(Integer, ForeignKey('articles.article_id'), index=True)
    text = Column(String)
    text_lang = Column(String, index=True)
    website = Column(String, index=True)
    normal_prediction_json = Column(JSONB)
    normal_prediction_emotion = Column(String, index=True)
    normal_prediction_score = Column(Float)
    ekman_prediction_json = Column(JSONB)
    ekman_prediction_emotion = Column(String, index=True)
    ekman_prediction_score = Column(Float)

    comment = relationship("Comment", back_populates="predicted_comments")
    article = relationship("Article", back_populates="predicted_comments")

class LogArticlesImport(Base):
    __tablename__ = "log_articles_imports"

    import_id = Column(Integer, primary_key=True)
    file_name = Column(String, index=True)
    import_timestamp = Column(TIMESTAMP, default=datetime.datetime.now)
    status = Column(String, index=True)
    notes = Column(String)
    website = Column(String)

class LogCommentsImport(Base):
    __tablename__ = "log_comments_imports"

    import_id = Column(Integer, primary_key=True)
    file_name = Column(String, index=True)
    import_timestamp = Column(TIMESTAMP, default=datetime.datetime.now)
    status = Column(String, index=True)
    notes = Column(String)
    website = Column(String)

class EmotionKeywordsByDay(Base):
    __tablename__ = "emotion_keywords_by_day"
    __table_args__ = (
        Index('idx_emotion_keywords_date_lang_type', 'date', 'language', 'prediction_type'),
    )

    id = Column(Integer, primary_key=True)
    date = Column(TIMESTAMP, index=True)
    language = Column(String, index=True)
    prediction_type = Column(String, index=True)
    website = Column(String, index=True)
    keywords_json = Column(JSONB)

class AggressiveKeyword(Base):
    __tablename__ = "aggressive_keywords"

    id = Column(Integer, primary_key=True)
    word = Column(String, unique=True, index=True)
    language = Column(String, index=True)
    weight = Column(Float)
    frequency = Column(Integer)

    category_diskrim = Column(Boolean, default=False)
    category_lamuv = Column(Boolean, default=False)
    category_netaisn = Column(Boolean, default=False)
    category_aicin = Column(Boolean, default=False)
    category_darb = Column(Boolean, default=False)
    category_pers = Column(Boolean, default=False)
    category_asoc = Column(Boolean, default=False)
    category_milit = Column(Boolean, default=False)
    category_nosod = Column(Boolean, default=False)
    category_emoc = Column(Boolean, default=False)
    category_nodev = Column(Boolean, default=False)

class LemmatizedComment(Base):
    __tablename__ = "lemmatized_comments"

    id = Column(Integer, primary_key=True)
    comment_id = Column(Integer, ForeignKey('comments.id'), unique=True, index=True)
    lemmas = Column(JSONB)
    lemma_count = Column(Integer)
    words = Column(JSONB)  # original word forms, parallel to lemmas: words[i] is the surface form of lemmas[i]

class AggressivenessByDay(Base):
    __tablename__ = "aggressiveness_by_day"

    id = Column(Integer, primary_key=True)
    date = Column(TIMESTAMP, index=True)
    language = Column(String, index=True)
    website = Column(String, index=True)
    aggressive_word_count = Column(Integer)
    aggressive_word_weight_sum = Column(Float)
    total_word_count = Column(Integer)
    aggressiveness_ratio = Column(Float)
    weighted_aggressiveness_ratio = Column(Float)

class AggressiveKeywordsByDay(Base):
    __tablename__ = "aggressive_keywords_by_day"

    id = Column(Integer, primary_key=True)
    date = Column(TIMESTAMP, index=True)
    language = Column(String, index=True)
    website = Column(String, index=True)
    keywords_json = Column(JSONB)  # {"word": {"count": N, "weight_sum": F, "article_count": N, "article_ids": [...], "forms": {"surface_form": count}}}
    total_word_count = Column(Integer)

def register_models():
    pass
