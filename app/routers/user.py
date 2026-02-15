from __future__ import annotations

from aiogram import Router, F
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, func
from datetime import timedelta

from ..models import User, Test, Question, Attempt, Answer
from ..keyboards import kb_main_user, kb_main_admin, kb_abcd
from ..utils import now_utc, seconds_between

router = Router()


# ===================== FSM =====================

class RegisterFSM(StatesGroup):
    full_name = State()
    phone = State()


class StartTestFSM(StatesGroup):
    waiting_test_id = State()


# ===================== Helpers =====================

async def _get_user(session, tg_id: int) -> User | None:
    q = await session.execute(select(User).where(User.telegram_id == tg_id))
    return q.scalar_one_or_none()


def _main_kb_for(message: Message, config):
    return kb_main_admin() if message.from_user.id in config.admin_ids else kb_main_user()


async def _send_question(target: Message | CallbackQuery, session, attempt: Attempt, q_index: int) -> bool:
    q = await session.execute(
        select(Question).where(
            Question.test_id == attempt.test_id,
            Question.order_index == q_index
        )
    )
    question = q.scalar_one_or_none()
    if not question:
        return False

    text = (
        f"🧪 Savol {q_index}\n\n"
        f"{question.q_text}\n\n"
        f"A) {question.a_text}\n"
        f"B) {question.b_text}\n"
        f"C) {question.c_text}\n"
        f"D) {question.d_text}\n"
    )

    if isinstance(target, CallbackQuery):
        await target.message.answer(text, reply_markup=kb_abcd(attempt.id, q_index))
    else:
        await target.answer(text, reply_markup=kb_abcd(attempt.id, q_index))
    return True


# ===================== Registration =====================

@router.message(F.text == "📝 Ro‘yxatdan o‘tish")
async def reg_start(message: Message, state: FSMContext, config, sessionmaker):
    async with sessionmaker() as session:
        user = await _get_user(session, message.from_user.id)

    if user:
        await message.answer(
            "Siz allaqachon ro‘yxatdan o‘tgansiz ✅",
            reply_markup=_main_kb_for(message, config),
        )
        return

    await state.set_state(RegisterFSM.full_name)
    await message.answer("Ism Familiyangizni kiriting:")


@router.message(RegisterFSM.full_name)
async def reg_fullname(message: Message, state: FSMContext):
    name = (message.text or "").strip()
    if len(name) < 3:
        await message.answer("Iltimos, to‘liq ism kiriting (kamida 3 belgi).")
        return

    await state.update_data(full_name=name)
    await state.set_state(RegisterFSM.phone)
    await message.answer("Telefon raqamingiz (ixtiyoriy). Xohlamasangiz, 0 yuboring:")


@router.message(RegisterFSM.phone)
async def reg_phone(message: Message, state: FSMContext, config, sessionmaker):
    data = await state.get_data()
    phone = (message.text or "").strip()
    if phone == "0":
        phone = None

    async with sessionmaker() as session:
        session.add(
            User(
                telegram_id=message.from_user.id,
                full_name=data["full_name"],
                phone=phone,
            )
        )
        await session.commit()

    await state.clear()
    await message.answer("Ro‘yxatdan o‘tdingiz ✅", reply_markup=_main_kb_for(message, config))


# ===================== Results =====================

@router.message(F.text == "📊 Natijalarim")
async def my_results(message: Message, config, sessionmaker):
    async with sessionmaker() as session:
        user = await _get_user(session, message.from_user.id)
        if not user:
            await message.answer(
                "Avval ro‘yxatdan o‘ting: 📝 Ro‘yxatdan o‘tish",
                reply_markup=_main_kb_for(message, config),
            )
            return

        q = await session.execute(
            select(Attempt, Test)
            .join(Test, Attempt.test_id == Test.id)
            .where(
                Attempt.telegram_id == user.telegram_id,
                Attempt.status != "in_progress",
            )
            .order_by(Attempt.id.desc())
            .limit(10)
        )
        rows = q.all()

    if not rows:
        await message.answer("Hali natijalar yo‘q.")
        return

    lines = ["📊 Oxirgi natijalaringiz (10 ta):\n"]
    for att, test in rows:
        lines.append(
            f"• {test.public_id} — {att.score}/{att.total} ({att.percent}%) — {att.time_spent_sec}s — {att.status}"
        )
    await message.answer("\n".join(lines))


# ===================== Start test =====================

@router.message(F.text == "🧪 Test ishlash")
async def test_start(message: Message, state: FSMContext, config, sessionmaker):
    async with sessionmaker() as session:
        user = await _get_user(session, message.from_user.id)

    if not user:
        await message.answer(
            "Avval ro‘yxatdan o‘ting: 📝 Ro‘yxatdan o‘tish",
            reply_markup=_main_kb_for(message, config),
        )
        return

    await state.set_state(StartTestFSM.waiting_test_id)
    await message.answer("Test ID ni kiriting (masalan: T38471):")


