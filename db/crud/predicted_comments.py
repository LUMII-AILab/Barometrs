from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date, or_, and_
from core import load_model
from db import models
import pandas as pd

supported_languages = ['lv', 'ru']
min_date = date(2023, 1, 1)

def create_predicted_comment(db: Session, predicted_comment: models.PredictedComment):
    db.add(predicted_comment)
    return predicted_comment

def get_predicted_comment_allowed_months(db: Session):
    results = (
        db.query(
            func.max(cast(models.PredictedComment.comment_timestamp, Date)).label('max_date')
        ).first()
    )

    max_date = results.max_date
    months = pd.date_range(start=min_date, end=max_date, freq='MS').strftime('%Y-%m').tolist()

    return {
        "min_month": min_date.strftime('%Y-%m'),
        "max_month": max_date.strftime('%Y-%m'),
        "months": months
    }

def get_predicted_comments(db: Session, offset: int = 0, batch_size: int = 100):
    # Left join to get the raw comment text
    results = (db.query(models.PredictedComment, models.RawComment)
            .outerjoin(models.RawComment, models.PredictedComment.comment_id == models.RawComment.id)
            .where(models.PredictedComment.comment_id != None)
            .offset(offset).limit(batch_size).all())

    # Serialize the data manually
    return [{
        "predicted_comment": result[0],
        "raw_comment": result[1],
    } for result in results]

