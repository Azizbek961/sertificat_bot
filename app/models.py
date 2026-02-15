from sqlalchemy import String, Integer, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from .db import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    attempts: Mapped[list["Attempt"]] = relationship(back_populates="user")

class Test(Base):
    __tablename__ = "tests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # internal id
    public_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)  # e.g. T38471
    title: Mapped[str] = mapped_column(String(255))
    duration_sec: Mapped[int] = mapped_column(Integer, default=0)
    created_by_admin_id: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    questions: Mapped[list["Question"]] = relationship(back_populates="test", cascade="all, delete-orphan")
    attempts: Mapped[list["Attempt"]] = relationship(
        back_populates="test",
        cascade="all, delete-orphan"
    )

class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id"))
    order_index: Mapped[int] = mapped_column(Integer)
    q_text: Mapped[str] = mapped_column(Text)
    a_text: Mapped[str] = mapped_column(Text)
    b_text: Mapped[str] = mapped_column(Text)
    c_text: Mapped[str] = mapped_column(Text)
    d_text: Mapped[str] = mapped_column(Text)
    correct: Mapped[str] = mapped_column(String(1))  # A/B/C/D

    test: Mapped["Test"] = relationship(back_populates="questions")
    answers: Mapped[list["Answer"]] = relationship(back_populates="question")

class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id"))
    telegram_id: Mapped[int] = mapped_column(ForeignKey("users.telegram_id"))

    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    score: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=0)
    percent: Mapped[int] = mapped_column(Integer, default=0)
    time_spent_sec: Mapped[int] = mapped_column(Integer, default=0)

    status: Mapped[str] = mapped_column(String(20), default="in_progress")  # finished / timeout / in_progress

    test: Mapped["Test"] = relationship(back_populates="attempts")
    user: Mapped["User"] = relationship(back_populates="attempts", primaryjoin="User.telegram_id==Attempt.telegram_id")
    answers: Mapped[list["Answer"]] = relationship(back_populates="attempt", cascade="all, delete-orphan")

class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("attempts.id"))
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    chosen: Mapped[str] = mapped_column(String(1))  # A/B/C/D
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)

    attempt: Mapped["Attempt"] = relationship(back_populates="answers")
    question: Mapped["Question"] = relationship(back_populates="answers")