@router.message(StartTestFSM.waiting_test_id)
async def test_id_received(message: Message, state: FSMContext, config, sessionmaker):
    public_id = (message.text or "").strip().upper()

    async with sessionmaker() as session:
        # test exists?
        tq = await session.execute(
            select(Test).where(Test.public_id == public_id, Test.is_active == True)
        )
        test = tq.scalar_one_or_none()
        if not test:
            await message.answer("Bunday test topilmadi ❌ ID ni tekshirib qayta yuboring.")
            return

        # count questions
        qc = await session.execute(
            select(func.count(Question.id)).where(Question.test_id == test.id)
        )
        total = int(qc.scalar() or 0)
        if total == 0:
            await message.answer("Bu testda savollar yo‘q (admin hali kiritmagan).")
            return

        # create attempt
        attempt = Attempt(
            test_id=test.id,
            telegram_id=message.from_user.id,
            started_at=now_utc(),
            total=total,
            status="in_progress",
        )
        session.add(attempt)
        await session.commit()
        await session.refresh(attempt)

        # important: these values needed after session close
        test_title = test.title
        test_minutes = test.duration_sec // 60
        attempt_id = attempt.id

    await state.clear()
    await message.answer(
        f"✅ Test boshlandi: {test_title}\n⏳ Vaqt: {test_minutes} daqiqa\nSavollar ketma-ket chiqadi."
    )

    async with sessionmaker() as session:
        a = await session.get(Attempt, attempt_id)
        await _send_question(message, session, a, 1)


# ===================== Answer callback =====================

@router.callback_query(F.data.startswith("ans:"))
async def answer_callback(call: CallbackQuery, config, sessionmaker):
    try:
        _, attempt_id, q_index, chosen = call.data.split(":")
        attempt_id = int(attempt_id)
        q_index = int(q_index)
        chosen = chosen.upper()
        if chosen not in {"A", "B", "C", "D"}:
            raise ValueError
    except Exception:
        await call.answer("Xatolik: callback noto‘g‘ri")
        return

    async with sessionmaker() as session:
        attempt = await session.get(Attempt, attempt_id)
        if not attempt:
            await call.answer("Attempt topilmadi")
            return

        # only owner can answer
        if attempt.telegram_id != call.from_user.id:
            await call.answer("Bu test sizniki emas.")
            return

        test = await session.get(Test, attempt.test_id)
        if not test:
            await call.answer("Test topilmadi.")
            return

        # time check
        deadline = attempt.started_at + timedelta(seconds=test.duration_sec)
        if now_utc() > deadline:
            attempt.finished_at = now_utc()
            attempt.status = "timeout"
            attempt.time_spent_sec = seconds_between(attempt.started_at, attempt.finished_at)
            attempt.percent = int(round((attempt.score / max(attempt.total, 1)) * 100))
            await session.commit()

            await call.message.answer(
                f"⏰ Vaqt tugadi! Test yakunlandi (timeout).\n"
                f"Natija: {attempt.score}/{attempt.total} ({attempt.percent}%)"
            )
            await call.answer()
            return

        # get question
        qq = await session.execute(
            select(Question).where(
                Question.test_id == attempt.test_id,
                Question.order_index == q_index
            )
        )
        question = qq.scalar_one_or_none()
        if not question:
            await call.answer("Savol topilmadi")
            return

        # prevent double-answer
        exists = await session.execute(
            select(Answer).where(
                Answer.attempt_id == attempt.id,
                Answer.question_id == question.id
            )
        )
        if exists.scalar_one_or_none():
            await call.answer("Bu savolga javob berilgandi.")
            return

        is_correct = (chosen == question.correct.upper())

        session.add(
            Answer(
                attempt_id=attempt.id,
                question_id=question.id,
                chosen=chosen,
                is_correct=is_correct,
            )
        )
        if is_correct:
            attempt.score += 1

        await session.commit()

        # next question?
        next_index = q_index + 1
        if next_index > attempt.total:
            attempt.finished_at = now_utc()
            attempt.status = "finished"
            attempt.time_spent_sec = seconds_between(attempt.started_at, attempt.finished_at)
            attempt.percent = int(round((attempt.score / max(attempt.total, 1)) * 100))
            await session.commit()

            await call.message.answer(
                f"✅ Test tugadi!\n"
                f"Natija: {attempt.score}/{attempt.total} ({attempt.percent}%)\n"
                f"⏱ Sarflangan vaqt: {attempt.time_spent_sec}s"
            )
            await call.answer()
            return

        await call.answer("Qabul qilindi ✅")
        # send next
        await _send_question(call, session, attempt, next_index)