def get_predicted_comments_max_emotion_chart_data(
        db: Session,
        prediction_type: str,
        start_month: date,
        end_month: date,
        group_by: str = 'month'
):
    if start_month < min_date:
        start_month = min_date

    if end_month < min_date:
        end_month = min_date

    if start_month > end_month:
        start_month = end_month

    if prediction_type == 'normal':
        query = db.query(
            models.PredictedComment.comment_timestamp.label('timestamp'),
            models.PredictedComment.article_id.label('article_id'),
            models.PredictedComment.normal_prediction_emotion.label('emotion'),
            models.PredictedComment.normal_prediction_score.label('emotion_score'),
            models.PredictedComment.text_lang.label('text_lang'),
        )
    elif prediction_type == 'ekman':
        query = db.query(
            models.PredictedComment.comment_timestamp.label('timestamp'),
            models.PredictedComment.article_id.label('article_id'),
            models.PredictedComment.ekman_prediction_emotion.label('emotion'),
            models.PredictedComment.ekman_prediction_score.label('emotion_score'),
            models.PredictedComment.text_lang.label('text_lang'),
        )
    else:
        return None

    # filter my month and year
    results = query.filter(
        models.PredictedComment.text_lang.in_(supported_languages),
        or_(
            and_(
                func.date_part('year', models.PredictedComment.comment_timestamp) > start_month.year,
                func.date_part('year', models.PredictedComment.comment_timestamp) < end_month.year
            ),
            and_(
                func.date_part('year', models.PredictedComment.comment_timestamp) == start_month.year,
                func.date_part('year', models.PredictedComment.comment_timestamp) == end_month.year,
                func.date_part('month', models.PredictedComment.comment_timestamp) >= start_month.month,
                func.date_part('month', models.PredictedComment.comment_timestamp) <= end_month.month
            ),
            and_(
                func.date_part('year', models.PredictedComment.comment_timestamp) == start_month.year,
                func.date_part('month', models.PredictedComment.comment_timestamp) >= start_month.month,
                start_month.year < end_month.year
            ),
            and_(
                func.date_part('year', models.PredictedComment.comment_timestamp) == end_month.year,
                func.date_part('month', models.PredictedComment.comment_timestamp) <= end_month.month,
                start_month.year < end_month.year
            )
        )
    ).all()

    if not results:
        return None

    df = pd.DataFrame(results, columns=['timestamp', 'article_id', 'emotion', 'emotion_score', 'text_lang'])

    # Convert 'timestamp' from string or other types to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    df['comment_month'] = df['timestamp'].dt.strftime('%Y-%m')
    # Group by week, then convert week to string format 'YYYY-MM-DD', where the day is the first day of the week
    df['comment_week'] = df['timestamp'].dt.to_period('W').dt.start_time.dt.strftime('%Y-%m-%d')
    df['comment_date'] = df['timestamp'].dt.strftime('%Y-%m-%d')

    # Filter by language ('lv' or 'ru')
    def prepare_response_per_requested(df_scoped, requested_language):
        if requested_language in ['lv', 'ru']:
            df_scoped = df_scoped[df_scoped['text_lang'] == requested_language]

        if group_by == 'month':
            chart_start = df_scoped['comment_month'].min()
            article_count_per_period = df_scoped.groupby('comment_month')['article_id'].nunique()
            comment_count_per_period = df_scoped['comment_month'].value_counts().sort_index()
            emotion_count_per_period = df_scoped.groupby(['comment_month', 'emotion']).size().unstack(fill_value=0)
            emotion_percent_per_period = emotion_count_per_period.divide(emotion_count_per_period.sum(axis=1), axis=0)
            emotions_grouped_percent_per_period = emotion_count_per_period.sum() / len(df_scoped)
        elif group_by == 'week':
            chart_start = df_scoped['comment_week'].min()
            article_count_per_period = df_scoped.groupby('comment_week')['article_id'].nunique()
            comment_count_per_period = df_scoped['comment_week'].value_counts().sort_index()
            emotion_count_per_period = df_scoped.groupby(['comment_week', 'emotion']).size().unstack(fill_value=0)
            emotion_percent_per_period = emotion_count_per_period.divide(emotion_count_per_period.sum(axis=1), axis=0)
            emotions_grouped_percent_per_period = emotion_count_per_period.sum() / len(df_scoped)
        elif group_by == 'day':
            chart_start = df_scoped['comment_date'].min()
            article_count_per_period = df_scoped.groupby('comment_date')['article_id'].nunique()
            comment_count_per_period = df_scoped['comment_date'].value_counts().sort_index()
            emotion_count_per_period = df_scoped.groupby(['comment_date', 'emotion']).size().unstack(fill_value=0)
            emotion_percent_per_period = emotion_count_per_period.divide(emotion_count_per_period.sum(axis=1), axis=0)
            emotions_grouped_percent_per_period = emotion_count_per_period.sum() / len(df_scoped)
        else:
            return None

        return {
            "chart_start": chart_start,
            "article_count_per_period": article_count_per_period.to_dict(),
            "comment_count_per_period": comment_count_per_period.to_dict(),
            "emotion_count_per_period": emotion_count_per_period.to_dict(),
            "emotion_percent_per_period": emotion_percent_per_period.to_dict(),
            "emotions_grouped_percent_per_period": emotions_grouped_percent_per_period.to_dict(),
        }

    response = {
        "lv": prepare_response_per_requested(df, 'lv'),
        "ru": prepare_response_per_requested(df, 'ru'),
        "total": prepare_response_per_requested(df, 'total')
    }

    return response

def get_predicted_comments_max_emotion_comments_by_type_and_request_date(db: Session, prediction_type: str, request_date: date, lang: str):
    query = db.query(
        models.PredictedComment.id.label('id'),
        models.PredictedComment.text.label('comment_text'),
        models.PredictedComment.article_id.label('article_id'),
        models.RawArticle.headline.label('article_title'),
        models.PredictedComment.text_lang.label('comment_lang'),
    ).outerjoin(
        models.RawArticle, models.RawArticle.article_id == models.PredictedComment.article_id
    ).filter(
        models.RawArticle.article_id != None,
        cast(models.PredictedComment.comment_timestamp, Date) == request_date
    )

    if prediction_type == 'normal':
        # add additional select
        query = (
            query.add_columns(
                models.PredictedComment.normal_prediction_emotion.label('prediction'),
                models.PredictedComment.normal_prediction_score.label('prediction_score')
            ).filter(
                models.PredictedComment.normal_prediction_emotion != None
            )
        )
    elif prediction_type == 'ekman':
        query = (
            query.add_columns(
                models.PredictedComment.ekman_prediction_emotion.label('prediction'),
                models.PredictedComment.ekman_prediction_score.label('prediction_score')
            ).filter(
                models.PredictedComment.ekman_prediction_emotion != None
            )
        )
    else:
        return None

    if lang and lang != 'all' and lang in supported_languages:
        query = query.filter(models.PredictedComment.text_lang == lang)
    else:
        query = query.filter(models.PredictedComment.text_lang.in_(supported_languages))

    results = query.all()

    if not results:
        return None

    df = pd.DataFrame(results, columns=[
        'id', 'comment_text', 'article_id', 'article_title', 'comment_lang', 'prediction', 'prediction_score'
    ])

    # Convert score to percentage and round to 2 decimal places
    df['prediction_score'] = (df['prediction_score'] * 100).round(2)

    return df.to_dict(orient='records')

