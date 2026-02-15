from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy import select
from ..models import User
from ..keyboards import kb_main_user, kb_main_admin

router = Router()

def is_admin(user_id: int, admin_ids: set[int]) -> bool:
    return user_id in admin_ids

@router.message(CommandStart())
async def start(message: Message, config, sessionmaker):
    async with sessionmaker() as session:
        q = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = q.scalar_one_or_none()

    if is_admin(message.from_user.id, config.admin_ids):
        await message.answer(
            "Salom! Siz admin sifatida kirdingiz.\nMenyudan foydalaning.",
            reply_markup=kb_main_admin(),
        )
        return

    if user:
        await message.answer("Salom! Menyudan foydalaning.", reply_markup=kb_main_user())
    else:
        await message.answer(
            "Salom! Avval ro‘yxatdan o‘ting: 📝 Ro‘yxatdan o‘tish",
            reply_markup=kb_main_user(),
        )