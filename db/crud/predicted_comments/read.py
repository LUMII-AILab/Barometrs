from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, distinct, text, cast, Date
from db import models
import pandas as pd

def get_predicted_comment_count(db: Session):
    return db.query(models.PredictedComment).count()

def get_predicted_comments_by_batch(db: Session, last_id: int = 0, batch_size: int = 100):
    return db.query(models.PredictedComment).filter(
        models.PredictedComment.id > last_id,
    ).order_by(models.PredictedComment.id).limit(batch_size).all()

def get_predicted_comments_by_day(db: Session, date: date = None):
    return db.query(models.PredictedComment).filter(
        cast(models.PredictedComment.comment_timestamp, Date) == date
    ).order_by(models.PredictedComment.id).all()

def aggregate_predicted_comments(
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