def get_predicted_comments_max_emotion_articles_clustered(
        db: Session,
        prediction_type: str,
        request_date: date,
        lang: str,
        min_cluster_size: int,
        min_samples: int
):
    import hdbscan

    if request_date < min_date:
        request_date = min_date

    query = db.query(
        models.PredictedComment.id.label('id'),
        models.PredictedComment.text.label('comment_text'),
        models.RawArticle.article_id.label('id'),
        models.RawArticle.headline.label('article_title'),
        models.RawArticle.embedding.label('embedding')
    ).outerjoin(
        models.PredictedComment, models.PredictedComment.article_id == models.RawArticle.article_id
    ).filter(
        models.PredictedComment.id != None,
        func.cast(models.PredictedComment.comment_timestamp, Date) == request_date
    )

    if prediction_type == 'normal':
        query = (
            query.add_columns(
                models.PredictedComment.normal_prediction_emotion.label('emotion'),
                models.PredictedComment.normal_prediction_score.label('emotion_score')
            ).filter(
                models.PredictedComment.normal_prediction_emotion != None
            )
         )
    elif prediction_type == 'ekman':
        query = (
            query.add_columns(
                models.PredictedComment.ekman_prediction_emotion.label('emotion'),
                models.PredictedComment.ekman_prediction_score.label('emotion_score')
            ).filter(
                models.PredictedComment.ekman_prediction_emotion != None
            )
        )
    else:
        return None

    if lang and lang != 'all' and lang in supported_languages:
        query = query.filter(
            models.PredictedComment.text_lang == lang,
            models.RawArticle.headline_lang == lang
        )
    else:
        query = query.filter(
            models.PredictedComment.text_lang.in_(supported_languages),
            models.RawArticle.headline_lang.in_(supported_languages)
        )

    # Ensure results are unique
    query = query.distinct()
    results = query.all()

    if not results:
        return None

    df = pd.DataFrame(results, columns=['id', 'comment_text', 'article_id', 'article_title', 'embedding', 'emotion', 'emotion_score'])

    # Get unique articles with their embeddings
    articles_df = df[['article_id', 'article_title', 'embedding']].drop_duplicates(subset=['article_id'])
    embeddings = articles_df['embedding'].tolist()

    # Cluster the embeddings
    clusterer = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size, min_samples=min_samples)
    clusters = clusterer.fit_predict(embeddings)

    # map cluster to article_id from the original dataframe
    articles_df['cluster'] = clusters

    # merge the cluster column back to the original dataframe
    df = df.merge(articles_df[['article_id', 'cluster']], on='article_id')

    # drop the embeddings column
    df.drop(columns=['embedding'], inplace=True)

    df['emotion_score'] = (df['emotion_score'] * 100).round(2)

    return df.to_dict(orient='records')

def get_predicted_comments_max_emotion_articles_by_type_and_date(db: Session, prediction_type: str, request_date: date, lang: str):
    if request_date < min_date:
        request_date = min_date

    query = db.query(
        models.RawArticle.article_id.label('id'),
        models.RawArticle.headline.label('article_title'),
    ).outerjoin(
        models.PredictedComment, models.PredictedComment.article_id == models.RawArticle.article_id
    ).filter(
        models.PredictedComment.id != None,
        func.cast(models.PredictedComment.comment_timestamp, Date) == request_date
    )

    if prediction_type == 'normal':
        query = query.filter(models.PredictedComment.normal_prediction_emotion != None)
    elif prediction_type == 'ekman':
        query = query.filter(models.PredictedComment.ekman_prediction_emotion != None)
    else:
        return None

    if lang and lang != 'all' and lang in supported_languages:
        query = query.filter(models.PredictedComment.text_lang == lang)
    else:
        query = query.filter(models.PredictedComment.text_lang.in_(supported_languages))

    # Ensure results are unique
    query = query.distinct()
    results = query.all()

    if not results:
        return None

    df = pd.DataFrame(results, columns=['id', 'article_title'])

    return df.to_dict(orient='records')

