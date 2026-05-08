import pandas as pd
from sqlalchemy import or_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from . import models

def create_article(db: Session, article: models.Article):
    db.add(article)
    db.commit()
    db.refresh(article)
    return article

def bulk_insert_articles(df: pd.DataFrame, db: Session):
    data = df.to_dict(orient='records')
    db.execute(insert(models.Article).on_conflict_do_nothing(index_elements=['article_id']), data)
    db.commit()

def bulk_insert_comments(df: pd.DataFrame, db: Session):
    comments_data = df.to_dict(orient='records')
    db.execute(insert(models.Comment), comments_data)
    db.commit()

def get_article(db: Session, article_id: int):
    return db.query(models.Article).filter(models.Article.article_id == article_id).first()

def check_article_exists(db: Session, article_id: int):
    return get_article(db, article_id) is not None

def get_comment_count(db: Session):
    return db.query(models.Comment).count()

def get_comment(db: Session, comment_id: int):
    return db.query(models.Comment).filter(models.Comment.id == comment_id).first()

def check_comment_exists(db: Session, comment_id: int):
    return get_comment(db, comment_id) is not None

def get_raw_comments(db: Session, offset: int = 0, batch_size: int = 100):
    return db.query(models.Comment).offset(offset).limit(batch_size).all()

def get_raw_lv_comments(db: Session, offset: int = 0, batch_size: int = 100):
    return db.query(models.Comment).filter(models.Comment.comment_lang == 'lv').offset(offset).limit(batch_size).all()

def get_unprecited_comment_count(db: Session):
    article_exists_subquery = db.query(models.Article.article_id).filter(
        models.Article.article_id == models.Comment.article_id
    ).exists()

    return (db.query(models.Comment)
    .filter(
        or_(models.Comment.comment_lang == 'lv', models.Comment.comment_lang == 'ru'),
        models.Comment.predicted_comments == None,
        article_exists_subquery
    ).count())

def get_raw_unpredicted_comments_by_batch(db: Session, last_id: int = 0, batch_size: int = 100):
    article_exists_subquery = db.query(models.Article.article_id).filter(
        models.Article.article_id == models.Comment.article_id
    ).exists()

    return db.query(models.Comment).filter(
        or_(models.Comment.comment_lang == 'lv', models.Comment.comment_lang == 'ru'),
        models.Comment.predicted_comments == None,
        models.Comment.id > last_id,
        article_exists_subquery
    ).order_by(models.Comment.id).limit(batch_size).all()

def create_comment(db: Session, comment: models.Comment):
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment

def create_log_comments_import(db: Session, file_name: str, status: str, notes: str, website: str):
    log = models.LogCommentsImport(file_name=file_name, status=status, notes=notes, website=website)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log

def check_log_comments_import_exists(db: Session, file_name: str):
    return db.query(models.LogCommentsImport).filter(models.LogCommentsImport.file_name == file_name).first() is not None

def create_log_articles_import(db: Session, file_name: str, status: str, notes: str, website: str):
    log = models.LogArticlesImport(file_name=file_name, status=status, notes=notes, website=website)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log

def check_log_articles_import_exists(db: Session, file_name: str):
    return db.query(models.LogArticlesImport).filter(models.LogArticlesImport.file_name == file_name).first() is not None

def get_processed_article_files(db: Session) -> list[str]:
    return [log.file_name for log in db.query(models.LogArticlesImport).where(models.LogArticlesImport.status == 'Success').all()]

def get_processed_comment_files(db: Session) -> list[str]:
    return [log.file_name for log in db.query(models.LogCommentsImport).where(models.LogCommentsImport.status == 'Success').all()]
