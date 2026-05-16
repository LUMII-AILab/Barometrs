import csv
import gzip
import os
import re
import time

import math
import pandas as pd
import torch
from lingua import Language, LanguageDetectorBuilder
from sqlalchemy.orm import sessionmaker
from tqdm import tqdm

from core import load_model
from db import crud_utils, database
from path_config import data_path

# Database connection setup
new_delfi_data = data_path('delfi-new')
old_delfi_data = data_path('delfi')
apollo_data = data_path('apollo')
tvnet_data = data_path('tvnet')
years_to_process = ['2020', '2021', '2022', '2023', '2024']
CHUNK_SIZE = 1_000_000

# Session placeholder
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=database.engine)
session = SessionLocal()
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

lvbert_model, lvbert_tokenizer = load_model.get_embedding_model_and_tokenizer('lvbert')
rubert_model, rubert_tokenizer = load_model.get_embedding_model_and_tokenizer('rubert-base-cased')

processed_article_file_list = crud_utils.get_processed_article_files(session)
processed_comment_file_list = crud_utils.get_processed_comment_files(session)

_CYRILLIC = re.compile(r'[Ѐ-ӿ]')
_LATIN    = re.compile(r'[A-Za-zĀ-žā-ž]')
_lingua_detector = LanguageDetectorBuilder.from_languages(Language.LATVIAN, Language.RUSSIAN).build()
_REGION_LANG = {'rus': 'ru', 'lat': 'lv'}

def determine_text_language_lingua(text_str):
    result = _lingua_detector.detect_language_of(text_str)
    return 'ru' if result == Language.RUSSIAN else 'lv'

def determine_text_language(text_str, region=None):
    cyrillic = len(_CYRILLIC.findall(text_str))
    latin    = len(_LATIN.findall(text_str))
    total    = cyrillic + latin
    if total == 0:
        return _REGION_LANG.get(region, 'lv')
    if cyrillic / total > 0.85:
        return 'ru'
    # FastText and Lingua fail on transliterated text - for RU region assume latin text is actually Russian
    if region == 'rus':
        return 'ru'
    return determine_text_language_lingua(text_str)


def get_embedding(model, tokenizer, text):
    model.to(device)

    encoded_input = tokenizer(text, return_tensors='pt', padding=True, truncation=True, max_length=512)
    encoded_input = {key: val.to(device) for key, val in encoded_input.items()}

    with torch.no_grad():
        outputs = model(**encoded_input)

    embeddings = outputs.last_hidden_state[:, 0, :]
    return embeddings.squeeze().tolist()

def get_text_embedding_by_language(text, lang):
    if lang == 'lv':
        embedding = get_embedding(lvbert_model, lvbert_tokenizer, text)
    elif lang == 'ru':
        embedding = get_embedding(rubert_model, rubert_tokenizer, text)
    else:
        embedding = None

    return embedding


def log_import(tracking_table, base_filename, status, notes, website):
    if tracking_table == 'log_articles_imports':
        crud_utils.create_log_articles_import(session, base_filename, status, notes, website)
    elif tracking_table == 'log_comments_imports':
        crud_utils.create_log_comments_import(session, base_filename, status, notes, website)


def process_directory(directory, website):
    global processed_article_file_list, processed_comment_file_list
    excluded_files = processed_article_file_list + processed_comment_file_list
    sorted_filenames = sorted(os.listdir(directory))

    for filename in sorted_filenames:
        if filename in excluded_files:
            continue
        if filename.endswith('.txt') or filename.endswith('.txt.gz'):
            if any(year in filename for year in years_to_process):
                process_file(os.path.join(directory, filename), website)


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


def process_comment_file(file_path, website):
    tracking_table = 'log_comments_imports'
    columns = ['region', 'article_id', 'user_nickname', 'encoded_ip', 'timestamp', 'comment_text']
    filename = get_base_filename(file_path)

    try:
        df = create_df_from_file(file_path, columns)

        df['comment_text'] = df['comment_text'].astype(str)
        df['comment_lang'] = df.apply(lambda row: determine_text_language(row['comment_text'], row['region']), axis=1)
        df['website'] = website

        crud_utils.bulk_insert_comments(df, session)

        print(f"Data from {file_path} has been inserted into comments")
        log_import(tracking_table, filename, "Success", "File imported successfully.", website)
    except Exception as e:
        session.rollback()
        print(f"Error processing file {file_path}: {e}")
        log_import(tracking_table, filename, "Failed", str(e), website)


