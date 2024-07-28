from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date, and_, distinct, text
from db import models
import pandas as pd

supported_languages = ['lv', 'ru']
min_date = date(2020, 1, 1)

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
        session: Session,
        prediction_type: str,
        start_month: date,
        end_month: date,
        group_by: str = 'month'
):
    start_month = max(start_month, min_date)
    end_month = max(end_month, min_date)
    if start_month > end_month:
        start_month = end_month

    def prepare_response_per_requested(requested_language):
        # Determine the fields based on the prediction type
        if prediction_type == 'normal':
            emotion_field = models.PredictedComment.normal_prediction_emotion.label('emotion')
        elif prediction_type == 'ekman':
            emotion_field = models.PredictedComment.ekman_prediction_emotion.label('emotion')
        else:
            return None

        # Beginning of the start month
        start_date = start_month.replace(day=1)

        # Exclusive end of interval
        if end_month.month == 12:
            end_date = end_month.replace(year=end_month.year + 1, month=1, day=1)
        else:
            end_date = end_month.replace(month=end_month.month + 1, day=1)

        # Define filter condition to cover the whole interval in one range
        date_interval_condition = and_(
            models.PredictedComment.comment_timestamp >= start_date,
            models.PredictedComment.comment_timestamp < end_date
        )

        valid_groupings = {
            'month': 'YYYY-MM',
            'week': 'YYYY-MM-DD',
            'day': 'YYYY-MM-DD',
        }

        timestamp_format = valid_groupings[group_by]
        if group_by == 'week':
            group_by_field = func.to_char(
                func.date_trunc('week', models.PredictedComment.comment_timestamp) +
                text("interval '1 day'") -
                text("interval '1 week'"),
                timestamp_format
            )
        else:
            group_by_field = func.to_char(
                func.date_trunc(group_by, models.PredictedComment.comment_timestamp),
                timestamp_format
            )

        def apply_common_filters(query):
            """ Apply common filters to a query. """
            return query.filter(
                models.PredictedComment.text_lang == requested_language,
                date_interval_condition
            )

        def get_article_and_comment_count_per_period():
            """ Return dictionaries with the count of unique articles and total comments per period. """
            query = session.query(
                group_by_field.label('comment_period'),
                func.count(distinct(models.PredictedComment.article_id)).label('unique_articles'),
                func.count().label('total_comments')
            )
            # Apply common filters, group by the month, and fetch results
            results = apply_common_filters(query).group_by('comment_period').order_by('comment_period').all()

            # Load the results into a DataFrame
            df_results = pd.DataFrame(results, columns=['comment_period', 'unique_articles', 'total_comments'])

            article_counts = df_results.set_index('comment_period')['unique_articles']
            comment_counts = df_results.set_index('comment_period')['total_comments']

            return article_counts, comment_counts

        def get_emotion_data():
            # Retrieve emotion counts per period using a database query
            query = session.query(
                group_by_field.label('comment_period'),
                emotion_field.label('emotion'),
                func.count().label('emotion_count')
            )

            # Apply common filters, group by necessary fields, and order the results
            results = (apply_common_filters(query)
                       .group_by('comment_period', 'emotion')
                       .order_by('comment_period', 'emotion')
                       .all()
            )

            # Create a DataFrame from the query results
            df_results = pd.DataFrame(results, columns=['comment_period', 'emotion', 'emotion_count'])

            # Pivot table to transform data for emotion counts by period
            emotion_count_per_period = df_results.pivot_table(
                index='emotion',
                columns='comment_period',
                values='emotion_count',
                aggfunc='sum',
                fill_value=0
            )

            # Calculate the total emotions and grouped percentages
            total_emotions = df_results['emotion_count'].sum()
            emotions_grouped_percent_per_period = emotion_count_per_period.sum(axis=1) / total_emotions

            # Calculate emotion percentages per period
            emotion_percent_per_period = emotion_count_per_period.div(emotion_count_per_period.sum(axis=0), axis=1)

            return (emotion_count_per_period,
                    emotion_percent_per_period,
                    emotions_grouped_percent_per_period)

        article_count_per_period, comment_count_per_period = get_article_and_comment_count_per_period()
        emotion_count_per_period, emotion_percent_per_period, emotions_grouped_percent_per_period = get_emotion_data()

        if article_count_per_period.empty:
            return None
        chart_start = comment_count_per_period.index[0]

        return {
            "chart_start": chart_start,
            "article_count_per_period": article_count_per_period,
            "comment_count_per_period": comment_count_per_period,
            "emotion_count_per_period": emotion_count_per_period,
            "emotion_percent_per_period": emotion_percent_per_period,
            "emotions_grouped_percent_per_period": emotions_grouped_percent_per_period,
        }

    def combine_responses(response1, response2):
        chart_start = min(response1['chart_start'], response2['chart_start'])

        # sum article and comment counts
        article_count_per_period = response1['article_count_per_period'] + response2['article_count_per_period']
        comment_count_per_period = response1['comment_count_per_period'] + response2['comment_count_per_period']

        # sum emotion counts
        emotion_count_per_period = response1['emotion_count_per_period'].add(response2['emotion_count_per_period'], fill_value=0)

        # calculate emotion percentages
        emotion_percent_per_period = emotion_count_per_period.div(emotion_count_per_period.sum(axis=0), axis=1)

        # calculate grouped emotion percentages
        emotions_grouped_percent_per_period = emotion_count_per_period.sum(axis=1) / emotion_count_per_period.sum().sum()

        return {
            "chart_start": chart_start,
            "article_count_per_period": article_count_per_period,
            "comment_count_per_period": comment_count_per_period,
            "emotion_count_per_period": emotion_count_per_period,
            "emotion_percent_per_period": emotion_percent_per_period,
            "emotions_grouped_percent_per_period": emotions_grouped_percent_per_period,
        }

    lv_response = prepare_response_per_requested('lv')
    ru_response = prepare_response_per_requested('ru')
    total_response = combine_responses(lv_response, ru_response)

    # convert the responses to a dictionary
    def convert_response_to_dict(response):
        response['article_count_per_period'] = response['article_count_per_period'].to_dict()
        response['comment_count_per_period'] = response['comment_count_per_period'].to_dict()
        response['emotion_count_per_period'] = response['emotion_count_per_period'].to_dict()
        response['emotion_percent_per_period'] = response['emotion_percent_per_period'].to_dict()
        return response

    lv_response = convert_response_to_dict(lv_response)
    ru_response = convert_response_to_dict(ru_response)
    total_response = convert_response_to_dict(total_response)

    response = {
        "lv": lv_response,
        "ru": ru_response,
        "total": total_response,
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
    query = db.query(
        models.EmotionKeywordsByDay.language.label('language'),
        models.EmotionKeywordsByDay.keywords_json.label('keywords')
    ).filter(
        models.EmotionKeywordsByDay.date == request_date,
        models.EmotionKeywordsByDay.prediction_type == prediction_type
    )

    if lang and lang != 'all' and lang in supported_languages:
        query = query.filter(models.EmotionKeywordsByDay.language == lang)
    else:
        query = query.filter(models.EmotionKeywordsByDay.language.in_(supported_languages))

    results = query.all()

    if not results:
        return None

    df = pd.DataFrame(columns=['emotion', 'keywords'])

    for result in results:
        language = result.language

        # Create a temporary DataFrame from JSONB
        temp_df = pd.DataFrame(result.keywords.items(), columns=['emotion', 'keywords'])

        # Prefix each emotion with the language code
        temp_df['emotion'] = language + "_" + temp_df['emotion']

        # Append the temporary DataFrame
        df = pd.concat([df, temp_df], ignore_index=True)

    return df.to_dict(orient='records')
