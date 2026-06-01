import time
from collections import defaultdict
from datetime import datetime

import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import sessionmaker
from tqdm import tqdm

from db import database, models

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=database.engine)

SUPPORTED_LANGUAGES = ['lv', 'ru']
WEBSITES = ['tvnet', 'delfi', 'apollo']
CHUNK_MONTHS = 1


def _iter_months(start_year, start_month, end_year, end_month):
    y, m = start_year, start_month
    while (y, m) <= (end_year, end_month):
        yield y, m
        m += 1
        if m > 12:
            m, y = 1, y + 1


def _month_chunk_range(month_chunk):
    y0, m0 = month_chunk[0]
    y1, m1 = month_chunk[-1]
    start = datetime(y0, m0, 1)
    end = datetime(y1 + 1, 1, 1) if m1 == 12 else datetime(y1, m1 + 1, 1)
    return start, end


def compute_aggressive_keywords_by_day():
    session = SessionLocal()
    try:
        aggressive_keywords = {
            row.word: row.weight
            for row in session.query(models.AggressiveKeyword).all()
        }
        print(f'Loaded {len(aggressive_keywords)} aggressive keywords')

        already_processed = {
            (row[0], row[1], row[2]) for row in session.query(
                models.AggressiveKeywordsByDay.date,
                models.AggressiveKeywordsByDay.language,
                models.AggressiveKeywordsByDay.website,
            ).all()
        }
        print(f'Already processed (date, lang, website) triples: {len(already_processed)}')

        for lang in SUPPORTED_LANGUAGES:
            min_ts, max_ts = session.query(
                func.min(models.Comment.timestamp),
                func.max(models.Comment.timestamp),
            ).join(
                models.LemmatizedComment,
                models.LemmatizedComment.comment_id == models.Comment.id,
            ).filter(models.Comment.comment_lang == lang).one()

            if min_ts is None:
                print(f'[{lang}] No data, skipping.')
                continue

            months = list(_iter_months(min_ts.year, min_ts.month, max_ts.year, max_ts.month))
            chunks = [months[i:i + CHUNK_MONTHS] for i in range(0, len(months), CHUNK_MONTHS)]
            print(f'\n[{lang}] {len(months)} months → {len(chunks)} chunks of {CHUNK_MONTHS} month(s)')

            for month_chunk in tqdm(chunks, desc=f'[{lang}]', unit='month'):
                start, end = _month_chunk_range(month_chunk)

                rows = (
                    session.query(
                        models.LemmatizedComment.lemmas,
                        models.LemmatizedComment.words,
                        models.LemmatizedComment.lemma_count,
                        models.Comment.timestamp,
                        models.Comment.website,
                        models.Comment.article_id,
                    )
                    .join(models.Comment, models.LemmatizedComment.comment_id == models.Comment.id)
                    .filter(
                        models.Comment.comment_lang == lang,
                        models.Comment.timestamp >= start,
                        models.Comment.timestamp < end,
                    )
                    .all()
                )

                df = pd.DataFrame(rows, columns=['lemmas', 'words', 'lemma_count', 'timestamp', 'website', 'article_id'])
                df['comment_date'] = pd.to_datetime(df['timestamp']).dt.date

                # Group once to avoid repeated boolean masking per scope/date
                site_date_dfs = dict(tuple(df.groupby(['website', 'comment_date'])))
                all_date_dfs = dict(tuple(df.groupby('comment_date')))
                chunk_dates = sorted(df['comment_date'].unique())

                for scope_name in WEBSITES + ['all']:
                    for date in chunk_dates:
                        if (date, lang, scope_name) in already_processed:
                            continue

                        day_df = (
                            all_date_dfs[date]
                            if scope_name == 'all'
                            else site_date_dfs.get((scope_name, date))
                        )
                        if day_df is None:
                            continue

                        total_word_count = int(day_df['lemma_count'].sum())
                        if total_word_count == 0:
                            continue

                        keyword_counts = defaultdict(lambda: {
                            'count': 0,
                            'weight_sum': 0.0,
                            'forms': defaultdict(int),
                            'article_ids': set(),
                        })

                        for lemmas, words, article_id in zip(day_df['lemmas'], day_df['words'], day_df['article_id']):
                            if not lemmas:
                                continue
                            words = words or []
                            for i, lemma in enumerate(lemmas):
                                w = aggressive_keywords.get(lemma)
                                if w is not None:
                                    kc = keyword_counts[lemma]
                                    kc['count'] += 1
                                    kc['weight_sum'] += w
                                    kc['article_ids'].add(int(article_id))
                                    if i < len(words):
                                        kc['forms'][words[i]] += 1

                        keywords_json = {
                            word: {
                                'count': v['count'],
                                'weight_sum': v['weight_sum'],
                                'forms': dict(v['forms']),
                                'article_ids': list(v['article_ids']),
                                'article_count': len(v['article_ids']),
                            }
                            for word, v in keyword_counts.items()
                        }

                        session.add(models.AggressiveKeywordsByDay(
                            date=date,
                            language=lang,
                            website=scope_name,
                            keywords_json=keywords_json,
                            total_word_count=total_word_count,
                        ))
                        already_processed.add((date, lang, scope_name))

                session.commit()

        print('\nDone.')
    finally:
        session.close()


if __name__ == '__main__':
    t_start = time.time()
    print('Computing aggressive keywords by day...')
    compute_aggressive_keywords_by_day()
    print(f'Finished in {time.time() - t_start:.1f}s')
