from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import BaseFilter
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from ..models import Test, Question, Attempt, User
from ..utils import make_test_public_id
from sqlalchemy import select, func
from aiogram.types import CallbackQuery
router = Router()


# ===================== Filters / FSM =====================

class AdminOnly(BaseFilter):
    async def __call__(self, message: Message, config) -> bool:
        return message.from_user.id in config.admin_ids

class DeleteTestFSM(StatesGroup):
    waiting_test_id = State()
class CreateTestFSM(StatesGroup):
    title = State()
    duration_min = State()
    question_count = State()

    q_text = State()
    a_text = State()
    b_text = State()
    c_text = State()
    d_text = State()
    correct = State()


class AdminWhoFSM(StatesGroup):
    waiting_test_id = State()


# ===================== Create Test =====================

@router.message(AdminOnly(), F.text == "➕ Test yaratish")
async def admin_create_test_start(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(CreateTestFSM.title)
    await state.update_data(q_total=0, q_current=0, test_id=None)
    await message.answer("🧩 Test nomini kiriting:")


@router.message(CreateTestFSM.title)
async def admin_create_test_title(message: Message, state: FSMContext):
    title = (message.text or "").strip()
    if len(title) < 3:
        await message.answer("Kamida 3 belgi bo‘lsin. Qayta kiriting:")
        return

    await state.update_data(title=title)
    await state.set_state(CreateTestFSM.duration_min)
    await message.answer("⏳ Test vaqti (daqiqada). Masalan: 20")


@router.message(CreateTestFSM.duration_min)
async def admin_create_test_duration(message: Message, state: FSMContext):
    raw = (message.text or "").strip()
    if not raw.isdigit():
        await message.answer("Faqat son kiriting. Masalan: 20")
        return

    minutes = int(raw)
    if minutes <= 0 or minutes > 300:
        await message.answer("1..300 oralig‘ida kiriting.")
        return

    await state.update_data(duration_sec=minutes * 60)
    await state.set_state(CreateTestFSM.question_count)
    await message.answer("Nechta savol bo‘ladi? Masalan: 10")


@router.message(CreateTestFSM.question_count)
async def admin_create_test_qcount(message: Message, state: FSMContext, sessionmaker):
    raw = (message.text or "").strip()
    if not raw.isdigit():
        await message.answer("Faqat son kiriting. Masalan: 10")
        return

    q_total = int(raw)
    if q_total <= 0 or q_total > 200:
        await message.answer("1..200 oralig‘ida kiriting.")
        return

    data = await state.get_data()
    public_id = make_test_public_id()

    async with sessionmaker() as session:
        test = Test(
            public_id=public_id,
            title=data["title"],
            duration_sec=data["duration_sec"],
            created_by_admin_id=message.from_user.id,
            is_active=True,
        )
        session.add(test)
        await session.commit()
        await session.refresh(test)

        test_id = test.id  # needed after session close

    await state.update_data(test_id=test_id, public_id=public_id, q_total=q_total, q_current=1)
    await state.set_state(CreateTestFSM.q_text)
    await message.answer(
        f"✅ Test yaratildi. ID: {public_id}\n\n"
        f"1-savol matnini yuboring:"
    )


@router.message(CreateTestFSM.q_text)
async def admin_q_text(message: Message, state: FSMContext):
    txt = (message.text or "").strip()
    if len(txt) < 2:
        await message.answer("Savol matni bo‘sh bo‘lmasin. Qayta yuboring:")
        return
    await state.update_data(q_text=txt)
    await state.set_state(CreateTestFSM.a_text)
    await message.answer("A variantni yuboring:")


@router.message(CreateTestFSM.a_text)
async def admin_a(message: Message, state: FSMContext):
    await state.update_data(a_text=(message.text or "").strip())
    await state.set_state(CreateTestFSM.b_text)
    await message.answer("B variantni yuboring:")


@router.message(CreateTestFSM.b_text)
async def admin_b(message: Message, state: FSMContext):
    await state.update_data(b_text=(message.text or "").strip())
    await state.set_state(CreateTestFSM.c_text)
    await message.answer("C variantni yuboring:")


@router.message(CreateTestFSM.c_text)
async def admin_c(message: Message, state: FSMContext):
    await state.update_data(c_text=(message.text or "").strip())
    await state.set_state(CreateTestFSM.d_text)
    await message.answer("D variantni yuboring:")


@router.message(CreateTestFSM.d_text)
async def admin_d(message: Message, state: FSMContext):
    await state.update_data(d_text=(message.text or "").strip())
    await state.set_state(CreateTestFSM.correct)
    await message.answer("To‘g‘ri javob harfi (A/B/C/D) ni yuboring:")


@router.message(CreateTestFSM.correct)
async def admin_correct(message: Message, state: FSMContext, sessionmaker):
    correct = (message.text or "").strip().upper()
    if correct not in {"A", "B", "C", "D"}:
        await message.answer("Faqat A/B/C/D dan biri bo‘lsin.")
        return

    data = await state.get_data()
    test_id = data["test_id"]
    q_index = data["q_current"]
    q_total = data["q_total"]

    async with sessionmaker() as session:
        q = Question(
            test_id=test_id,
            order_index=q_index,
            q_text=data["q_text"],
            a_text=data["a_text"],
            b_text=data["b_text"],
            c_text=data["c_text"],
            d_text=data["d_text"],
            correct=correct,
        )
        session.add(q)
        await session.commit()

    # next or finish
    if q_index >= q_total:
        await state.clear()
        await message.answer(f"🎉 Tayyor! Test ID: {data['public_id']}\nSavollar: {q_total}")
        return

    await state.update_data(q_current=q_index + 1)
    await state.set_state(CreateTestFSM.q_text)
    await message.answer(f"{q_index + 1}-savol matnini yuboring:")


# ===================== Tests List =====================

@router.message(AdminOnly(), F.text == "📥 Testlar ro‘yxati")
async def admin_tests_list(message: Message, sessionmaker):
    async with sessionmaker() as session:
        q = await session.execute(select(Test).order_by(Test.id.desc()).limit(10))
        tests = q.scalars().all()

    if not tests:
        await message.answer("Hali testlar yo‘q.")
        return

    lines = ["📥 Oxirgi 10 ta test:\n"]
    for t in tests:
        lines.append(f"• {t.public_id} — {t.title} — {t.duration_sec // 60} min — active={t.is_active}")
    await message.answer("\n".join(lines))


# ===================== Who solved =====================

@router.message(AdminOnly(), F.text == "👥 Kimlar ishlagan")
async def admin_who_start(message: Message, state: FSMContext):
    await state.set_state(AdminWhoFSM.waiting_test_id)
    await message.answer("Qaysi test? Test ID kiriting (masalan: T38471):")


@router.message(AdminWhoFSM.waiting_test_id)
async def admin_who_show(message: Message, state: FSMContext, sessionmaker):
    public_id = (message.text or "").strip().upper()
    await state.clear()

    async with sessionmaker() as session:
        tq = await session.execute(select(Test).where(Test.public_id == public_id))
        test = tq.scalar_one_or_none()
        if not test:
            await message.answer("Test topilmadi.")
            return

        aq = await session.execute(
            select(Attempt, User)
            .join(User, Attempt.telegram_id == User.telegram_id)
            .where(Attempt.test_id == test.id, Attempt.status != "in_progress")
            .order_by(Attempt.id.desc())
            .limit(30)
        )
        rows = aq.all()

    if not rows:
        await message.answer("Hali hech kim ishlamagan.")
        return

    lines = [f"👥 {public_id} — oxirgi 30 urinish:\n"]
    for att, user in rows:
        lines.append(
            f"• {user.full_name} (tg:{user.telegram_id}) — {att.score}/{att.total} ({att.percent}%) — {att.status}"
        )
    await message.answer("\n".join(lines))
@router.message(AdminOnly(), F.text == "🗑 Test o‘chirish")
async def admin_delete_test_start(message: Message, state: FSMContext):
    await state.set_state(DeleteTestFSM.waiting_test_id)
    await message.answer("🗑 Qaysi testni o‘chirasiz? Test ID kiriting (masalan: T89101):")


@router.message(DeleteTestFSM.waiting_test_id)
async def admin_delete_test_confirm(message: Message, state: FSMContext, sessionmaker):
    public_id = (message.text or "").strip().upper()
    await state.clear()

    async with sessionmaker() as session:
        tq = await session.execute(select(Test).where(Test.public_id == public_id))
        test = tq.scalar_one_or_none()
        if not test:
            await message.answer("Test topilmadi.")
            return

        # statistikani oldindan ko'rsatamiz
        q_count = await session.execute(select(func.count(Question.id)).where(Question.test_id == test.id))
        a_count = await session.execute(select(func.count(Attempt.id)).where(Attempt.test_id == test.id))
        questions = int(q_count.scalar() or 0)
        attempts = int(a_count.scalar() or 0)

        # o‘chirish
        await session.delete(test)
        await session.commit()

    await message.answer(
        f"✅ O‘chirildi: {public_id}\n"
        f"• Savollar: {questions}\n"
        f"• Urinishlar: {attempts}\n"
        f"(Urinishlar bilan birga javoblar ham o‘chirildi)"
    )