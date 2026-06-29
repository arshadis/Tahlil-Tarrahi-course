import json
import os
from uuid import uuid4
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Form, File, UploadFile
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.game import Question, QuestionOption, DailyStage, StageQuestion
router = APIRouter(prefix="/admin/questions", tags=["admin-questions"])
security = HTTPBearer()


def get_current_admin(
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

    if user.role != "admin":
        raise HTTPException(status_code=403, detail="فقط ادمین اجازه افزودن سوال دارد.")

    return user


@router.post("")
def create_question(
    title: str = Form(...),
    question_type: str = Form(...),
    difficulty: str = Form(...),
    topic: str = Form(...),
    correct_answer: str = Form(...),
    explanation: str = Form(""),
    options_json: str = Form("[]"),
    image: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    allowed_types = ["multiple_choice", "fill_blank", "image"]
    allowed_difficulties = ["easy", "medium", "hard"]

    if question_type not in allowed_types:
        raise HTTPException(status_code=400, detail="نوع سوال معتبر نیست.")

    if difficulty not in allowed_difficulties:
        raise HTTPException(status_code=400, detail="سطح سختی معتبر نیست.")

    try:
        options = json.loads(options_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="فرمت گزینه‌ها معتبر نیست.")

    if question_type in ["multiple_choice", "image"]:
        clean_options = [str(option).strip() for option in options if str(option).strip()]

        if len(clean_options) < 3:
            raise HTTPException(status_code=400, detail="برای سوال گزینه‌ای حداقل ۳ گزینه لازم است.")

        if correct_answer.strip() not in clean_options:
            raise HTTPException(status_code=400, detail="پاسخ صحیح باید یکی از گزینه‌ها باشد.")
    else:
        clean_options = []

    image_url = None

    if image:
        os.makedirs("uploads", exist_ok=True)

        file_ext = os.path.splitext(image.filename)[1].lower() or ".png"
        file_name = f"{uuid4()}{file_ext}"
        file_path = os.path.join("uploads", file_name)

        with open(file_path, "wb") as buffer:
            buffer.write(image.file.read())

        image_url = f"/uploads/{file_name}"

    question = Question(
        title=title.strip(),
        question_type=question_type,
        difficulty=difficulty,
        topic=topic.strip(),
        correct_answer=correct_answer.strip(),
        explanation=explanation.strip(),
        image_url=image_url,
        is_active=True,
    )

    db.add(question)
    db.flush()

    for option_text in clean_options:
        db.add(QuestionOption(
            question_id=question.id,
            option_text=option_text,
            is_correct=option_text == correct_answer.strip(),
        ))
    today_stage = (
        db.query(DailyStage)
        .filter(
            DailyStage.stage_date == date.today(),
            DailyStage.is_active == True,
        )
        .first()
    )

    if today_stage:
        last_order = (
            db.query(StageQuestion)
            .filter(StageQuestion.stage_id == today_stage.id)
            .count()
        )

        db.add(StageQuestion(
            stage_id=today_stage.id,
            question_id=question.id,
            sort_order=last_order + 1,
        ))
    db.commit()
    db.refresh(question)

    return {
        "message": "سوال با موفقیت اضافه شد.",
        "question": {
            "id": question.id,
            "title": question.title,
            "question_type": question.question_type,
            "difficulty": question.difficulty,
            "topic": question.topic,
            "image_url": question.image_url,
        }
    }


@router.get("")
def list_questions(
    search: str = "",
    topic: str = "",
    difficulty: str = "",
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    query = db.query(Question).filter(Question.is_active == True)

    if search:
        query = query.filter(Question.title.ilike(f"%{search}%"))

    if topic:
        query = query.filter(Question.topic.ilike(f"%{topic}%"))

    if difficulty:
        query = query.filter(Question.difficulty == difficulty)

    questions = query.order_by(Question.id.desc()).all()

    return {
        "questions": [
            {
                "id": question.id,
                "title": question.title,
                "question_type": question.question_type,
                "difficulty": question.difficulty,
                "topic": question.topic,
                "correct_answer": question.correct_answer,
                "explanation": question.explanation,
                "image_url": question.image_url,
            }
            for question in questions
        ]
    }


@router.get("/{question_id}")
def get_question(
    question_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    question = (
        db.query(Question)
        .filter(Question.id == question_id, Question.is_active == True)
        .first()
    )

    if not question:
        raise HTTPException(status_code=404, detail="سوال پیدا نشد.")

    options = (
        db.query(QuestionOption)
        .filter(QuestionOption.question_id == question.id)
        .all()
    )

    return {
        "id": question.id,
        "title": question.title,
        "question_type": question.question_type,
        "difficulty": question.difficulty,
        "topic": question.topic,
        "correct_answer": question.correct_answer,
        "explanation": question.explanation,
        "image_url": question.image_url,
        "options": [
            {
                "id": option.id,
                "text": option.option_text,
                "is_correct": option.is_correct,
            }
            for option in options
        ],
    }


@router.put("/{question_id}")
def update_question(
    question_id: int,
    title: str = Form(...),
    question_type: str = Form(...),
    difficulty: str = Form(...),
    topic: str = Form(...),
    correct_answer: str = Form(...),
    explanation: str = Form(""),
    options_json: str = Form("[]"),
    image: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    question = (
        db.query(Question)
        .filter(Question.id == question_id, Question.is_active == True)
        .first()
    )

    if not question:
        raise HTTPException(status_code=404, detail="سوال پیدا نشد.")

    allowed_types = ["multiple_choice", "fill_blank", "image"]
    allowed_difficulties = ["easy", "medium", "hard"]

    if question_type not in allowed_types:
        raise HTTPException(status_code=400, detail="نوع سوال معتبر نیست.")

    if difficulty not in allowed_difficulties:
        raise HTTPException(status_code=400, detail="سطح سختی معتبر نیست.")

    try:
        options = json.loads(options_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="فرمت گزینه‌ها معتبر نیست.")

    if question_type in ["multiple_choice", "image"]:
        clean_options = [str(option).strip() for option in options if str(option).strip()]

        if len(clean_options) < 3:
            raise HTTPException(status_code=400, detail="برای سوال گزینه‌ای حداقل ۳ گزینه لازم است.")

        if correct_answer.strip() not in clean_options:
            raise HTTPException(status_code=400, detail="پاسخ صحیح باید یکی از گزینه‌ها باشد.")
    else:
        clean_options = []

    image_url = question.image_url

    if image:
        os.makedirs("uploads", exist_ok=True)

        file_ext = os.path.splitext(image.filename)[1].lower() or ".png"
        file_name = f"{uuid4()}{file_ext}"
        file_path = os.path.join("uploads", file_name)

        with open(file_path, "wb") as buffer:
            buffer.write(image.file.read())

        image_url = f"/uploads/{file_name}"

    question.title = title.strip()
    question.question_type = question_type
    question.difficulty = difficulty
    question.topic = topic.strip()
    question.correct_answer = correct_answer.strip()
    question.explanation = explanation.strip()
    question.image_url = image_url

    db.query(QuestionOption).filter(
        QuestionOption.question_id == question.id
    ).delete()

    for option_text in clean_options:
        db.add(QuestionOption(
            question_id=question.id,
            option_text=option_text,
            is_correct=option_text == correct_answer.strip(),
        ))

    db.commit()
    db.refresh(question)

    return {
        "message": "سوال با موفقیت ویرایش شد.",
        "question": {
            "id": question.id,
            "title": question.title,
            "question_type": question.question_type,
            "difficulty": question.difficulty,
            "topic": question.topic,
        }
    }




@router.delete("/{question_id}")
def delete_question(
    question_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    question = (
        db.query(Question)
        .filter(Question.id == question_id, Question.is_active == True)
        .first()
    )

    if not question:
        raise HTTPException(status_code=404, detail="سوال پیدا نشد.")

    question.is_active = False

    db.query(StageQuestion).filter(
        StageQuestion.question_id == question.id
    ).delete()

    db.commit()

    return {
        "message": "سوال با موفقیت حذف شد."
    }