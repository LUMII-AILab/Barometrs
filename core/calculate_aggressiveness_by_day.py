import time
import pandas as pd
from sqlalchemy.orm import sessionmaker
from sqlalchemy import cast, Date, extract
from tqdm import tqdm
from db import database, models

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=database.engine)

SUPPORTED_LANGUAGES = ['lv', 'ru']
WEBSITES = ['tvnet', 'delfi', 'apollo']


def _score_lemmas(aggressive_weights, lemmas):
    if not lemmas:
        return 0, 0.0
    count = 0
    wsum = 0.0
    for lemma in lemmas:
        w = aggressive_weights.get(lemma)
        if w is not None:
            count += 1
            wsum += w
    return count, wsum


def _make_records(grouped, scope_name, lang, already_processed):
    records = []
    for row in grouped.itertuples(index=False):
        if (row.comment_date, lang, scope_name) in already_processed:
            continue
        total = int(row.total_word_count)
        agg_count = int(row.aggressive_word_count)
        agg_weight = float(row.aggressive_word_weight_sum)
        records.append({
            'date': row.comment_date,
            'language': lang,
            'website': scope_name,
            'aggressive_word_count': agg_count,
            'aggressive_word_weight_sum': agg_weight,
            'total_word_count': total,
            'aggressiveness_ratio': agg_count / total if total > 0 else 0.0,
            'weighted_aggressiveness_ratio': agg_weight / total if total > 0 else 0.0,
        })
        already_processed.add((row.comment_date, lang, scope_name))
    return records


def calculate_aggressiveness():
    session = SessionLocal()
    try:
        aggressive_weights = {
            row.word: row.weight
            for row in session.query(models.AggressiveKeyword).all()
        }
        print(f'Loaded {len(aggressive_weights)} aggressive keywords')

        already_processed = {
            (row[0], row[1], row[2]) for row in session.query(
                cast(models.AggressivenessByDay.date, Date),
                models.AggressivenessByDay.language,
                models.AggressivenessByDay.website,
            ).all()
        }
        print(f'Already processed (date, lang, website) triples: {len(already_processed)}')

        scorer = lambda lemmas: pd.Series(_score_lemmas(aggressive_weights, lemmas))

        for lang in SUPPORTED_LANGUAGES:
            months = (
                session.query(
                    extract('year', models.Comment.timestamp).label('year'),
                    extract('month', models.Comment.timestamp).label('month'),
                )
                .join(models.LemmatizedComment, models.LemmatizedComment.comment_id == models.Comment.id)
                .filter(models.Comment.comment_lang == lang)
                .distinct()
                .order_by('year', 'month')
                .all()
            )

            tqdm.write(f'\nLanguage: {lang} — {len(months)} months to process')

            for year, month in tqdm(months, desc=f'{lang}'):
                rows = (
                    session.query(
                        models.LemmatizedComment.lemmas,
                        models.LemmatizedComment.lemma_count,
                        cast(models.Comment.timestamp, Date).label('comment_date'),
                        models.Comment.website,
                    )
                    .join(models.Comment, models.LemmatizedComment.comment_id == models.Comment.id)
                    .filter(
                        models.Comment.comment_lang == lang,
                        extract('year', models.Comment.timestamp) == year,
                        extract('month', models.Comment.timestamp) == month,
                    )
                    .all()
                )

                df = pd.DataFrame(rows, columns=['lemmas', 'lemma_count', 'comment_date', 'website'])
                df['comment_date'] = pd.to_datetime(df['comment_date']).dt.date

                # Score every comment once for the whole month
                df[['agg_count', 'agg_weight']] = df['lemmas'].apply(scorer)

                agg = dict(
                    total_word_count=('lemma_count', 'sum'),
                    aggressive_word_count=('agg_count', 'sum'),
                    aggressive_word_weight_sum=('agg_weight', 'sum'),
                )

                records = []
                website_groupbys = []

                for website in WEBSITES:
                    scope_df = df[df['website'] == website]
                    if scope_df.empty:
                        continue
                    grouped = scope_df.groupby('comment_date').agg(**agg).reset_index()
                    website_groupbys.append(grouped)
                    records.extend(_make_records(grouped, website, lang, already_processed))

                # 'all' summed from already-computed per-website groupbys — avoids a second pass through df
                if website_groupbys:
                    all_grouped = (
                        pd.concat(website_groupbys)
                        .groupby('comment_date', as_index=False)[
                            ['total_word_count', 'aggressive_word_count', 'aggressive_word_weight_sum']
                        ]
                        .sum()
                    )
                    records.extend(_make_records(all_grouped, 'all', lang, already_processed))

                if records:
                    session.bulk_insert_mappings(models.AggressivenessByDay, records)
                session.commit()

        print('\nDone.')
    finally:
        session.close()


if __name__ == '__main__':
    t_start = time.time()
    print('Calculating aggressiveness by day...')
    calculate_aggressiveness()
    print(f'Finished in {time.time() - t_start:.1f}s')
