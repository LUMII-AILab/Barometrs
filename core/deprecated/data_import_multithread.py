import csv
import gzip
import os
import queue
import threading
import time

import fasttext
import pandas as pd
from sqlalchemy.orm import sessionmaker

import database
from db import crud_utils
from path_config import data_path, models_path
import torch
from core import load_model

new_delfi_data = data_path('delfi-new')
old_delfi_data = data_path('delfi-old/delfi')
years_to_process = ['2023', '2024']

# Session placeholder
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=database.engine)

# Load the language detection model
language_detection_model = fasttext.load_model(models_path('lid.176.bin'))

# add type hints
lvbert_model, lvbert_tokenizer = load_model.get_embedding_model_and_tokenizer('lvbert')
rubert_model, rubert_tokenizer = load_model.get_embedding_model_and_tokenizer('rubert-base-cased')

def determine_text_language(text_str):
    lang_code, probability = language_detection_model.predict(text_str.replace('\n', ' '), k=1)

    if lang_code[0] == '__label__lv':
        return 'lv'
    elif lang_code[0] == '__label__en':
        return 'en'
    elif lang_code[0] == '__label__ru':
        return 'ru'
    else:
        # It seems that usual case for this transliteration from English to Russian
        return 'other'

def get_embedding(model, tokenizer, text):
    # TODO: Determine the device dynamically based on CUDA availability
    encoded_input = tokenizer(text, return_tensors='pt', padding=True, truncation=True, max_length=512)
    with torch.no_grad():
        outputs = model(**encoded_input)
    embeddings = outputs.last_hidden_state[:, 0, :]  # taking the first token ([CLS] in BERT)
    return embeddings.squeeze().tolist()

def get_text_embedding_by_language(text, lang):
    if lang == 'lv':
        embedding = get_embedding(lvbert_model, lvbert_tokenizer, text)
    elif lang == 'ru':
        embedding = get_embedding(rubert_model, rubert_tokenizer, text)
    else:
        embedding = None

    return embedding


def log_import(table_name, base_filename, status, notes, session):
    # Rewrite the above code to use the session object
    if table_name == 'log_raw_articles_imports':
        crud_utils.create_log_raw_articles_import(session, base_filename, status, notes)
    elif table_name == 'log_raw_comments_imports':
        crud_utils.create_log_raw_comments_import(session, base_filename, status, notes)

def get_base_filename(file_path):
    return os.path.basename(file_path)


def create_df_from_file(file_path, columns):
    try:
        if file_path.endswith('.gz'):
            with gzip.open(file_path, 'rt', encoding='utf-8') as file:
                df = pd.read_csv(file, sep='\t', header=None, on_bad_lines='skip', quoting=csv.QUOTE_NONE)
        else:
            df = pd.read_csv(file_path, sep='\t', header=None, on_bad_lines='skip', quoting=csv.QUOTE_NONE)
    except Exception as e:
        raise e

    df.columns = columns

    return df


def process_comment_file(file_path, session):
    table_name = 'raw_comments'
    tracking_table = 'log_raw_comments_imports'
    columns = ['region', 'article_id', 'user_nickname', 'encoded_ip', 'timestamp', 'comment_text']
    filename = get_base_filename(file_path)

    try:
        df = create_df_from_file(file_path, columns)

        # Add language column
        df['comment_lang'] = df['comment_text'].apply(determine_text_language)

        # Bulk insert data into the database
        crud_utils.bulk_insert_comments(df, session)

        print(f"Data from {file_path} has been inserted into {table_name}")
        log_import(tracking_table, filename, "Success", "File imported successfully.", session)
    except Exception as e:
        session.rollback()
        print(f"Error processing file {file_path}: {e}")
        log_import(tracking_table, filename, "Failed", str(e), session)

    return


def process_article_file(file_path, session):
    table_name = 'raw_articles'
    tracking_table = 'log_raw_articles_imports'
    columns = ['region', 'article_id', 'headline', 'pub_timestamp', 'url']
    filename = get_base_filename(file_path)

    try:
        df = create_df_from_file(file_path, columns)

        # Add language column
        headline_lang_column = df['headline'].apply(determine_text_language)
        df.insert(3, 'headline_lang', headline_lang_column)

        # Remove articles with duplicate article_id
        df = df.drop_duplicates(subset='article_id')

        # Add embedding column
        df['embedding'] = df['headline'].apply(lambda x: get_text_embedding_by_language(x, determine_text_language(x)))

        # Insert data into the database
        crud_utils.bulk_insert_articles(df, session)

        # Log the import
        print(f"Data from {file_path} has been inserted into {table_name}")
        log_import(tracking_table, filename, "Success", "File imported successfully.", session)
    except Exception as e:
        session.rollback()
        print(f"Error processing file {file_path}: {e}")
        log_import(tracking_table, filename, "Failed", str(e), session)

    return


def process_file(file_path, session):
    # print(f"Processing {file_path}")
    if 'meta' in file_path:
        process_article_file(file_path, session)
    else:
        process_comment_file(file_path, session)

def thread_worker(file_queue):
    session = SessionLocal()
    try:
        while True:
            filepath = file_queue.get_nowait()
            process_file(filepath, session)
            file_queue.task_done()
    except queue.Empty:
        print("No more files to process.")
    except Exception as e:
        print(f"Unhandled error: {e}")
    finally:
        session.close()

def distribute_files_with_threads(directory):
    session = SessionLocal()
    processed_article_file_list = crud_utils.get_processed_article_files(session)
    processed_comment_file_list = crud_utils.get_processed_comment_files(session)
    excluded_files = processed_article_file_list + processed_comment_file_list
    sorted_filenames = sorted(os.listdir(directory))

    files_to_process = [
        os.path.join(directory, filename) for filename in sorted_filenames
        if filename not in excluded_files
           and (filename.endswith('.txt') or filename.endswith('.txt.gz'))
           and any(year in filename for year in years_to_process)
    ]

    file_queue = queue.Queue()

    for file in files_to_process:
        file_queue.put(file)

    threads = [threading.Thread(target=thread_worker, args=(file_queue,))
               for _ in range(min(4, file_queue.qsize()))]  # Limiting the number of threads

    for thread in threads:
        thread.start()

    file_queue.join()

    for thread in threads:
        thread.join()


if __name__ == "__main__":
    start_time = time.time()
    distribute_files_with_threads(new_delfi_data)
    distribute_files_with_threads(old_delfi_data)
    end_time = time.time()
    print(f"Processing new data took {end_time - start_time} seconds")