def process_article_file(file_path, website):
    tracking_table = 'log_articles_imports'
    columns = ['region', 'article_id', 'headline', 'pub_timestamp', 'url']
    filename = get_base_filename(file_path)

    try:
        df = create_df_from_file(file_path, columns)

        headline_lang_column = df.apply(lambda row: determine_text_language(row['headline'], row['region']), axis=1)
        df.insert(3, 'headline_lang', headline_lang_column)

        df = df.drop_duplicates(subset='article_id')

        df['embedding'] = df.apply(lambda row: get_text_embedding_by_language(row['headline'], row['headline_lang']), axis=1)
        df['website'] = website

        crud_utils.bulk_insert_articles(df, session)

        print(f"Data from {file_path} has been inserted into articles")
        log_import(tracking_table, filename, "Success", "File imported successfully.", website)
    except Exception as e:
        session.rollback()
        print(f"Error processing file {file_path}: {e}")
        log_import(tracking_table, filename, "Failed", str(e), website)


def process_file(file_path, website):
    if 'meta' in file_path:
        process_article_file(file_path, website)
    else:
        process_comment_file(file_path, website)


def parse_delfi_v3_articles(file_path):
    tracking_table = 'log_articles_imports'
    columns = ['region', 'article_id', 'headline', 'pub_timestamp', 'url']
    filename = get_base_filename(file_path)

    if filename in crud_utils.get_processed_article_files(session, 'delfi'):
        print(f"Skipping already processed file: {filename}")
        return

    try:
        total_lines = sum(1 for _ in open(file_path, encoding='utf-8'))
        total_chunks = math.ceil(total_lines / CHUNK_SIZE)
        chunks = pd.read_csv(file_path, sep='\t', header=None, names=columns,
                             on_bad_lines='skip', quoting=csv.QUOTE_NONE, chunksize=CHUNK_SIZE)
        for chunk in tqdm(chunks, total=total_chunks, desc='Articles', unit='chunk'):
            chunk['headline_lang'] = chunk.apply(lambda row: determine_text_language(row['headline'], row['region']), axis=1)
            chunk['embedding'] = chunk.apply(lambda row: get_text_embedding_by_language(row['headline'], row['headline_lang']), axis=1)
            chunk['website'] = 'delfi'
            crud_utils.bulk_insert_articles(chunk, session)

        print(f"Data from {file_path} has been inserted into articles")
        log_import(tracking_table, filename, "Success", "File imported successfully.", 'delfi')
    except Exception as e:
        session.rollback()
        print(f"Error processing file {file_path}: {e}")
        log_import(tracking_table, filename, "Failed", str(e), 'delfi')


def parse_delfi_v3_comments(file_path):
    tracking_table = 'log_comments_imports'
    columns = ['region', 'article_id', 'user_nickname', 'encoded_ip', 'timestamp', 'comment_text']
    filename = get_base_filename(file_path)

    if filename in crud_utils.get_processed_comment_files(session, 'delfi'):
        print(f"Skipping already processed file: {filename}")
        return

    try:
        total_lines = sum(1 for _ in open(file_path, encoding='utf-8'))
        total_chunks = math.ceil(total_lines / CHUNK_SIZE)
        chunks = pd.read_csv(file_path, sep='\t', header=None, names=columns,
                             on_bad_lines='skip', quoting=csv.QUOTE_NONE, chunksize=CHUNK_SIZE)
        for chunk in tqdm(chunks, total=total_chunks, desc='Comments', unit='chunk'):
            chunk['comment_text'] = chunk['comment_text'].astype(str)
            chunk['comment_lang'] = chunk.apply(lambda row: determine_text_language(row['comment_text'], row['region']), axis=1)
            chunk['website'] = 'delfi'
            crud_utils.bulk_insert_comments(chunk, session)

        print(f"Data from {file_path} has been inserted into comments")
        log_import(tracking_table, filename, "Success", "File imported successfully.", 'delfi')
    except Exception as e:
        session.rollback()
        print(f"Error processing file {file_path}: {e}")
        log_import(tracking_table, filename, "Failed", str(e), 'delfi')


# Processing data with CUDA for 2023.01.01.-2024.04.08. took 692 seconds
if __name__ == '__main__':
    start_time = time.time()
    delfi_v3 = data_path('v3/delfi')
    parse_delfi_v3_articles(os.path.join(delfi_v3, 'articles-meta.txt'))
    parse_delfi_v3_comments(os.path.join(delfi_v3, 'comments-meta.txt'))
    process_directory(tvnet_data, 'tvnet')
    process_directory(apollo_data, 'apollo')
    end_time = time.time()
    print(f"Processing new data took {end_time - start_time} seconds")
