from datetime import date
from sqlalchemy import func, text
from sqlalchemy.orm import Session
from db import models


def get_aggressiveness_by_period(session: Session, language: str, start_date: date, end_date: date, group_by: str):
    trunc = {'month': 'month', 'week': 'week'}.get(group_by, 'day')
    period = func.date_trunc(trunc, models.AggressivenessByDay.date).label('date')
    weight_sum = func.sum(models.AggressivenessByDay.aggressive_word_weight_sum).label('aggressive_word_weight_sum')
    total_count = func.sum(models.AggressivenessByDay.total_word_count).label('total_word_count')

    rows = (
        session.query(period, weight_sum, total_count)
        .filter(
            models.AggressivenessByDay.language == language,
            models.AggressivenessByDay.date >= start_date,
            models.AggressivenessByDay.date <= end_date,
        )
        .group_by(period)
        .order_by(period)
        .all()
    )

    return [
        {
            'date': row.date.strftime('%Y-%m-%d'),
            'aggressive_word_weight_sum': row.aggressive_word_weight_sum,
            'total_word_count': row.total_word_count,
            'weighted_aggressiveness_ratio': (
                row.aggressive_word_weight_sum / row.total_word_count if row.total_word_count else 0
            ),
        }
        for row in rows
    ]


def get_aggressive_keywords_count_by_day(session: Session, request_date: date, lang: str):
    supported_languages = ['lv', 'ru']

    if lang and lang != 'all' and lang in supported_languages:
        sql = text("""
            SELECT ak.word, ak.language, ak.weight, COUNT(*) AS count
            FROM lemmatized_comments lc
            JOIN raw_comments rc ON rc.id = lc.comment_id
            CROSS JOIN LATERAL jsonb_array_elements_text(lc.lemmas) AS lemma
            JOIN aggressive_keywords ak ON ak.word = lemma
            WHERE DATE_TRUNC('day', rc.timestamp) = :request_date
              AND rc.comment_lang = :lang
            GROUP BY ak.word, ak.language, ak.weight
            ORDER BY count DESC
        """)
        rows = session.execute(sql, {"request_date": request_date, "lang": lang}).fetchall()
    else:
        sql = text("""
            SELECT ak.word, ak.language, COUNT(*) AS count
            FROM lemmatized_comments lc
            JOIN raw_comments rc ON rc.id = lc.comment_id
            CROSS JOIN LATERAL jsonb_array_elements_text(lc.lemmas) AS lemma
            JOIN aggressive_keywords ak ON ak.word = lemma
            WHERE DATE_TRUNC('day', rc.timestamp) = :request_date
              AND rc.comment_lang IN ('lv', 'ru')
            GROUP BY ak.word, ak.language, ak.weight
            ORDER BY count DESC
        """)
        rows = session.execute(sql, {"request_date": request_date}).fetchall()

    return [
        {
            'word': row.word,
            'language': row.language,
            'count': row.count,
        }
        for row in rows
    ]
