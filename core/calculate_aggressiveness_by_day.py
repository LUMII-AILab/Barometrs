import time
import pandas as pd
from sqlalchemy.orm import sessionmaker
from sqlalchemy import cast, Date
from db import database, models

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=database.engine)

SUPPORTED_LANGUAGES = ['lv', 'ru']

# High memory usage but x3 times faster than doing it in SQL for each day+language
# Expect ~10GB of RAM, it should run in ~5 minutes on a decent machine for comments from 2020-01-01 to 2024-06-30
def calculate_aggressiveness():
    session = SessionLocal()
    try:
        # Load aggressive keyword weights into memory
        aggressive_weights = {
            row.word: row.weight
            for row in session.query(models.AggressiveKeyword).all()
        }
        print(f'Loaded {len(aggressive_weights)} aggressive keywords')

        already_processed = {
            (row[0], row[1]) for row in session.query(
                cast(models.AggressivenessByDay.date, Date),
                models.AggressivenessByDay.language,
            ).all()
        }
        print(f'Already processed (date, lang) pairs: {len(already_processed)}')

        for lang in SUPPORTED_LANGUAGES:
            print(f'\nQuerying lemmatized comments for language: {lang}')
            rows = (
                session.query(
                    models.LemmatizedComment.lemmas,
                    models.LemmatizedComment.lemma_count,
                    cast(models.Comment.timestamp, Date).label('comment_date'),
                )
                .join(models.Comment, models.LemmatizedComment.comment_id == models.Comment.id)
                .filter(
                    models.Comment.comment_lang == lang,
                    cast(models.Comment.timestamp, Date) >= '2020-01-01',
                )
                .all()
            )

            df = pd.DataFrame(rows, columns=['lemmas', 'lemma_count', 'comment_date'])
            df['comment_date'] = pd.to_datetime(df['comment_date']).dt.date
            df = df.sort_values('comment_date')

            print(f'  {len(df)} lemmatized comments loaded')

            for date in df['comment_date'].unique():
                if (date, lang) in already_processed:
                    print(f'  Skipping {date}/{lang} (already processed)')
                    continue

                t0 = time.time()
                day_df = df[df['comment_date'] == date]

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
                    aggressive_word_count=aggressive_word_count,
                    aggressive_word_weight_sum=aggressive_word_weight_sum,
                    total_word_count=total_word_count,
                    aggressiveness_ratio=ratio,
                    weighted_aggressiveness_ratio=weighted_ratio,
                ))
                already_processed.add((date, lang))

                print(f'  {date} | total={total_word_count} aggressive={aggressive_word_count} weight_sum={aggressive_word_weight_sum:.4f} ratio={ratio:.4f} weighted_ratio={weighted_ratio:.4f} ({time.time()-t0:.2f}s)')

            session.commit()

        print('\nDone.')
    finally:
        session.close()


if __name__ == '__main__':
    t_start = time.time()
    print('Calculating aggressiveness by day...')
    calculate_aggressiveness()
    print(f'Finished in {time.time() - t_start:.1f}s')
