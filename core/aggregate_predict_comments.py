from datetime import timedelta
import time
from sqlalchemy.orm import sessionmaker
from db import models, database
from db.crud.predicted_comments import read
from sqlalchemy import func

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=database.engine)
session = SessionLocal()

# TODO: smart way would be to keep a list of comments that were agregated
# But we will keep it simple and run complete re-agregation when new comments pop-up
def aggregate_comments():
    # Get total number of predicted comments
    predicted_comments_count = read.get_predicted_comment_count(session)
    print(f'Total predicted comment count: {predicted_comments_count}')
    processed_comment_count = 0

    # Get min and max dates for predicted comments
    # Start with min date and get the next step by determening aggregation step (day, week, month)
    # Select the comments that fall into the interval and populate predicted_comment_aggregation table
    aggregation_start_date = session.query(func.min(models.PredictedComment.comment_timestamp)).scalar().date()
    aggregation_end_date = session.query(func.max(models.PredictedComment.comment_timestamp)).scalar().date()

    print(f'Aggregating comments from {aggregation_start_date} to {aggregation_end_date}')

    def get_next_aggregation_date(current_date, aggregation_step='day'):
        if aggregation_step == 'day':
            return current_date + timedelta(days=1)
        elif aggregation_step == 'week':
            return current_date + timedelta(weeks=1)
        else:
            return None

    # Populate aggregation by day
    step_date = aggregation_start_date
    while step_date <= aggregation_end_date:
        for comment in read.get_predicted_comments_by_day(session, date=step_date):
            print(comment)
            processed_comment_count += 1

        print(f'Processed {processed_comment_count} comments for {step_date}')
        step_date = get_next_aggregation_date(step_date, aggregation_step='day')

    print(f'Processed {processed_comment_count} comments')

if __name__ == '__main__':
    start_time = time.time()
    print('Agreggating predicted comments...')
    aggregate_comments()
    end_time = time.time()
    print(f'Agreggation of comments took {start_time - end_time} seconds')