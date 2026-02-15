from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def kb_main_user() -> ReplyKeyboardMarkup:
    b = ReplyKeyboardBuilder()
    b.add(
        KeyboardButton(text="📝 Ro‘yxatdan o‘tish"),
        KeyboardButton(text="🧪 Test ishlash"),
        KeyboardButton(text="📊 Natijalarim"),
    )
    b.adjust(2, 1)
    return b.as_markup(resize_keyboard=True)

def kb_main_admin() -> ReplyKeyboardMarkup:
    b = ReplyKeyboardBuilder()
    b.add(
        KeyboardButton(text="➕ Test yaratish"),
        KeyboardButton(text="👥 Kimlar ishlagan"),
        KeyboardButton(text="📥 Testlar ro‘yxati"),
        KeyboardButton(text="🗑 Test o‘chirish"),
    )
    b.add(
        KeyboardButton(text="🧪 Test ishlash"),
        KeyboardButton(text="📊 Natijalarim"),
    )
    b.adjust(2, 1, 2)
    return b.as_markup(resize_keyboard=True)

def kb_abcd(attempt_id: int, q_index: int) -> InlineKeyboardMarkup:
    ib = InlineKeyboardBuilder()
    for letter in ["A", "B", "C", "D"]:
        ib.button(text=letter, callback_data=f"ans:{attempt_id}:{q_index}:{letter}")
    ib.adjust(4)
    return ib.as_markup()
def kb_page(public_id: str, page: int, page_size: int, has_prev: bool, has_next: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if has_prev:
        kb.button(text="⬅️ Oldingi", callback_data=f"who:{public_id}:{page-1}:{page_size}")
    if has_next:
        kb.button(text="Keyingi ➡️", callback_data=f"who:{public_id}:{page+1}:{page_size}")
    kb.adjust(2)
    return kb.as_markup()