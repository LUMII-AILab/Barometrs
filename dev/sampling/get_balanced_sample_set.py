import sys
sys.path.append('/app')

import os
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker
import pandas as pd
import numpy as np
from datetime import datetime
from db.models import PredictedComment
import json

# Database configuration
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", None)

engine = create_engine(SQLALCHEMY_DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

# Configure emotional classes and sampling parameters
EMOTIONS = ['joy','fear']
# EMOTIONS = ['joy', 'fear', 'anger', 'disgust', 'surprise', 'sadness', 'neutral']
SAMPLE_PER_EMOTION = 200
TIME_BINS = 4
CONFIDENCE_BINS = [0, 0.4, 0.7, 1.0]


def get_stratified_sample(df, emotion):
    try:
        df['time_group'] = pd.qcut(
            df['comment_timestamp'],
            q=TIME_BINS,
            duplicates='drop'
        )
        df['confidence_group'] = pd.cut(
            df['ekman_prediction_score'],
            bins=CONFIDENCE_BINS,
            labels=['low', 'medium', 'high'],
            include_lowest=True
        )

        # First stage: Limit per article contribution
        stage1 = df.groupby(['article_id'], group_keys=False).apply(
            lambda x: x.sample(min(len(x), 3), random_state=42)
        )

        # Second stage: Stratify by time and confidence
        if stage1.empty:
            raise ValueError(f"No data available for {emotion}")

        groups = stage1.groupby(['time_group', 'confidence_group'])
        members_per_group = max(1, SAMPLE_PER_EMOTION // groups.ngroups)

        stage2 = groups.apply(
            lambda x: x.sample(min(len(x), members_per_group), random_state=42)
        ).reset_index(drop=True)

        sample_count = min(len(stage2), SAMPLE_PER_EMOTION)
        print(f"Sample count for {emotion}: {sample_count}")

        return stage2.sample(sample_count, random_state=42)

    except Exception as e:
        print(f"Error sampling {emotion}: {str(e)}")
        return pd.DataFrame()


final_samples = []

for emotion in EMOTIONS:
    # Query database using ORM
    query = session.query(PredictedComment).filter(
        PredictedComment.ekman_prediction_emotion == emotion,
        PredictedComment.comment_timestamp >= datetime(2020, 1, 1),
        PredictedComment.text_lang == 'lv',
    )

    df = pd.read_sql(query.statement, session.bind)

    # drop redundant columns
    df.drop(columns=['normal_prediction_json', 'normal_prediction_emotion', 'normal_prediction_score'], inplace=True)

    # Convert JSON column to string
    df['ekman_prediction_json'] = df['ekman_prediction_json'].apply(json.dumps)

    if not df.empty:
        sampled = get_stratified_sample(df, emotion)
        if not sampled.empty:
            final_samples.append(sampled)
            print(f"Sampled {len(sampled)} for {emotion}")
        else:
            print(f"Insufficient data for {emotion}")
    else:
        print(f"No data found for {emotion}")

final_df = pd.concat(final_samples, ignore_index=True)

print("Current working directory:", os.getcwd())

# Save the final DataFrame to a CSV file
output_file = './balanced_sample_set.csv'
final_df.to_csv(output_file, index=False)

session.close()
