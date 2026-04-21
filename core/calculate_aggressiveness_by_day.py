import time
import pandas as pd
from sqlalchemy.orm import sessionmaker
from sqlalchemy import cast, Date
from db import database, models

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=database.engine)

SUPPORTED_LANGUAGES = ['lv', 'ru']


def calculate_aggressiveness():
    session = SessionLocal()
    try:
        # Load aggressive keyword weights into memory
        aggressive_set = {
            row.word
            for row in session.query(models.AggressiveKeyword).all()
        }
        print(f'Loaded {len(aggressive_set)} aggressive keywords')

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
                    cast(models.RawComment.timestamp, Date).label('comment_date'),
                )
                .join(models.RawComment, models.LemmatizedComment.comment_id == models.RawComment.id)
                .filter(
                    models.RawComment.comment_lang == lang,
                    cast(models.RawComment.timestamp, Date) >= '2020-01-01',
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

                for lemmas in day_df['lemmas']:
                    if not lemmas:
                        continue
                    for lemma in lemmas:
                        if lemma in aggressive_set:
                            aggressive_word_count += 1

                ratio = aggressive_word_count / total_word_count if total_word_count > 0 else 0.0

                session.add(models.AggressivenessByDay(
                    date=date,
                    language=lang,
                    aggressive_word_count=aggressive_word_count,
                    total_word_count=total_word_count,
                    aggressiveness_ratio=ratio,
                ))
                already_processed.add((date, lang))

                print(f'  {date} | total={total_word_count} aggressive={aggressive_word_count} ratio={ratio:.4f} ({time.time()-t0:.2f}s)')

            session.commit()

        print('\nDone.')
    finally:
        session.close()


if __name__ == '__main__':
    t_start = time.time()
    print('Calculating aggressiveness by day...')
    calculate_aggressiveness()
    print(f'Finished in {time.time() - t_start:.1f}s')
