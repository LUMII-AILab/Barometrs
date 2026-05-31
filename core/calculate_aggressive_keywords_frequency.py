from collections import Counter
from sqlalchemy.orm import sessionmaker
from tqdm import tqdm
from db import database, models

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=database.engine)

BATCH_SIZE = 50_000


def build_frequency_map(session, language: str) -> Counter:
    total = (
        session.query(models.LemmatizedComment)
        .join(models.Comment, models.LemmatizedComment.comment_id == models.Comment.id)
        .filter(models.Comment.comment_lang == language)
        .count()
    )

    query = (
        session.query(models.LemmatizedComment.lemmas)
        .join(models.Comment, models.LemmatizedComment.comment_id == models.Comment.id)
        .filter(models.Comment.comment_lang == language)
        .yield_per(BATCH_SIZE)
    )

    counter: Counter = Counter()
    with tqdm(total=total, unit='comments', desc=f'frequency [{language}]') as pbar:
        for (lemmas,) in query:
            if lemmas:
                counter.update(lemmas)
            pbar.update(1)

    return counter


def calculate_frequencies():
    session = SessionLocal()
    try:
        keywords = session.query(models.AggressiveKeyword).all()
        if not keywords:
            print('No keywords found in aggressive_keywords table.')
            return

        freq_lv = build_frequency_map(session, 'lv')
        freq_ru = build_frequency_map(session, 'ru')

        for kw in keywords:
            freq_map = freq_ru if kw.language == 'ru' else freq_lv
            kw.frequency = freq_map[kw.word.lower()]

        session.commit()
        print(f'Updated frequency for {len(keywords)} keywords.')
    finally:
        session.close()


if __name__ == '__main__':
    calculate_frequencies()
