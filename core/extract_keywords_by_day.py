import time
from sqlalchemy.orm import sessionmaker
import database
from sqlalchemy import cast, Date
from core import load_model
from db import models
import pandas as pd

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=database.engine)
session = SessionLocal()
supported_languages = ['lv', 'ru']

def extract_keywords_from_comments():
    query = session.query(
        models.PredictedComment.text.label('comment_text'),
        models.PredictedComment.text_lang.label('text_lang'),
        cast(models.PredictedComment.comment_timestamp, Date).label('comment_date'),
        models.PredictedComment.normal_prediction_emotion.label('normal_emotion'),
        models.PredictedComment.ekman_prediction_emotion.label('ekman_emotion'),
    ).filter(
        models.PredictedComment.text_lang.in_(supported_languages),
        models.PredictedComment.normal_prediction_emotion != '',
        models.PredictedComment.ekman_prediction_emotion != '',
        cast(models.PredictedComment.comment_timestamp, Date) >= '2023-01-01'
    )

    results = query.all()

    df = pd.DataFrame(results, columns=['comment_text', 'text_lang', 'comment_date', 'normal_emotion', 'ekman_emotion'])

    # order comments by date
    df = df.sort_values(by='comment_date')

    def extract_keywords(model, text, stopword_list=None):
        keywords = model.extract_keywords(text, stop_words=stopword_list, keyphrase_ngram_range=(2, 2), top_n=5)
        return keywords

    kb_lvbert_normal = load_model.get_keybert_model_by_language_and_prediction_type('lv', 'normal')
    kb_lvbert_ekman = load_model.get_keybert_model_by_language_and_prediction_type('lv', 'ekman')
    kb_rubert_normal = load_model.get_keybert_model_by_language_and_prediction_type('ru', 'normal')
    kb_rubert_ekman = load_model.get_keybert_model_by_language_and_prediction_type('ru', 'ekman')

    lv_stopwords = load_model.get_stopwords('lv')
    ru_stopwords = load_model.get_stopwords('ru')

    prediction_configurations = [
        ('normal', 'lv', kb_lvbert_normal, lv_stopwords),
        ('ekman', 'lv', kb_lvbert_ekman, lv_stopwords),
        ('normal', 'ru', kb_rubert_normal, ru_stopwords),
        ('ekman', 'ru', kb_rubert_ekman, ru_stopwords)
    ]

    processed_dates = session.query(models.EmotionKeywordsByDay.date).all()
    processed_dates = set(processed_dates)

    # For each day, extract keywords for each emotion and each language
    for date in df['comment_date'].unique():
        start = time.time()

        if (date,) in processed_dates:
            print(f'Skipping {date} as it has already been processed')
            continue

        date_df = df[df['comment_date'] == date]

        for prediction_type, lang, kb_model, stopword_list in prediction_configurations:
            concat_text = date_df[(date_df['text_lang'] == lang) & (date_df[prediction_type + '_emotion'] != '')].groupby(prediction_type + '_emotion')['comment_text'].agg(lambda texts: ' '.join(texts))
            emotion_keywords = concat_text.apply(lambda text: extract_keywords(kb_model, text, stopword_list))

            keywords_df = emotion_keywords.reset_index()
            keywords_df.columns = ['emotion', 'keywords']

            keywords_dict = keywords_df.set_index('emotion').to_dict()['keywords']

            emotion_keywords = models.EmotionKeywordsByDay(
                date=date,
                language=lang,
                prediction_type=prediction_type,
                keywords_json=keywords_dict
            )
            session.add(emotion_keywords)

        session.commit()

        end = time.time()
        print(f'Processed {date} in {end - start} seconds')

if __name__ == '__main__':
    predict_start_time = time.time()
    print('Processing comments for keyword extraction...')
    extract_keywords_from_comments()
    predict_end_time = time.time()
    print(f'Keyword extraction took {predict_end_time - predict_start_time} seconds')