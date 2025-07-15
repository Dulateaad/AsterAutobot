import os
import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import Router
from dotenv import load_dotenv
from knowledge_base import find_relevant_chunks, load_documents, knowledge_base
import openai

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

openai.api_key = OPENAI_API_KEY

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()
router = Router()
dp.include_router(router)

user_states = {}
user_results = {}

THEMES = {
    "Гарантия 365": {
        "presentation": "files/presentation.pdf",
        "video_url": "https://youtu.be/fdVDF42lehU",
        "quiz": [
            {
                "q": "1. Что входит в гарантийный ремонт по программе \"Гарантия 365\"?",
                "options": ["A) Только работа", "B) Только запчасти", "C) Только расходные материалы", "D) Работа, запчасти и расходные материалы"],
                "answer": 3
            },
            {
                "q": "2. Есть ли ограничение по количеству обращений?",
                "options": ["A) Да, не более трёх", "B) Да, не более пяти", "C) Нет ограничений по количеству обращений", "D) Только одно обращение"],
                "answer": 2
            }
        ]
    }
}

@router.message(Command("start"))
async def start(message: Message):
    keyboard = [["📌 Гарантия 365"], ["📂 Мои результаты", "❓ Задать вопрос"], ["🧠 Потренироваться"]]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await message.answer("👋 Добро пожаловать! Выберите тему или режим:", reply_markup=markup)

@router.message(F.text)
async def handle_message(message: Message):
    user_id = message.from_user.id
    text = message.text.strip()

    if text == "📌 Гарантия 365":
        user_states[user_id] = {"mode": "theme", "theme": "Гарантия 365", "current": 0, "score": 0}
        await message.answer_document(open(THEMES["Гарантия 365"]["presentation"], "rb"))
        await message.answer(f"🎬 Видео: {THEMES['Гарантия 365']['video_url']}")
        await message.answer("🧪 Когда будете готовы, нажмите кнопку ниже для начала квиза.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🧪 Пройти квиз", callback_data="start_quiz")]]))
        return

    if text == "📂 Мои результаты":
        results = user_results.get(user_id, [])
        if not results:
            await message.answer("📭 Вы ещё не проходили квизы.")
        else:
            result_text = "🗂 Ваши результаты:\n" + "\n".join(
                [f"• {r['theme']} — {r['score']}/{r['total']} ({r['date']})" for r in results]
            )
            await message.answer(result_text)
        return

    if text == "❓ Задать вопрос":
        user_states[user_id] = {"mode": "chat"}
        await message.answer("✍️ Введите свой вопрос:")
        return

    if text == "🧠 Потренироваться":
        user_states[user_id] = {"mode": "select_role"}
        markup = ReplyKeyboardMarkup(keyboard=[["🙋‍♂️ Я клиент", "💼 Я менеджер"]], resize_keyboard=True)
        await message.answer("Выберите роль:", reply_markup=markup)
        return

    if text == "🙋‍♂️ Я клиент":
        user_states[user_id] = {"mode": "train", "role": "client"}
        markup = ReplyKeyboardMarkup(keyboard=[["⬅️ Назад в меню"]], resize_keyboard=True)
        await message.answer("Отлично! Задавайте свои вопросы как клиент.", reply_markup=markup)
        return

    if text == "💼 Я менеджер":
        user_states[user_id] = {"mode": "train", "role": "manager"}
        markup = ReplyKeyboardMarkup(keyboard=[["⬅️ Назад в меню"]], resize_keyboard=True)
        await message.answer("Хорошо! Задавайте вопросы, как менеджер.", reply_markup=markup)
        return

    if text == "⬅️ Назад в меню":
        await start(message)
        return

    mode = user_states.get(user_id, {}).get("mode", "")
    if mode in ["chat", "train"]:
        role = user_states[user_id].get("role", "client")
        context_chunks = find_relevant_chunks(text, role) if mode == "train" else []

        system_prompt = {
            "chat": "Ты — помощник автосалона. Отвечай кратко и по делу.",
            "client": "Ты — консультант AsterAuto. Отвечай как клиенту: просто, уверенно и по делу.",
            "manager": "Ты — тренер для новых менеджеров AsterAuto. Объясняй профессионально и с опорой на скрипты."
        }[role if mode == "train" else "chat"]

        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt + ("\n\n📚 Информация:\n" + "\n---\n".join(context_chunks) if context_chunks else "")},
                    {"role": "user", "content": text}
                ]
            )
            await message.answer(response["choices"][0]["message"]["content"].strip())
        except Exception as e:
            await message.answer(f"⚠ Ошибка OpenAI: {str(e)}")

@router.callback_query()
async def handle_callback(callback):
    user_id = callback.from_user.id
    data = callback.data
    await callback.answer()

    if data == "start_quiz":
        user_states[user_id]["mode"] = "quiz"
        user_states[user_id]["current"] = 0
        user_states[user_id]["score"] = 0
        await send_question(callback.message.chat.id, user_id)
        return

    if ":" in data:
        q_index, selected = map(int, data.split(":"))
        theme = user_states[user_id]["theme"]
        quiz = THEMES[theme]["quiz"]
        correct = quiz[q_index]["answer"]
        if selected == correct:
            user_states[user_id]["score"] += 1
        user_states[user_id]["current"] += 1
        await send_question(callback.message.chat.id, user_id)

async def send_question(chat_id, user_id):
    state = user_states[user_id]
    theme = state["theme"]
    quiz = THEMES[theme]["quiz"]
    index = state["current"]

    if index >= len(quiz):
        score = state["score"]
        total = len(quiz)
        user_results.setdefault(user_id, []).append({
            "theme": theme,
            "score": score,
            "total": total,
            "date": datetime.datetime.now().strftime("%Y-%m-%d")
        })
        user_states[user_id]["mode"] = "theme"
        await bot.send_message(chat_id, f"✅ Квиз завершён!\nВы ответили правильно на {score} из {total}.")
        return

    q = quiz[index]
    buttons = [[InlineKeyboardButton(text=opt, callback_data=f"{index}:{i}")] for i, opt in enumerate(q["options"])]
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    await bot.send_message(chat_id, f"🧪 {q['q']}", reply_markup=markup)

@router.message(Command("обновить_базу"))
async def reload_knowledge(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Только админ может обновить базу.")
        return

    try:
        knowledge_base.clear()
        knowledge_base.extend(load_documents())
        await message.answer("🔄 База знаний успешно обновлена!")
    except Exception as e:
        await message.answer(f"❌ Ошибка при обновлении базы: {e}")

# 🔁 Запуск
import asyncio

if __name__ == "__main__":
    async def main():
        print("🚀 Бот AsterAuto запущен на aiogram!")
        await dp.start_polling(bot)

    asyncio.run(main())