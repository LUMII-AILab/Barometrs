import time
from datasets import Dataset as HFDataset
from tqdm import tqdm
from transformers.pipelines.pt_utils import KeyDataset
from sqlalchemy.orm import sessionmaker
from db import models, crud_utils, database
from core import load_model

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=database.engine)
session = SessionLocal()

CHUNK_SIZE = 10_000
PIPELINE_BATCH_SIZE = 128

def process_predictions(prediction):
    emotion_dict = {emotion['label']: round(emotion['score'], 5) for emotion in prediction}
    max_emotion = max(emotion_dict, key=emotion_dict.get)
    return emotion_dict, max_emotion, emotion_dict[max_emotion]

def process_language(pipeline, lang, website=None):
    total = crud_utils.get_unpredicted_comment_count_by_lang(session, lang, website)
    if total == 0:
        print(f'[{lang}] No unpredicted comments.')
        return 0

    last_id = 0
    processed = 0

    with tqdm(total=total, desc=f'[{lang}]', unit='comment') as progress:
        while True:
            batch = crud_utils.get_unpredicted_comments_batch_by_lang(session, lang, last_id, CHUNK_SIZE, website)
            if not batch:
                break

            texts = [c.comment_text for c in batch]
            ds = HFDataset.from_dict({"text": texts})
            results = list(pipeline(KeyDataset(ds, "text"), batch_size=PIPELINE_BATCH_SIZE, truncation=True))

            objects = []
            for comment, prediction in zip(batch, results):
                emotion_dict, max_emotion, max_score = process_predictions(prediction)
                objects.append({
                    'comment_id': comment.id,
                    'comment_timestamp': comment.timestamp,
                    'article_id': comment.article_id,
                    'text': comment.comment_text,
                    'text_lang': lang,
                    'website': comment.website,
                    'ekman_prediction_json': emotion_dict,
                    'ekman_prediction_emotion': max_emotion,
                    'ekman_prediction_score': max_score,
                })

            session.bulk_insert_mappings(models.PredictedComment, objects)
            session.commit()
            processed += len(objects)
            last_id = batch[-1].id
            progress.update(len(batch))

    print(f'[{lang}] done — {processed} comments processed.')
    return processed

def process_comments():
    pipelines = {
        'lv': load_model.get_pipeline_for_model('lvbert-lv-emotions-ekman'),
        'ru': load_model.get_pipeline_for_model('rubert-base-cased-ru-go-emotions-ekman'),
    }
    for lang, pipeline in pipelines.items():
        process_language(pipeline, lang, website='delfi')

if __name__ == '__main__':
    start_time = time.time()
    print('Processing comments...')
    process_comments()
    print(f'Done in {time.time() - start_time:.1f}s')
