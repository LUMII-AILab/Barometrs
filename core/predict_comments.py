import time
from sqlalchemy.orm import sessionmaker
import database
from db import models, crud_utils
from db.crud import predicted_comments as pc_crud
from core import load_model

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=database.engine)
session = SessionLocal()

def process_predictions(predictions):
    flat_predictions = [item for sublist in predictions for item in sublist]
    emotion_dict = {emotion['label']: round(emotion['score'], 5) for emotion in flat_predictions}
    max_emotion = max(emotion_dict, key=emotion_dict.get)
    max_emotion_score = emotion_dict[max_emotion]

    return emotion_dict, max_emotion, max_emotion_score

def add_predictions(predicted_comment, normal_model, ekman_model, text):
    normal_prediction_result = normal_model(text)
    (predicted_comment.normal_prediction_json,
     predicted_comment.normal_prediction_emotion,
     predicted_comment.normal_prediction_score) = process_predictions(normal_prediction_result)

    ekman_prediction_result = ekman_model(text)
    (predicted_comment.ekman_prediction_json,
     predicted_comment.ekman_prediction_emotion,
     predicted_comment.ekman_prediction_score) = process_predictions(ekman_prediction_result)

    return predicted_comment


def process_comments(batch_size=100):
    # Get total number of comments
    unpredicted_comments_count = crud_utils.get_unprecited_comment_count(session)
    print(f'Total comment count: {unpredicted_comments_count}')
    processed_comment_count = 0

    lvbert_lv_go_emotion_pipeline = load_model.get_pipeline_for_model('lvbert-lv-go-emotions')
    lvbert_lv_go_emotion_ekman_pipeline = load_model.get_pipeline_for_model('lvbert-lv-go-emotions-ekman')
    rubert_ru_go_emotion_pipeline = load_model.get_pipeline_for_model('rubert-base-cased-ru-go-emotions')
    rubert_ru_go_emotion_ekman_pipeline = load_model.get_pipeline_for_model('rubert-base-cased-ru-go-emotions-ekman')

    # Paginate through raw_comments
    last_id = 0
    while True:
        start_time = time.time()
        raw_comments = crud_utils.get_raw_unpredicted_comments(session, last_id, batch_size)
        if not raw_comments:
            break

        # Predict emotions
        for raw_comment in raw_comments:
            comment_text = raw_comment.comment_text
            comment_lang = raw_comment.comment_lang

            if not comment_text or len(comment_text) == 0:
                continue

            predicted_comment = models.PredictedComment(
                comment_id=raw_comment.id,
                comment_timestamp=raw_comment.timestamp,
                article_id=raw_comment.article_id,
                text=comment_text,
                text_lang=raw_comment.comment_lang
            )

            if comment_lang == 'lv':
                predicted_comment = add_predictions(predicted_comment,
                                                    lvbert_lv_go_emotion_pipeline,
                                                    lvbert_lv_go_emotion_ekman_pipeline,
                                                    comment_text)
            elif comment_lang == 'ru':
                predicted_comment = add_predictions(predicted_comment,
                                                    rubert_ru_go_emotion_pipeline,
                                                    rubert_ru_go_emotion_ekman_pipeline,
                                                    comment_text)
            else:
                continue

            pc_crud.create_predicted_comment(session, predicted_comment)
            processed_comment_count += 1

        session.commit()

        # Update last_id to the id of the last processed comment
        last_id = raw_comments[-1].id

        end_time = time.time()
        print(
            f'Processed: {processed_comment_count} out of {unpredicted_comments_count}. Time spend: {end_time - start_time} seconds.'
        )

if __name__ == '__main__':
    predict_start_time = time.time()
    print('Processing comments...')
    process_comments()
    predict_end_time = time.time()
    print(f'Processing comments took {predict_end_time - predict_start_time} seconds')