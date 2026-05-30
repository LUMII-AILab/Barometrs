import time
from collections import defaultdict
from itertools import groupby

import pandas as pd
from sqlalchemy import cast, Date
from sqlalchemy.orm import sessionmaker
from tqdm import tqdm

from db import database, models

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=database.engine)

SUPPORTED_LANGUAGES = ['lv', 'ru']
WEBSITES = ['tvnet', 'delfi', 'apollo']
CHUNK_MONTHS = 1


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
                cast(models.AggressiveKeywordsByDay.date, Date),
                models.AggressiveKeywordsByDay.language,
                models.AggressiveKeywordsByDay.website,
            ).all()
        }
        print(f'Already processed (date, lang, website) triples: {len(already_processed)}')

        for lang in SUPPORTED_LANGUAGES:
            all_dates = sorted({
                r.comment_date for r in session.query(
                    cast(models.Comment.timestamp, Date).label('comment_date')
                )
                .join(models.LemmatizedComment, models.LemmatizedComment.comment_id == models.Comment.id)
                .filter(models.Comment.comment_lang == lang)
                .distinct()
                .all()
            })

            # Group dates by (year, month), then batch into CHUNK_MONTHS-sized groups
            by_month = [
                list(dates)
                for _, dates in groupby(all_dates, key=lambda d: (d.year, d.month))
            ]
            chunks = [
                [d for month in by_month[i:i + CHUNK_MONTHS] for d in month]
                for i in range(0, len(by_month), CHUNK_MONTHS)
            ]
            print(f'\n[{lang}] {len(all_dates)} dates → {len(chunks)} chunks of {CHUNK_MONTHS} month(s)')

            for chunk in tqdm(chunks, desc=f'[{lang}]', unit='month'):
                rows = (
                    session.query(
                        models.LemmatizedComment.lemmas,
                        models.LemmatizedComment.words,
                        models.LemmatizedComment.lemma_count,
                        cast(models.Comment.timestamp, Date).label('comment_date'),
                        models.Comment.website,
                        models.Comment.article_id,
                    )
                    .join(models.Comment, models.LemmatizedComment.comment_id == models.Comment.id)
                    .filter(
                        models.Comment.comment_lang == lang,
                        cast(models.Comment.timestamp, Date) >= chunk[0],
                        cast(models.Comment.timestamp, Date) <= chunk[-1],
                    )
                    .all()
                )

                df = pd.DataFrame(rows, columns=['lemmas', 'words', 'lemma_count', 'comment_date', 'website', 'article_id'])
                df['comment_date'] = pd.to_datetime(df['comment_date']).dt.date

                scopes = [(website, df[df['website'] == website]) for website in WEBSITES]
                scopes.append(('all', df))

                for scope_name, scope_df in scopes:
                    for date in chunk:
                        if (date, lang, scope_name) in already_processed:
                            continue

                        day_df = scope_df[scope_df['comment_date'] == date]
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
