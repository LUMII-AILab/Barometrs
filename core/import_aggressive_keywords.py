import os
import re
from collections import Counter
import pandas as pd
from sqlalchemy.orm import sessionmaker
from db import database, models

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=database.engine)

CSV_PATH = os.path.join(os.path.dirname(__file__), 'data', 'aggressive_keywords.csv')

CATEGORY_COLUMNS = ['DISKRIM', 'LAMUV', 'NETAISN', 'AICIN', 'DARB', 'PERS', 'ASOC', 'MILIT', 'NOSOD', 'EMOC', 'NODEV']

CYRILLIC_RE = re.compile(r'[а-яёА-ЯЁ]')

def detect_word_language(word: str) -> str:
    return 'ru' if CYRILLIC_RE.search(word) else 'lv'

def build_frequency_map(session, language: str) -> Counter:
    """Return a Counter of lemma → total appearances across lemmatized comments for the given language."""
    print(f'Building frequency map for language={language}...')
    rows = (
        session.query(models.LemmatizedComment.lemmas)
        .join(models.Comment, models.LemmatizedComment.comment_id == models.Comment.id)
        .filter(models.Comment.comment_lang == language)
        .all()
    )
    counter: Counter = Counter()
    for (lemmas,) in rows:
        if lemmas:
            counter.update(lemmas)
    print(f'  Processed {len(rows)} lemmatized comments, {sum(counter.values())} total lemma tokens.')
    return counter

def import_keywords():
    session = SessionLocal()
    try:
        existing = session.query(models.AggressiveKeyword).count()
        if existing > 0:
            print(f'Table already has {existing} keywords. Truncating before re-import.')
            session.query(models.AggressiveKeyword).delete()
            session.commit()

        freq_lv = build_frequency_map(session, 'lv')
        freq_ru = build_frequency_map(session, 'ru')

        df = pd.read_csv(CSV_PATH)
        print(f'Read {len(df)} keywords from {CSV_PATH}')

        records = []
        for _, row in df.iterrows():
            word = row['word']
            lang = detect_word_language(word)
            freq_map = freq_ru if lang == 'ru' else freq_lv
            records.append({
                'word':      word,
                'language':  lang,
                'weight':    row['weight'],
                'frequency': freq_map[word.lower()],
                'category_diskrim': bool(row['DISKRIM']),
                'category_lamuv':   bool(row['LAMUV']),
                'category_netaisn': bool(row['NETAISN']),
                'category_aicin':   bool(row['AICIN']),
                'category_darb':    bool(row['DARB']),
                'category_pers':    bool(row['PERS']),
                'category_asoc':    bool(row['ASOC']),
                'category_milit':   bool(row['MILIT']),
                'category_nosod':   bool(row['NOSOD']),
                'category_emoc':    bool(row['EMOC']),
                'category_nodev':   bool(row['NODEV']),
            })

        session.bulk_insert_mappings(models.AggressiveKeyword, records)
        session.commit()
        print(f'Inserted {len(records)} keywords into aggressive_keywords.')
    finally:
        session.close()

if __name__ == '__main__':
    import_keywords()
