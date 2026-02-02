import asyncio
import logging
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

from config import TOKEN, ADMIN_IDS
from db import init_db, add_booking, get_user_bookings, is_slot_taken

dp = Dispatcher()

# ================== STATE ==================
# user_id -> dict
state = {}

SERVICES = ["Стрижка", "Манікюр", "Масаж"]

TIME_SLOTS = [
    "10:00", "11:00", "12:00",
    "13:00", "14:00", "15:00",
    "16:00", "17:00", "18:00",
]

# ================== KEYBOARDS ==================

def main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 Записатись")],
            [KeyboardButton(text="🧾 Мої записи")]
        ],
        resize_keyboard=True
    )


def services_kb():
    rows = [[KeyboardButton(text=s)] for s in SERVICES]
    rows.append([KeyboardButton(text="⬅️ Назад")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def dates_kb():
    today = datetime.now()
    dates = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(1, 8)]

    rows = []
    for i in range(0, len(dates), 2):
        row = [KeyboardButton(text=dates[i])]
        if i + 1 < len(dates):
            row.append(KeyboardButton(text=dates[i + 1]))
        rows.append(row)

    rows.append([KeyboardButton(text="⬅️ Назад")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def times_kb(date):
    available = [t for t in TIME_SLOTS if not is_slot_taken(date, t)]
    rows = []

    for i in range(0, len(available), 3):
        rows.append([KeyboardButton(text=t) for t in available[i:i + 3]])

    if not rows:
        rows = [[KeyboardButton(text="❌ Немає вільних слотів")]]

    rows.append([KeyboardButton(text="⬅️ Назад")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def confirm_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="✅ Підтвердити"), KeyboardButton(text="❌ Скасувати")]],
        resize_keyboard=True
    )

# ================== ADMIN NOTIFY ==================

async def notify_admins(bot: Bot, text: str):
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text)
        except Exception as e:
            print(f"Не вдалося надіслати адміну {admin_id}: {e}")

# ================== HANDLERS ==================

@dp.message(CommandStart())
async def start(message: Message):
    state.pop(message.from_user.id, None)
    await message.answer(
        "👋 Привіт! Я бот для запису клієнтів.\nНатисни «📅 Записатись».",
        reply_markup=main_kb()
    )


@dp.message()
async def router(message: Message):
    user_id = message.from_user.id
    text = (message.text or "").strip()
    st = state.get(user_id)

    # ===== GLOBAL =====
    if text == "📅 Записатись":
        state[user_id] = {"step": "service"}
        await message.answer("Обери послугу:", reply_markup=services_kb())
        return

    if text == "🧾 Мої записи":
        rows = get_user_bookings(user_id)
        if not rows:
            await message.answer("Записів ще немає.", reply_markup=main_kb())
            return

        out = "🧾 Твої записи:\n\n"
        for service, date, time in rows:
            out += f"• {service} — {date} {time}\n"

        await message.answer(out, reply_markup=main_kb())
        return

    if text == "⬅️ Назад":
        state.pop(user_id, None)
        await message.answer("Повертаємось у меню.", reply_markup=main_kb())
        return

    # ===== NO STATE =====
    if not st:
        await message.answer("Натисни «📅 Записатись» 🙂", reply_markup=main_kb())
        return

    step = st["step"]

    # ===== SERVICE =====
    if step == "service":
        if text not in SERVICES:
            await message.answer("Обери послугу кнопкою 👇", reply_markup=services_kb())
            return

        st["service"] = text
        st["step"] = "date"
        await message.answer("📅 Обери дату:", reply_markup=dates_kb())
        return

    # ===== DATE =====
    if step == "date":
        if len(text) != 10 or text[4] != "-" or text[7] != "-":
            await message.answer("Обери дату кнопкою 👇", reply_markup=dates_kb())
            return

        st["date"] = text
        st["step"] = "time"
        await message.answer("⏰ Обери час:", reply_markup=times_kb(text))
        return

    # ===== TIME =====
    if step == "time":
        if text not in TIME_SLOTS:
            await message.answer("Обери час кнопкою 👇", reply_markup=times_kb(st["date"]))
            return

        if is_slot_taken(st["date"], text):
            await message.answer("❌ Цей час зайнятий. Обери інший:", reply_markup=times_kb(st["date"]))
            return

        st["time"] = text
        st["step"] = "name"
        await message.answer("✍️ Напиши своє ім’я:")
        return

    # ===== NAME =====
    if step == "name":
        if len(text) < 2:
            await message.answer("Ім’я занадто коротке.")
            return

        st["name"] = text
        st["step"] = "phone"
        await message.answer("📞 Введи номер телефону:")
        return

    # ===== PHONE =====
    if step == "phone":
        phone = text.replace(" ", "")
        if not (phone.startswith("+") and phone[1:].isdigit()):
            await message.answer("Невірний номер. Приклад: +380991234567")
            return

        st["phone"] = phone
        st["step"] = "confirm"

        await message.answer(
            f"✅ Підтверди запис:\n\n"
            f"🧾 {st['service']}\n"
            f"📅 {st['date']} {st['time']}\n"
            f"👤 {st['name']}\n"
            f"📞 {st['phone']}",
            reply_markup=confirm_kb()
        )
        return

    # ===== CONFIRM =====
    if step == "confirm":
        if text == "✅ Підтвердити":
            add_booking(
                user_id=user_id,
                service=st["service"],
                name=st["name"],
                phone=st["phone"],
                date=st["date"],
                time=st["time"]
            )

            admin_text = (
                "📢 НОВИЙ ЗАПИС\n\n"
                f"🧾 Послуга: {st['service']}\n"
                f"📅 Дата: {st['date']}\n"
                f"⏰ Час: {st['time']}\n"
                f"👤 Імʼя: {st['name']}\n"
                f"📞 Телефон: {st['phone']}\n"
                f"🆔 ID клієнта: {user_id}"
            )

            await notify_admins(message.bot, admin_text)

            state.pop(user_id, None)
            await message.answer("🎉 Запис збережено! Адміну надіслано повідомлення.", reply_markup=main_kb())
            return

        if text == "❌ Скасувати":
            state.pop(user_id, None)
            await message.answer("❌ Скасовано.", reply_markup=main_kb())
            return

        await message.answer("Обери кнопку 👇", reply_markup=confirm_kb())


# ================== MAIN ==================

async def main():
    logging.basicConfig(level=logging.INFO)
    init_db()
    bot = Bot(token=TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
