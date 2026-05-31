from collections import defaultdict
from datetime import date
from sqlalchemy import func, text, cast, Date
from sqlalchemy.orm import Session
from db import models


def get_aggressiveness_by_period(session: Session, language: str, start_date: date, end_date: date, group_by: str):
    trunc = {'month': 'month', 'week': 'week'}.get(group_by, 'day')
    period = func.date_trunc(trunc, models.AggressivenessByDay.date).label('date')
    weight_sum = func.sum(models.AggressivenessByDay.aggressive_word_weight_sum).label('aggressive_word_weight_sum')
    word_count = func.sum(models.AggressivenessByDay.aggressive_word_count).label('aggressive_word_count')
    total_count = func.sum(models.AggressivenessByDay.total_word_count).label('total_word_count')

    rows = (
        session.query(period, weight_sum, word_count, total_count)
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
            'aggressive_word_count': row.aggressive_word_count,
            'aggressive_word_weight_sum': row.aggressive_word_weight_sum,
            'total_word_count': row.total_word_count,
            'unweighted_aggressiveness_ratio': (
                row.aggressive_word_count / row.total_word_count * 100 if row.total_word_count else 0
            ),
            'weighted_aggressiveness_ratio': (
                row.aggressive_word_weight_sum / row.total_word_count * 100 if row.total_word_count else 0
            ),
        }
        for row in rows
    ]


def get_aggressiveness_by_period_per_website(session: Session, start_date: date, end_date: date, group_by: str):
    trunc = {'month': 'month', 'week': 'week'}.get(group_by, 'day')
    period = func.date_trunc(trunc, models.AggressivenessByDay.date).label('date')
    language_col = models.AggressivenessByDay.language
    website_col = models.AggressivenessByDay.website
    weight_sum = func.sum(models.AggressivenessByDay.aggressive_word_weight_sum).label('aggressive_word_weight_sum')
    word_count = func.sum(models.AggressivenessByDay.aggressive_word_count).label('aggressive_word_count')
    total_count = func.sum(models.AggressivenessByDay.total_word_count).label('total_word_count')

    rows = (
        session.query(period, language_col, website_col, weight_sum, word_count, total_count)
        .filter(
            models.AggressivenessByDay.language.in_(['lv', 'ru']),
            models.AggressivenessByDay.website.in_(['tvnet', 'apollo', 'delfi']),
            models.AggressivenessByDay.date >= start_date,
            models.AggressivenessByDay.date <= end_date,
        )
        .group_by(period, language_col, website_col)
        .order_by(language_col, website_col, period)
        .all()
    )

    result = {}
    for row in rows:
        lang = row.language
        site = row.website
        result.setdefault(lang, {}).setdefault(site, []).append({
            'date': row.date.strftime('%Y-%m-%d'),
            'unweighted_aggressiveness_ratio': (
                row.aggressive_word_count / row.total_word_count * 100 if row.total_word_count else 0
            ),
        })
    return result