def get_predicted_comments_emotion_keywords(db: Session, prediction_type: str, request_date: date, lang: str):
    if prediction_type == 'normal':
        query = db.query(
            models.PredictedComment.text.label('comment_text'),
            models.PredictedComment.text_lang.label('text_lang'),
            models.PredictedComment.normal_prediction_emotion.label('emotion'),
            models.PredictedComment.normal_prediction_score.label('emotion_score'),
        )
    elif prediction_type == 'ekman':
        query = db.query(
            models.PredictedComment.text.label('comment_text'),
            models.PredictedComment.text_lang.label('text_lang'),
            models.PredictedComment.ekman_prediction_emotion.label('emotion'),
            models.PredictedComment.ekman_prediction_score.label('emotion_score'),
        )
    else:
        return None

    query = query.filter(
        cast(models.PredictedComment.comment_timestamp, Date) == request_date
    )

    if lang and lang != 'all' and lang in supported_languages:
        query = query.filter(models.PredictedComment.text_lang == lang)
    else:
        query = query.filter(models.PredictedComment.text_lang.in_(supported_languages))

    results = query.all()

    if not results:
        return None

    df = pd.DataFrame(results, columns=['comment_text', 'text_lang', 'emotion', 'emotion_score'])

    def extract_keywords(model, text, stopword_list=None):
        keywords = model.extract_keywords(text, stop_words=stopword_list, keyphrase_ngram_range=(2, 2), top_n=5)
        return keywords

    if lang in supported_languages:
        kb_model = load_model.get_keybert_model_by_language_and_prediction_type(lang, prediction_type)
        stopword_list = load_model.get_stopwords(lang)

        emotion_concat_text = df.groupby('emotion')['comment_text'].agg(lambda texts: ' '.join(texts))
        keywords_by_emotion = emotion_concat_text.apply(lambda text: extract_keywords(kb_model, text, stopword_list))

        keywords_df = keywords_by_emotion.reset_index()
        keywords_df.columns = ['emotion', 'keywords']
    else:
        kb_lvbert = load_model.get_keybert_model_by_language_and_prediction_type('lv', prediction_type)
        lv_stopwords = load_model.get_stopwords('lv')

        kb_rubert = load_model.get_keybert_model_by_language_and_prediction_type('ru', prediction_type)
        ru_stopwords = load_model.get_stopwords('ru')

        lv_emotion_concat_text = df[df['text_lang'] == 'lv'].groupby('emotion')['comment_text'].agg(lambda texts: ' '.join(texts))
        ru_emotion_concat_text = df[df['text_lang'] == 'ru'].groupby('emotion')['comment_text'].agg(lambda texts: ' '.join(texts))

        keywords_by_emotion_lv = lv_emotion_concat_text.apply(lambda text: extract_keywords(kb_lvbert, text, lv_stopwords))
        keywords_by_emotion_ru = ru_emotion_concat_text.apply(lambda text: extract_keywords(kb_rubert, text, ru_stopwords))

        keywords_df_lv = keywords_by_emotion_lv.reset_index()
        keywords_df_lv.columns = ['emotion', 'keywords']
        keywords_df_lv['emotion'] = 'lv_' + keywords_df_lv['emotion']

        keywords_df_ru = keywords_by_emotion_ru.reset_index()
        keywords_df_ru.columns = ['emotion', 'keywords']
        keywords_df_ru['emotion'] = 'ru_' + keywords_df_ru['emotion']

        keywords_df = pd.concat([keywords_df_lv, keywords_df_ru], ignore_index=True)

    return keywords_df.to_dict(orient='records')