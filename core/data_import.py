import csv
import gzip
import os
import time

import fasttext
import pandas as pd
from sqlalchemy.orm import sessionmaker

# import database
from db import crud_utils, database
from path_config import data_path, models_path
import torch
from core import load_model

# Database connection setup
new_delfi_data = data_path('delfi-new')
old_delfi_data = data_path('delfi')
apollo_data = data_path('apollo')
tvnet_data = data_path('tvnet')
years_to_process = ['2020', '2021', '2022', '2023', '2024']

# Session placeholder
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=database.engine)
session = SessionLocal()
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Load the language detection model
language_detection_model = fasttext.load_model(models_path('lid.176.bin'))

# add type hints
lvbert_model, lvbert_tokenizer = load_model.get_embedding_model_and_tokenizer('lvbert')
rubert_model, rubert_tokenizer = load_model.get_embedding_model_and_tokenizer('rubert-base-cased')

processed_article_file_list = crud_utils.get_processed_article_files(session)
processed_comment_file_list = crud_utils.get_processed_comment_files(session)

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
    # Move the model to the appropriate device
    model.to(device)

    # Tokenize the input text and move the input tensors to the same device
    encoded_input = tokenizer(text, return_tensors='pt', padding=True, truncation=True, max_length=512)
    encoded_input = {key: val.to(device) for key, val in encoded_input.items()}

    # Run inference without computing gradients
    with torch.no_grad():
        outputs = model(**encoded_input)

    # Extract the embeddings of the first token ([CLS] token in BERT) from the last hidden state
    embeddings = outputs.last_hidden_state[:, 0, :]

    # Convert the embeddings tensor to a list after squeezing the extra dimension
    return embeddings.squeeze().tolist()

def get_text_embedding_by_language(text, lang):
    if lang == 'lv':
        embedding = get_embedding(lvbert_model, lvbert_tokenizer, text)
    elif lang == 'ru':
        embedding = get_embedding(rubert_model, rubert_tokenizer, text)
    else:
        embedding = None

    return embedding


def log_import(table_name, base_filename, status, notes):
    # Rewrite the above code to use the session object
    if table_name == 'log_raw_articles_imports':
        crud_utils.create_log_raw_articles_import(session, base_filename, status, notes)
    elif table_name == 'log_raw_comments_imports':
        crud_utils.create_log_raw_comments_import(session, base_filename, status, notes)


def process_directory(directory):
    global processed_article_file_list, processed_comment_file_list
    excluded_files = processed_article_file_list + processed_comment_file_list
    sorted_filenames = sorted(os.listdir(directory))

    for filename in sorted_filenames:
        if filename in excluded_files:
            continue
        if filename.endswith('.txt') or filename.endswith('.txt.gz'):
            # Process files from 2020-2024
            if any(year in filename for year in years_to_process):
                process_file(os.path.join(directory, filename))


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


def process_comment_file(file_path):
    table_name = 'raw_comments'
    tracking_table = 'log_raw_comments_imports'
    columns = ['region', 'article_id', 'user_nickname', 'encoded_ip', 'timestamp', 'comment_text']
    filename = get_base_filename(file_path)

    try:
        df = create_df_from_file(file_path, columns)

        # Convert comment text to string
        df['comment_text'] = df['comment_text'].astype(str)

        # Add language column
        df['comment_lang'] = df['comment_text'].apply(determine_text_language)

        # Bulk insert data into the database
        crud_utils.bulk_insert_comments(df, session)

        print(f"Data from {file_path} has been inserted into {table_name}")
        log_import(tracking_table, filename, "Success", "File imported successfully.")
    except Exception as e:
        session.rollback()
        print(f"Error processing file {file_path}: {e}")
        log_import(tracking_table, filename, "Failed", str(e))

    return


def process_article_file(file_path):
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
        log_import(tracking_table, filename, "Success", "File imported successfully.")
    except Exception as e:
        session.rollback()
        print(f"Error processing file {file_path}: {e}")
        log_import(tracking_table, filename, "Failed", str(e))

    return


def process_file(file_path):
    # print(f"Processing {file_path}")
    if 'meta' in file_path:
        process_article_file(file_path)
    else:
        process_comment_file(file_path)

# Processing data with CUDA for 2023.01.01.-2024.04.08. took 692 seconds
if __name__ == '__main__':
    start_time = time.time()
    process_directory(new_delfi_data)
    process_directory(old_delfi_data)
    process_directory(tvnet_data)
    process_directory(apollo_data)
    end_time = time.time()
    print(f"Processing new data took {end_time - start_time} seconds")