def get_aggressiveness_by_period_precomputed(session: Session, request_date: date, lang: str):
    supported_languages = ['lv', 'ru']

    if lang and lang != 'all' and lang in supported_languages:
        sql = text("""
            SELECT ak.word, ak.language, ak.weight, COUNT(*) AS count
            FROM lemmatized_comments lc
            JOIN comments rc ON rc.id = lc.comment_id
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
            JOIN comments rc ON rc.id = lc.comment_id
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


def get_aggressive_keywords_by_day_precomputed(session: Session, request_date: date, lang: str, website: str = 'all'):
    row = (
        session.query(models.AggressiveKeywordsByDay)
        .filter(
            func.date_trunc('day', models.AggressiveKeywordsByDay.date) == request_date,
            models.AggressiveKeywordsByDay.language == lang,
            models.AggressiveKeywordsByDay.website == website,
        )
        .first()
    )
    if not row or not row.keywords_json:
        return []

    return sorted(
        [
            {
                'word': word,
                'language': lang,
                'count': v['count'],
                'weight_sum': v['weight_sum'],
                'article_count': v.get('article_count', 0),
                'forms': v.get('forms', {}),
            }
            for word, v in row.keywords_json.items()
        ],
        key=lambda x: x['count'],
        reverse=True,
    )


def get_aggressive_keywords_by_period(session: Session, start_date: date, end_date: date, lang: str, website: str = 'all'):
    rows = (
        session.query(models.AggressiveKeywordsByDay)
        .filter(
            models.AggressiveKeywordsByDay.language == lang,
            models.AggressiveKeywordsByDay.website == website,
            models.AggressiveKeywordsByDay.date >= start_date,
            models.AggressiveKeywordsByDay.date <= end_date,
        )
        .all()
    )

    merged = defaultdict(lambda: {
        'count': 0,
        'weight_sum': 0.0,
        'forms': defaultdict(int),
        'article_ids': set(),
    })
    for row in rows:
        if not row.keywords_json:
            continue
        for word, v in row.keywords_json.items():
            m = merged[word]
            m['count'] += v['count']
            m['weight_sum'] += v['weight_sum']
            for form, cnt in v.get('forms', {}).items():
                m['forms'][form] += cnt
            m['article_ids'].update(v.get('article_ids', []))

    return sorted(
        [
            {
                'word': word,
                'count': v['count'],
                'weight_sum': v['weight_sum'],
                'article_count': len(v['article_ids']),
                'forms': dict(v['forms']),
            }
            for word, v in merged.items()
        ],
        key=lambda x: x['count'],
        reverse=True,
    )


def get_aggressive_keywords_dates(session: Session, start_date: date, end_date: date, lang: str, website: str = 'all'):
    rows = (
        session.query(cast(models.AggressiveKeywordsByDay.date, Date).label('d'))
        .filter(
            models.AggressiveKeywordsByDay.language == lang,
            models.AggressiveKeywordsByDay.website == website,
            models.AggressiveKeywordsByDay.date >= start_date,
            models.AggressiveKeywordsByDay.date <= end_date,
        )
        .order_by(models.AggressiveKeywordsByDay.date.desc())
        .all()
    )
    return [str(r.d) for r in rows]


def get_aggressive_keyword_articles(
    session: Session,
    lemma: str,
    start_date: date,
    end_date: date,
    lang: str,
    website: str = 'all',
):
    rows = (
        session.query(models.AggressiveKeywordsByDay)
        .filter(
            models.AggressiveKeywordsByDay.language == lang,
            models.AggressiveKeywordsByDay.website == website,
            models.AggressiveKeywordsByDay.date >= start_date,
            models.AggressiveKeywordsByDay.date <= end_date,
        )
        .all()
    )

    article_ids = set()
    for row in rows:
        if row.keywords_json and lemma in row.keywords_json:
            article_ids.update(row.keywords_json[lemma].get('article_ids', []))

    if not article_ids:
        return []

    articles = (
        session.query(models.Article)
        .filter(models.Article.article_id.in_(article_ids))
        .order_by(models.Article.pub_timestamp.desc())
        .all()
    )

    return [
        {
            'article_id': a.article_id,
            'headline': a.headline,
            'url': a.url,
            'website': a.website,
            'pub_timestamp': a.pub_timestamp.strftime('%Y-%m-%d') if a.pub_timestamp else None,
        }
        for a in articles
    ]


def get_all_aggressive_keywords(session: Session):
    rows = (
        session.query(models.AggressiveKeyword)
        .order_by(models.AggressiveKeyword.language, models.AggressiveKeyword.word)
        .all()
    )
    return [
        {
            'word': row.word,
            'language': row.language,
            'weight': row.weight,
            'frequency': row.frequency,
            'category_diskrim': row.category_diskrim,
            'category_lamuv': row.category_lamuv,
            'category_netaisn': row.category_netaisn,
            'category_aicin': row.category_aicin,
            'category_darb': row.category_darb,
            'category_pers': row.category_pers,
            'category_asoc': row.category_asoc,
            'category_milit': row.category_milit,
            'category_nosod': row.category_nosod,
            'category_emoc': row.category_emoc,
            'category_nodev': row.category_nodev,
        }
        for row in rows
    ]
