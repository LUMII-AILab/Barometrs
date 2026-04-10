import time
import stanza
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import insert
from db import database, models

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=database.engine)

BATCH_SIZE = 500
SUPPORTED_LANGUAGES = ['lv', 'ru']


def get_stanza_pipeline(lang: str) -> stanza.Pipeline:
    return stanza.Pipeline(lang, processors='tokenize,lemma', use_gpu=True, verbose=False)


def lemmatize_batch(nlp: stanza.Pipeline, comments: list) -> list[dict]:
    docs = [stanza.Document([], text=comment.comment_text or '') for comment in comments]
    processed = nlp(docs)
    results = []
    for comment, doc in zip(comments, processed):
        lemmas = [
            word.lemma.lower()
            for sentence in doc.sentences
            for word in sentence.words
            if word.lemma
            and word.upos not in ('PUNCT', 'SYM', 'X', 'NUM')
            and word.lemma.isalpha() # drops punctuation, numbers, emoticon fragments
        ]
        results.append({
            'comment_id': comment.id,
            'lemmas': lemmas,
            'lemma_count': len(lemmas),
        })
    return results


def lemmatize_comments():
    session = SessionLocal()
    try:
        for lang in SUPPORTED_LANGUAGES:
            print(f'\nLoading Stanza pipeline for language: {lang}')
            nlp = get_stanza_pipeline(lang)

            last_id = 0
            total = 0
            while True:
                batch = (
                    session.query(models.RawComment)
                    .outerjoin(
                        models.LemmatizedComment,
                        models.LemmatizedComment.comment_id == models.RawComment.id
                    )
                    .filter(
                        models.RawComment.comment_lang == lang,
                        models.RawComment.id > last_id,
                        models.LemmatizedComment.comment_id == None,
                    )
                    .order_by(models.RawComment.id)
                    .limit(BATCH_SIZE)
                    .all()
                )

                if not batch:
                    break

                t0 = time.time()
                rows = lemmatize_batch(nlp, batch)
                session.execute(insert(models.LemmatizedComment), rows)
                session.commit()

                last_id = batch[-1].id
                total += len(batch)
                print(f'  [{lang}] Processed {total} comments (batch in {time.time() - t0:.1f}s)')

            print(f'  [{lang}] Done. Total processed: {total}')
    finally:
        session.close()


if __name__ == '__main__':
    t_start = time.time()
    print('Starting comment lemmatization...')
    lemmatize_comments()
    print(f'\nFinished in {time.time() - t_start:.1f}s')