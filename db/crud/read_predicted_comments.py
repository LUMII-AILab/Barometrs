from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, text
from db import models
import pandas as pd

def get_predicted_comment_count(db: Session):
    return db.query(models.PredictedComment).count()

def aggregate_predicted_comments(
        session: Session,
        prediction_type: str,
        start_month: date,
        end_month: date,
        group_by: str = 'month'
):
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

            return emotion_count_per_period

        return {
            "emotion_count_per_period": get_emotion_data(),
        }

    def combine_responses(response1, response2):
        # sum emotion counts
        emotion_count_per_period = response1['emotion_count_per_period'].add(response2['emotion_count_per_period'], fill_value=0)

        return {
            "emotion_count_per_period": emotion_count_per_period,
        }

    lv_response = prepare_response_per_requested('lv')
    ru_response = prepare_response_per_requested('ru')
    total_response = combine_responses(lv_response, ru_response)

    # convert the responses to a dictionary
    def convert_response_to_dict(response):
        response['emotion_count_per_period'] = response['emotion_count_per_period'].to_dict()
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