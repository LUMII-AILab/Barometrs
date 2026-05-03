from datetime import datetime
from fastapi import APIRouter, Depends, Request, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette.templating import Jinja2Templates
from db import crud_utils, database
from db.crud import predicted_comments as pc_crud
from db.crud import aggressiveness as agg_crud
import redis
import pickle

router = APIRouter()
templates = Jinja2Templates(directory="templates")
templates.env.filters['month_label'] = lambda v: datetime.strptime(v, '%Y-%m').strftime('%b %Y')
r = redis.Redis(host='redis', port=6379, db=0)

@router.get("/")
def read_root(request: Request, session: Session = Depends(database.get_session)):
    allowed_months = pc_crud.get_predicted_comment_allowed_months(session)
    return templates.TemplateResponse(request, "index.html", {"allowed_months": allowed_months})

@router.get("/comments")
def read_raw_comments(session: Session = Depends(database.get_session)):
    raw_comments = crud_utils.get_raw_comments(session)
    return raw_comments

@router.get("/predicted_comments")
def read_predicted_comments(session: Session = Depends(database.get_session)):
    predicted_comments = pc_crud.get_predicted_comments(session)

    return predicted_comments

class PredictedCommentsFilter(BaseModel):
    startMonth: str
    endMonth: str
    groupBy: str
    predictionType: str

@router.post("/predicted_comments_max_emotion_charts")
def read_predicted_comments_max_emotion_charts(
    filter: PredictedCommentsFilter,
    session: Session = Depends(database.get_session)
):
    cache_key = f"chart_data_{filter.predictionType}_{filter.startMonth}_{filter.endMonth}_{filter.groupBy}"
    result = r.get(cache_key)
    
    if result:
        return pickle.loads(result)

    start_month = datetime.strptime(filter.startMonth, "%Y-%m").date()
    end_month = datetime.strptime(filter.endMonth, "%Y-%m").date()

    predicted_comments = pc_crud.get_predicted_comments_max_emotion_chart_data(
        session,
        filter.predictionType,
        start_month,
        end_month,
        filter.groupBy
    )

    r.set(cache_key, pickle.dumps(predicted_comments))

    return predicted_comments

@router.get("/predicted_comments_emotion_comments")
def read_predicted_comments_max_emotion_comments(
    predictionType: str,
    language: str,
    requestDate: str = Query(..., pattern="^\\d{4}-\\d{2}-\\d{2}$"),
    session: Session = Depends(database.get_session)
):
    request_date = datetime.strptime(requestDate, "%Y-%m-%d").date()

    predicted_comments = pc_crud.get_predicted_comments_max_emotion_comments_by_type_and_request_date(
        session,
        predictionType,
        request_date,
        language
    )

    return predicted_comments

@router.get("/predicted_comments_max_emotion_articles")
def read_predicted_comments_max_emotion_articles(
    predictionType: str,
    language: str,
    requestDate: str = Query(..., pattern="^\\d{4}-\\d{2}-\\d{2}$"),
    session: Session = Depends(database.get_session)
):
    request_date = datetime.strptime(requestDate, "%Y-%m-%d").date()

    predicted_comments = pc_crud.get_predicted_comments_max_emotion_articles_by_type_and_date(
        session,
        predictionType,
        request_date,
        language
    )

    return predicted_comments

@router.get("/predicted_comments_max_emotion_clustered_articles")
def read_predicted_comments_max_emotion_articles(
    predictionType: str,
    language: str,
    requestDate: str = Query(..., pattern="^\\d{4}-\\d{2}-\\d{2}$"),
    minClusterSize: int = Query(5),
    minSamples: int = Query(2),
    session: Session = Depends(database.get_session)
):
    request_date = datetime.strptime(requestDate, "%Y-%m-%d").date()

    predicted_comments = pc_crud.get_predicted_comments_max_emotion_articles_clustered(
        session,
        predictionType,
        request_date,
        language,
        minClusterSize,
        minSamples
    )

    return predicted_comments

@router.get("/aggressiveness_by_period")
def read_aggressiveness_by_period(
    language: str,
    startDate: str = Query(..., pattern="^\\d{4}-\\d{2}-\\d{2}$"),
    endDate: str = Query(..., pattern="^\\d{4}-\\d{2}-\\d{2}$"),
    groupBy: str = Query(..., pattern="^(day|week|month)$"),
    session: Session = Depends(database.get_session)
):
    start_date = datetime.strptime(startDate, "%Y-%m-%d").date()
    end_date = datetime.strptime(endDate, "%Y-%m-%d").date()
    return agg_crud.get_aggressiveness_by_period(session, language, start_date, end_date, groupBy)

@router.get("/aggressiveness_by_period_per_website")
def read_aggressiveness_by_period_per_website(
    startDate: str = Query(..., pattern="^\\d{4}-\\d{2}-\\d{2}$"),
    endDate: str = Query(..., pattern="^\\d{4}-\\d{2}-\\d{2}$"),
    groupBy: str = Query(..., pattern="^(day|week|month)$"),
    session: Session = Depends(database.get_session)
):
    cache_key = f"agg_by_website_{startDate}_{endDate}_{groupBy}"
    cached = r.get(cache_key)
    if cached:
        return pickle.loads(cached)

    start_date = datetime.strptime(startDate, "%Y-%m-%d").date()
    end_date = datetime.strptime(endDate, "%Y-%m-%d").date()
    result = agg_crud.get_aggressiveness_by_period_per_website(session, start_date, end_date, groupBy)
    r.set(cache_key, pickle.dumps(result))
    return result


@router.get("/aggressive_keywords_by_day")
def read_aggressive_keywords_by_day(
    language: str,
    requestDate: str = Query(..., pattern="^\\d{4}-\\d{2}-\\d{2}$"),
    session: Session = Depends(database.get_session)
):
    request_date = datetime.strptime(requestDate, "%Y-%m-%d").date()
    return agg_crud.get_aggressive_keywords_count_by_day(session, request_date, language)


@router.get("/aggressive_keywords")
def read_aggressive_keywords(session: Session = Depends(database.get_session)):
    return agg_crud.get_all_aggressive_keywords(session)


@router.get("/predicted_comments_emotion_keywords")
def read_predicted_comments_emotion_keywords(
    predictionType: str,
    language: str,
    requestDate: str = Query(..., pattern="^\\d{4}-\\d{2}-\\d{2}$"),
    session: Session = Depends(database.get_session)
):
    request_date = datetime.strptime(requestDate, "%Y-%m-%d").date()

    predicted_comments = pc_crud.get_predicted_comments_emotion_keywords(
        session,
        predictionType,
        request_date,
        language
    )

    return predicted_comments