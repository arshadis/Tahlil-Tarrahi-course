import os
from sqlalchemy.orm import Session

from app.database import Base, engine, SessionLocal
from app.models.user import User
from app.models.game import Question, QuestionOption, DailyStage, StageQuestion, UserGameSession, UserAnswer, AppSetting
from app.services.auth_service import hash_password
from datetime import date
from app.models.game import Question, QuestionOption, DailyStage, StageQuestion



DEFAULT_SETTINGS = {
    "game_start_time": "08:00",
    "game_end_time": "17:00",
    "questions_per_stage": "10",
    "score_per_question": "10",
    "delay_penalty": "20",
    "leaderboard_enabled": "true",
    "chat_enabled": "false",
}


def init_database() -> None:
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        username = os.getenv("DEV_ADMIN_USERNAME", "admin")
        password = os.getenv("DEV_ADMIN_PASSWORD", "admin123")
        full_name = os.getenv("DEV_ADMIN_FULL_NAME", "مدیر سیستم")
        email = os.getenv("DEV_ADMIN_EMAIL", "admin@example.local")

        existing_admin = db.query(User).filter(User.username == username).first()
        if not existing_admin:
            db.add(User(
                username=username,
                full_name=full_name,
                email=email,
                password_hash=hash_password(password),
                role="admin",
                is_active=True,
            ))

        for key, value in DEFAULT_SETTINGS.items():
            exists = db.query(AppSetting).filter(AppSetting.setting_key == key).first()
            if not exists:
                db.add(AppSetting(setting_key=key, setting_value=value))
        
        today = date.today()

        existing_stage = db.query(DailyStage).filter(DailyStage.stage_date == today).first()

        if not existing_stage:
            q1 = Question(
                title="کدام گزینه برای رمز عبور امن‌تر است؟",
                question_type="multiple_choice",
                difficulty="easy",
                topic="امنیت اطلاعات",
                correct_answer="رمز طولانی شامل حروف، عدد و نماد",
                explanation="رمزهای طولانی و ترکیبی امنیت بیشتری دارند.",
                is_active=True,
            )

            q2 = Question(
                title="آیا اشتراک‌گذاری رمز عبور با همکار کار درستی است؟",
                question_type="multiple_choice",
                difficulty="easy",
                topic="امنیت اطلاعات",
                correct_answer="خیر",
                explanation="رمز عبور شخصی است و نباید با دیگران به اشتراک گذاشته شود.",
                is_active=True,
            )

            q3 = Question(
                title="اگر ایمیل مشکوک دریافت کردیم چه کاری بهتر است؟",
                question_type="multiple_choice",
                difficulty="easy",
                topic="فیشینگ",
                correct_answer="روی لینک کلیک نکنیم و گزارش دهیم",
                explanation="ایمیل‌های مشکوک می‌توانند حمله فیشینگ باشند.",
                is_active=True,
            )

            db.add_all([q1, q2, q3])
            db.flush()

            db.add_all([
                QuestionOption(question_id=q1.id, option_text="123456", is_correct=False),
                QuestionOption(question_id=q1.id, option_text="نام خودمان", is_correct=False),
                QuestionOption(question_id=q1.id, option_text="رمز طولانی شامل حروف، عدد و نماد", is_correct=True),

                QuestionOption(question_id=q2.id, option_text="بله", is_correct=False),
                QuestionOption(question_id=q2.id, option_text="خیر", is_correct=True),
                QuestionOption(question_id=q2.id, option_text="فقط در مواقع ضروری", is_correct=False),

                QuestionOption(question_id=q3.id, option_text="روی لینک کلیک کنیم", is_correct=False),
                QuestionOption(question_id=q3.id, option_text="روی فایل ضمیمه کلیک کنیم", is_correct=False),
                QuestionOption(question_id=q3.id, option_text="روی لینک کلیک نکنیم و گزارش دهیم", is_correct=True),
            ])

            stage = DailyStage(
                stage_date=today,
                difficulty="easy",
                question_count=3,
                max_score=30,
                is_active=True,
            )

            db.add(stage)
            db.flush()

            db.add_all([
                StageQuestion(stage_id=stage.id, question_id=q1.id, sort_order=1),
                StageQuestion(stage_id=stage.id, question_id=q2.id, sort_order=2),
                StageQuestion(stage_id=stage.id, question_id=q3.id, sort_order=3),
            ])
        db.commit()
    finally:
        db.close()
