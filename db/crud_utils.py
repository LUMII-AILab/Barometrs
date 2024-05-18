import pandas as pd
from sqlalchemy import or_
from sqlalchemy.orm import Session
from . import models

def create_raw_article(db: Session, raw_article: models.RawArticle):
    db.add(raw_article)
    db.commit()
    db.refresh(raw_article)
    return raw_article

def remove_existing_article_ids(df: pd.DataFrame, db: Session) -> pd.DataFrame:
    # Extract article_ids from the DataFrame
    article_ids = df['article_id'].tolist()

    # Query the database for these IDs
    existing_ids = db.query(models.RawArticle.article_id).filter(models.RawArticle.article_id.in_(article_ids)).all()
    existing_ids = {id[0] for id in existing_ids}  # Convert list of tuples to set for faster lookup

    # Filter the DataFrame to exclude existing IDs
    df_filtered = df[~df['article_id'].isin(existing_ids)]
    return df_filtered

def bulk_insert_articles(df: pd.DataFrame, db: Session):
    # First remove any rows with article_ids that already exist in the database
    df_to_insert = remove_existing_article_ids(df, db)

    if df_to_insert.empty:
        print("No new articles to insert.")
        return

    # Convert DataFrame to dictionary list for bulk insert
    articles_data = df_to_insert.to_dict(orient='records')

    # Perform bulk insert
    db.bulk_insert_mappings(models.RawArticle, articles_data)
    db.commit()

def bulk_insert_comments(df: pd.DataFrame, db: Session):
    # Convert DataFrame to dictionary list for bulk insert
    comments_data = df.to_dict(orient='records')

    # Perform bulk insert
    db.bulk_insert_mappings(models.RawComment, comments_data)
    db.commit()

def get_raw_article(db: Session, article_id: int):
    return db.query(models.RawArticle).filter(models.RawArticle.article_id == article_id).first()

def check_raw_article_exists(db: Session, article_id: int):
    return get_raw_article(db, article_id) is not None

def get_raw_comment_count(db: Session):
    return db.query(models.RawComment).count()

def get_raw_comment(db: Session, raw_comment_id: int):
    return db.query(models.RawComment).filter(models.RawComment.id == raw_comment_id).first()

def check_raw_comment_exists(db: Session, raw_comment_id: int):
    return get_raw_comment(db, raw_comment_id) is not None

def get_raw_comments(db: Session, offset: int = 0, batch_size: int = 100):
    return db.query(models.RawComment).offset(offset).limit(batch_size).all()

def get_raw_lv_comments(db: Session, offset: int = 0, batch_size: int = 100):
    return db.query(models.RawComment).filter(models.RawComment.comment_lang == 'lv').offset(offset).limit(batch_size).all()

def get_unprecited_comment_count(db: Session):
    return (db.query(models.RawComment)
    .filter(
        or_(models.RawComment.comment_lang == 'lv', models.RawComment.comment_lang == 'ru'),
        models.RawComment.predicted_comments == None
    ).count())

def get_raw_unpredicted_comments(db: Session, last_id: int = 0, batch_size: int = 100):
    # Filter by language ('lv' or 'ru') and predicted_comments is None
    return db.query(models.RawComment).filter(
        or_(models.RawComment.comment_lang == 'lv', models.RawComment.comment_lang == 'ru'),
        models.RawComment.predicted_comments == None,
        models.RawComment.id > last_id
    ).order_by(models.RawComment.id).limit(batch_size).all()

def create_raw_comment(db: Session, raw_comment: models.RawComment):
    db.add(raw_comment)
    db.commit()
    db.refresh(raw_comment)
    return raw_comment

def create_log_raw_comments_import(db: Session, file_name: str, status: str, notes: str):
    log_raw_comments_import = models.LogRawCommentsImport(file_name=file_name, status=status, notes=notes)
    db.add(log_raw_comments_import)
    db.commit()
    db.refresh(log_raw_comments_import)
    return log_raw_comments_import

def check_log_raw_comments_imports_exists(db: Session, file_name: str):
    return db.query(models.LogRawCommentsImport).filter(models.LogRawCommentsImport.file_name == file_name).first() is not None

def create_log_raw_articles_import(db: Session, file_name: str, status: str, notes: str):
    log_raw_articles_import = models.LogRawArticlesImport(file_name=file_name, status=status, notes=notes)
    db.add(log_raw_articles_import)
    db.commit()
    db.refresh(log_raw_articles_import)
    return log_raw_articles_import

def check_log_raw_articles_imports_exists(db: Session, file_name: str):
    return db.query(models.LogRawArticlesImport).filter(models.LogRawArticlesImport.file_name == file_name).first() is not None

def get_processed_article_files(db: Session) -> list[str]:
    return [log.file_name for log in db.query(models.LogRawArticlesImport).where(models.LogRawArticlesImport.status == 'Success').all()]

def get_processed_comment_files(db: Session) -> list[str]:
    return [log.file_name for log in db.query(models.LogRawCommentsImport).where(models.LogRawCommentsImport.status == 'Success').all()]