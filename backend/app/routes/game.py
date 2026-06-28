from datetime import date, datetime, timezone
import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.game import (
    DailyStage,
    StageQuestion,
    Question,
    QuestionOption,
    UserGameSession,
    UserAnswer,
    AppSetting,
)

router = APIRouter(prefix="/game", tags=["game"])
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            os.getenv("JWT_SECRET", "change-this-secret"),
            algorithms=[os.getenv("JWT_ALGORITHM", "HS256")],
        )
        user_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise HTTPException(status_code=401, detail="توکن نامعتبر است.")

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()

    if not user:
        raise HTTPException(status_code=401, detail="کاربر معتبر نیست.")

    return user


def get_setting(db: Session, key: str, default: str) -> str:
    setting = db.query(AppSetting).filter(AppSetting.setting_key == key).first()
    return setting.setting_value if setting else default


@router.post("/start")
def start_today_stage(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    today = date.today()

    stage = (
        db.query(DailyStage)
        .filter(DailyStage.stage_date == today, DailyStage.is_active == True)
        .first()
    )

    if not stage:
        raise HTTPException(status_code=404, detail="مرحله امروز هنوز تعریف نشده است.")

    session = (
        db.query(UserGameSession)
        .filter(
            UserGameSession.user_id == current_user.id,
            UserGameSession.stage_id == stage.id,
            UserGameSession.status.in_(["in_progress", "paused"]),
        )
        .first()
    )

    if not session:
        session = UserGameSession(
            user_id=current_user.id,
            stage_id=stage.id,
            status="in_progress",
            current_question_index=0,
            score=0,
        )
        db.add(session)
        db.flush()

    stage_questions = (
        db.query(StageQuestion)
        .filter(StageQuestion.stage_id == stage.id)
        .order_by(StageQuestion.sort_order.asc())
        .all()
    )

    questions = []

    for sq in stage_questions:
        question = db.query(Question).filter(Question.id == sq.question_id).first()

        options = (
            db.query(QuestionOption)
            .filter(QuestionOption.question_id == question.id)
            .all()
        )

        questions.append({
            "id": question.id,
            "title": question.title,
            "question_type": question.question_type,
            "difficulty": question.difficulty,
            "topic": question.topic,
            "options": [
                {
                    "id": option.id,
                    "text": option.option_text,
                }
                for option in options
            ],
        })

    db.commit()

    return {
        "session": {
            "id": session.id,
            "status": session.status,
            "score": session.score,
            "current_question_index": session.current_question_index,
        },
        "stage": {
            "id": stage.id,
            "date": str(stage.stage_date),
            "difficulty": stage.difficulty,
            "question_count": stage.question_count,
            "max_score": stage.max_score,
        },
        "questions": questions,
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "total_score": current_user.total_score,
        },
    }


@router.post("/submit-answer")
def submit_answer(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session_id = payload.get("session_id")
    question_id = payload.get("question_id")
    answer = payload.get("answer")

    if not session_id or not question_id or answer is None:
        raise HTTPException(status_code=400, detail="شناسه session، سوال و پاسخ الزامی است.")

    session = (
        db.query(UserGameSession)
        .filter(
            UserGameSession.id == session_id,
            UserGameSession.user_id == current_user.id,
            UserGameSession.status.in_(["in_progress", "paused"]),
        )
        .first()
    )

    if not session:
        raise HTTPException(status_code=404, detail="session فعال پیدا نشد.")

    question = db.query(Question).filter(Question.id == question_id).first()

    if not question:
        raise HTTPException(status_code=404, detail="سوال پیدا نشد.")

    already_answered = (
        db.query(UserAnswer)
        .filter(
            UserAnswer.session_id == session.id,
            UserAnswer.question_id == question.id,
        )
        .first()
    )

    if already_answered:
        raise HTTPException(status_code=400, detail="این سوال قبلاً پاسخ داده شده است.")

    is_correct = str(answer).strip() == str(question.correct_answer).strip()

    score_per_question = int(get_setting(db, "score_per_question", "10"))
    score_earned = score_per_question if is_correct else 0

    user_answer = UserAnswer(
        session_id=session.id,
        question_id=question.id,
        user_answer=str(answer),
        is_correct=is_correct,
        score_earned=score_earned,
    )

    db.add(user_answer)

    if is_correct:
        session.score += score_earned
        current_user.total_score += score_earned

    session.current_question_index += 1

    db.commit()
    db.refresh(session)
    db.refresh(current_user)

    return {
        "is_correct": is_correct,
        "correct_answer": question.correct_answer,
        "explanation": question.explanation,
        "score_earned": score_earned,
        "session_score": session.score,
        "user_total_score": current_user.total_score,
    }


@router.post("/finish")
def finish_stage(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session_id = payload.get("session_id")

    session = (
        db.query(UserGameSession)
        .filter(
            UserGameSession.id == session_id,
            UserGameSession.user_id == current_user.id,
        )
        .first()
    )

    if not session:
        raise HTTPException(status_code=404, detail="session پیدا نشد.")

    session.status = "completed"
    session.finished_at = datetime.now(timezone.utc)

    correct_count = (
        db.query(UserAnswer)
        .filter(UserAnswer.session_id == session.id, UserAnswer.is_correct == True)
        .count()
    )

    wrong_count = (
        db.query(UserAnswer)
        .filter(UserAnswer.session_id == session.id, UserAnswer.is_correct == False)
        .count()
    )

    db.commit()

    return {
        "message": "مرحله با موفقیت تمام شد.",
        "score": session.score,
        "correct_count": correct_count,
        "wrong_count": wrong_count,
        "user_total_score": current_user.total_score,
    }