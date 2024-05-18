from datetime import datetime
from fastapi import APIRouter, Depends, Request, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette.templating import Jinja2Templates
from db import crud_utils
from db import database
from db.crud import predicted_comments as pc_crud

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/")
def read_root(request: Request, session: Session = Depends(database.get_session)):
    allowed_months = pc_crud.get_predicted_comment_allowed_months(session)
    return templates.TemplateResponse("index.html", {"request": request, "allowed_months": allowed_months})

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
    start_month = datetime.strptime(filter.startMonth, "%Y-%m").date()
    end_month = datetime.strptime(filter.endMonth, "%Y-%m").date()

    predicted_comments = pc_crud.get_predicted_comments_max_emotion_chart_data(
        session,
        filter.predictionType,
        start_month,
        end_month,
        filter.groupBy
    )

    return predicted_comments

@router.get("/predicted_comments_emotion_comments")
def read_predicted_comments_max_emotion_comments(
    predictionType: str,
    language: str,
    requestDate: str = Query(..., regex="^\\d{4}-\\d{2}-\\d{2}$"),
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
    requestDate: str = Query(..., regex="^\\d{4}-\\d{2}-\\d{2}$"),
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
    requestDate: str = Query(..., regex="^\\d{4}-\\d{2}-\\d{2}$"),
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

@router.get("/predicted_comments_emotion_keywords")
def read_predicted_comments_emotion_keywords(
    predictionType: str,
    language: str,
    requestDate: str = Query(..., regex="^\\d{4}-\\d{2}-\\d{2}$"),
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