import time
from datetime import timedelta
from sqlalchemy.orm import sessionmaker
from sqlalchemy import cast, Date
from sklearn.feature_extraction.text import CountVectorizer
from tqdm import tqdm
from db import database
from core import load_model
from db import models
import pandas as pd

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=database.engine)
session = SessionLocal()
supported_languages = ['lv', 'ru']


def extract_keywords_from_comments():
    processed = {
        (row[0], row[1], row[2])
        for row in session.query(
            cast(models.EmotionKeywordsByDay.date, Date),
            models.EmotionKeywordsByDay.language,
            models.EmotionKeywordsByDay.prediction_type,
        ).all()
    }

    all_dates = sorted(
        row[0]
        for row in session.query(
            cast(models.PredictedComment.comment_timestamp, Date)
        ).filter(
            models.PredictedComment.text_lang.in_(supported_languages),
            models.PredictedComment.ekman_prediction_emotion != '',
        ).distinct().all()
    )

    kb_lvbert_ekman = load_model.get_keybert_model_by_language_and_prediction_type('lv', 'ekman')
    kb_rubert_ekman = load_model.get_keybert_model_by_language_and_prediction_type('ru', 'ekman')

    lv_stopwords = load_model.get_stopwords('lv')
    ru_stopwords = load_model.get_stopwords('ru')

    prediction_configurations = [
        ('ekman', 'lv', kb_lvbert_ekman, lv_stopwords),
        ('ekman', 'ru', kb_rubert_ekman, ru_stopwords),
    ]

    for date in tqdm(all_dates, desc='dates', unit='day'):
        if all((date, lang, pred_type) in processed for pred_type, lang, _, _ in prediction_configurations):
            continue

        rows = session.query(
            models.LemmatizedComment.lemmas,
            models.PredictedComment.text_lang,
            models.PredictedComment.ekman_prediction_emotion,
        ).join(
            models.LemmatizedComment,
            models.PredictedComment.comment_id == models.LemmatizedComment.comment_id,
        ).filter(
            models.PredictedComment.comment_timestamp >= date,
            models.PredictedComment.comment_timestamp < date + timedelta(days=1),
            models.PredictedComment.text_lang.in_(supported_languages),
            models.PredictedComment.ekman_prediction_emotion != '',
        ).all()

        date_df = pd.DataFrame(rows, columns=['lemmas', 'text_lang', 'ekman_emotion'])
        date_df['lemma_text'] = date_df['lemmas'].apply(lambda l: ' '.join(l) if l else '')

        for prediction_type, lang, kb_model, stopword_list in prediction_configurations:
            if (date, lang, prediction_type) in processed:
                continue

            emotion_col = prediction_type + '_emotion'
            docs_by_emotion = (
                date_df[date_df['text_lang'] == lang]
                .groupby(emotion_col)['lemma_text']
                .agg(' '.join)
            )

            if docs_by_emotion.empty:
                continue

            emotions = docs_by_emotion.index.tolist()
            docs = docs_by_emotion.tolist()

            vectorizer = CountVectorizer(
                ngram_range=(1, 3),
                stop_words=stopword_list,
                max_features=5000,
            )

            all_keywords = kb_model.extract_keywords(docs, vectorizer=vectorizer, top_n=30)
            keywords_dict = dict(zip(emotions, all_keywords))

            session.add(models.EmotionKeywordsByDay(
                date=date,
                language=lang,
                prediction_type=prediction_type,
                keywords_json=keywords_dict,
            ))
            session.commit()


if __name__ == '__main__':
    predict_start_time = time.time()
    print('Processing comments for keyword extraction...')
    extract_keywords_from_comments()
    predict_end_time = time.time()
    print(f'Keyword extraction took {predict_end_time - predict_start_time:.1f}s')
