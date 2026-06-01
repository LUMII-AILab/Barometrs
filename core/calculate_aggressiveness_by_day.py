import time
import pandas as pd
from sqlalchemy.orm import sessionmaker
from sqlalchemy import cast, Date, extract
from tqdm import tqdm
from db import database, models

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=database.engine)

SUPPORTED_LANGUAGES = ['lv', 'ru']
WEBSITES = ['tvnet', 'delfi', 'apollo']


def calculate_aggressiveness():
    session = SessionLocal()
    try:
        aggressive_weights = {
            row.word: row.weight
            for row in session.query(models.AggressiveKeyword).all()
        }
        print(f'Loaded {len(aggressive_weights)} aggressive keywords')

        already_processed = {
            (row[0], row[1], row[2]) for row in session.query(
                cast(models.AggressivenessByDay.date, Date),
                models.AggressivenessByDay.language,
                models.AggressivenessByDay.website,
            ).all()
        }
        print(f'Already processed (date, lang, website) triples: {len(already_processed)}')

        for lang in SUPPORTED_LANGUAGES:
            months = (
                session.query(
                    extract('year', models.Comment.timestamp).label('year'),
                    extract('month', models.Comment.timestamp).label('month'),
                )
                .join(models.LemmatizedComment, models.LemmatizedComment.comment_id == models.Comment.id)
                .filter(models.Comment.comment_lang == lang)
                .distinct()
                .order_by('year', 'month')
                .all()
            )

            tqdm.write(f'\nLanguage: {lang} — {len(months)} months to process')

            for year, month in tqdm(months, desc=f'{lang}'):
                rows = (
                    session.query(
                        models.LemmatizedComment.lemmas,
                        models.LemmatizedComment.lemma_count,
                        cast(models.Comment.timestamp, Date).label('comment_date'),
                        models.Comment.website,
                    )
                    .join(models.Comment, models.LemmatizedComment.comment_id == models.Comment.id)
                    .filter(
                        models.Comment.comment_lang == lang,
                        extract('year', models.Comment.timestamp) == year,
                        extract('month', models.Comment.timestamp) == month,
                    )
                    .all()
                )

                df = pd.DataFrame(rows, columns=['lemmas', 'lemma_count', 'comment_date', 'website'])
                df['comment_date'] = pd.to_datetime(df['comment_date']).dt.date

                scopes = [(website, df[df['website'] == website]) for website in WEBSITES]
                scopes.append(('all', df))

                for scope_name, scope_df in scopes:
                    for date in scope_df['comment_date'].unique():
                        if (date, lang, scope_name) in already_processed:
                            continue

                        day_df = scope_df[scope_df['comment_date'] == date]
                        total_word_count = int(day_df['lemma_count'].sum())
                        aggressive_word_count = 0
                        aggressive_word_weight_sum = 0.0

                        for lemmas in day_df['lemmas']:
                            if not lemmas:
                                continue
                            for lemma in lemmas:
                                w = aggressive_weights.get(lemma)
                                if w is not None:
                                    aggressive_word_count += 1
                                    aggressive_word_weight_sum += w

                        ratio = aggressive_word_count / total_word_count if total_word_count > 0 else 0.0
                        weighted_ratio = aggressive_word_weight_sum / total_word_count if total_word_count > 0 else 0.0

                        session.add(models.AggressivenessByDay(
                            date=date,
                            language=lang,
                            website=scope_name,
                            aggressive_word_count=aggressive_word_count,
                            aggressive_word_weight_sum=aggressive_word_weight_sum,
                            total_word_count=total_word_count,
                            aggressiveness_ratio=ratio,
                            weighted_aggressiveness_ratio=weighted_ratio,
                        ))
                        already_processed.add((date, lang, scope_name))

                session.commit()

        print('\nDone.')
    finally:
        session.close()


if __name__ == '__main__':
    t_start = time.time()
    print('Calculating aggressiveness by day...')
    calculate_aggressiveness()
    print(f'Finished in {time.time() - t_start:.1f}s')
