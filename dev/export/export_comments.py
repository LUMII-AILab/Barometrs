import sys
sys.path.append('/app')

import csv
import pandas as pd
from sqlalchemy.orm import sessionmaker
from db import database
from db import models

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=database.engine)

def export_predicted_comments_to_csv():
    session = SessionLocal()
    try:
        query = session.query(
            models.PredictedComment.text_lang,
            models.PredictedComment.comment_timestamp,
            models.RawArticle.url,
            models.PredictedComment.text,
        ).join(
            models.RawArticle,
            models.PredictedComment.article_id == models.RawArticle.article_id
        )
        results = query.all()
        df = pd.DataFrame(results, columns=[
            'text_lang', 'comment_timestamp', 'article_url', 'comment_text'
        ])

        def resolve_portal_domain(url):
            if 'delfi' in url:
                return 'delfi'
            elif 'tvnet' in url:
                return 'tvnet'
            elif 'apollo' in url:
                return 'apollo'
            return 'other'

        df['portāls'] = df['article_url'].apply(resolve_portal_domain)
        df = df.drop(columns=['article_url'])
        df = df.rename(columns={
            'text_lang': 'valoda',
            'comment_timestamp': 'datums',
            'comment_text': 'komentārs'
        })
        # reorder columns
        df = df[['valoda', 'datums', 'portāls', 'komentārs']]

        # order by date
        df = df.sort_values(by='datums')

        file_path = 'exported_predicted_comments.csv'
        df.to_csv(file_path, index=False, header=False, quoting=csv.QUOTE_NONNUMERIC)
        print(f'Exported {len(df)} comments to {file_path}')
    finally:
        session.close()

def export_raw_comments_to_csv():
    session = SessionLocal()
    try:
        query = session.query(
            models.RawComment.comment_lang,
            models.RawComment.region,
            models.RawComment.timestamp,
            models.RawArticle.url,
            models.RawComment.comment_text,
        ).join(
            models.RawArticle,
            models.RawComment.article_id == models.RawArticle.article_id
        )
        results = query.all()
        df = pd.DataFrame(results, columns=[
            'text_lang', 'region', 'comment_timestamp', 'article_url', 'comment_text'
        ])

        def resolve_portal_domain(url):
            if 'delfi' in url:
                return 'delfi'
            elif 'tvnet' in url:
                return 'tvnet'
            elif 'apollo' in url:
                return 'apollo'
            return 'other'

        df['portāls'] = df['article_url'].apply(resolve_portal_domain)
        df = df.drop(columns=['article_url'])

        # if comment_lang is 'other', use region to determine language
        def determine_language(row):
            if row['text_lang'] == 'other':
                if row['region'] == 'rus':
                    return 'ru'
                elif row['region'] == 'lat':
                    return 'lv'
            else:
                return row['text_lang']

        df['text_lang'] = df.apply(determine_language, axis=1)

        df = df.rename(columns={
            'text_lang': 'valoda',
            'comment_timestamp': 'datums',
            'comment_text': 'komentārs'
        })
        # reorder columns
        df = df[['valoda', 'datums', 'portāls', 'komentārs']]

        # order by date
        df = df.sort_values(by='datums')

        file_path = 'exported_raw_comments.csv'
        df.to_csv(file_path, index=False, header=False, quoting=csv.QUOTE_NONNUMERIC)
        print(f'Exported {len(df)} raw comments to {file_path}')
    finally:
        session.close()

# get option from command line argument
if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python export_comments.py [predicted|raw]')
        sys.exit(1)

    option = sys.argv[1]
    if option == 'predicted':
        export_predicted_comments_to_csv()
    elif option == 'raw':
        export_raw_comments_to_csv()
    else:
        print('Invalid option. Use "predicted" or "raw".')
        sys.exit(1)