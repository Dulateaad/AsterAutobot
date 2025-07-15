import os
import datetime
import openai
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import (
    Message, CallbackQuery, FSInputFile,
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils import markdown
from aiogram import Router
from config import TELEGRAM_BOT_TOKEN, OPENAI_API_KEY, ADMIN_ID
from knowledge_base import find_relevant_chunks, load_documents, knowledge_base

openai.api_key = OPENAI_API_KEY

bot = Bot(token=TELEGRAM_BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()
router = Router()
dp.include_router(router)

user_states = {}
user_results = {}

THEMES = {
    "Гарантия 365": {
        "presentation": "presentations/presentation.pdf",
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

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📌 Гарантия 365")],
        [KeyboardButton(text="📂 Мои результаты"), KeyboardButton(text="❓ Задать вопрос")],
        [KeyboardButton(text="🧠 Потренироваться")]
    ],
    resize_keyboard=True
)

@router.message(CommandStart())
async def start_cmd(message: Message):
    await message.answer("👋 Добро пожаловать! Выберите тему или режим:", reply_markup=main_menu)

@router.message(F.text == "📌 Гарантия 365")
async def handle_theme(message: Message):
    user_id = message.from_user.id
    user_states[user_id] = {"mode": "theme", "theme": "Гарантия 365", "current": 0, "score": 0}

    pres_path = THEMES["Гарантия 365"]["presentation"]
    if os.path.exists(pres_path):
        doc = FSInputFile(pres_path)
        await message.answer_document(document=doc, caption="📄 Презентация:")
    else:
        await message.answer("⚠️ Презентация не найдена.")

    await message.answer(f"🎬 Видео: {THEMES['Гарантия 365']['video_url']}")

    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🧪 Пройти квиз", callback_data="start_quiz")]]
    )
    await message.answer("🧪 Когда будете готовы, нажмите кнопку ниже для начала квиза:", reply_markup=kb)
    @router.callback_query(F.data == "start_quiz")
async def start_quiz(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_states[user_id]["mode"] = "quiz"
    user_states[user_id]["current"] = 0
    user_states[user_id]["score"] = 0
    await callback.answer()
    await send_question(callback.message.chat.id, user_id)

@router.callback_query(F.data.regexp(r"^\d+:\d$"))
async def handle_answer(callback: CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data
    q_index, selected = map(int, data.split(":"))
    theme = user_states[user_id]["theme"]
    quiz = THEMES[theme]["quiz"]
    correct = quiz[q_index]["answer"]
    if selected == correct:
        user_states[user_id]["score"] += 1
    user_states[user_id]["current"] += 1
    await callback.answer()
    await send_question(callback.message.chat.id, user_id)

async def send_question(chat_id: int, user_id: int):
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
    buttons = [
        [InlineKeyboardButton(text=opt, callback_data=f"{index}:{i}")]
        for i, opt in enumerate(q["options"])
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await bot.send_message(chat_id, f"🧪 {q['q']}", reply_markup=kb)
    @router.message(F.text == "📂 Мои результаты")
async def show_results(message: Message):
    user_id = message.from_user.id
    results = user_results.get(user_id, [])
    if not results:
        await message.answer("📭 Вы ещё не проходили квизы.")
    else:
        result_text = "🗂 Ваши результаты:\n" + "\n".join(
            [f"• {r['theme']} — {r['score']}/{r['total']} ({r['date']})" for r in results]
        )
        await message.answer(result_text)

@router.message(F.text == "❓ Задать вопрос")
async def enter_chat_mode(message: Message):
    user_states[message.from_user.id] = {"mode": "chat"}
    await message.answer("✍️ Введите свой вопрос:")

@router.message(F.text == "🧠 Потренироваться")
async def enter_train_mode(message: Message):
    user_states[message.from_user.id] = {"mode": "select_role"}
    role_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("🙋‍♂️ Я клиент"), KeyboardButton("💼 Я менеджер")],
            [KeyboardButton("⬅️ Назад в меню")]
        ],
        resize_keyboard=True
    )
    await message.answer("Выберите роль:", reply_markup=role_keyboard)

@router.message(F.text.in_(["🙋‍♂️ Я клиент", "💼 Я менеджер"]))
async def select_role(message: Message):
    role = "client" if "клиент" in message.text else "manager"
    user_states[message.from_user.id] = {"mode": "train", "role": role}
    await message.answer(
        "Отлично! Задавайте свои вопросы." if role == "client"
        else "Хорошо! Задавайте вопросы, как менеджер.",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton("⬅️ Назад в меню")]],
            resize_keyboard=True
        )
    )

@router.message(F.text == "⬅️ Назад в меню")
async def back_to_menu(message: Message):
    await start_cmd(message)

# Обработка текстовых сообщений (чат, тренировка)
@router.message(F.text)
async def handle_general_text(message: Message):
    user_id = message.from_user.id
    text = message.text.strip()
    state = user_states.get(user_id, {})
    mode = state.get("mode", "")

    if mode not in ["chat", "train"]:
        return

    role = state.get("role", "client")
    system_prompt = {
        "chat": "Ты — помощник автосалона. Отвечай кратко и по делу.",
        "client": "Ты — консультант AsterAuto. Отвечай как клиенту: просто, уверенно и по делу.",
        "manager": "Ты — тренер для новых менеджеров AsterAuto. Объясняй профессионально и с опорой на скрипты."
    }[role if mode == "train" else "chat"]

    context_chunks = []
    if mode == "train":
        context_chunks = find_relevant_chunks(text, role)

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt + ("\n📚 Информация:\n" + "\n---\n".join(context_chunks) if context_chunks else "")},
                {"role": "user", "content": text}
            ]
        )
        await message.answer(response["choices"][0]["message"]["content"].strip())
    except Exception as e:
        await message.answer(f"⚠ Ошибка OpenAI: {str(e)}")
        @router.message(F.document)
async def handle_document(message: Message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        await message.answer("❌ У вас нет прав загружать документы.")
        return

    doc = message.document
    if not doc:
        await message.answer("⚠️ Не удалось получить файл.")
        return

    os.makedirs("presentations", exist_ok=True)
    file_path = f"presentations/{doc.file_name}"
    await bot.download(doc, destination=file_path)
    await message.answer(f"✅ Файл «{doc.file_name}» загружен в /presentations.")

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

# Запуск бота
import asyncio

if __name__ == "__main__":
    async def main():
        print("🚀 Бот AsterAuto запущен на aiogram!")
        await dp.start_polling(bot)

    asyncio.run(main())
     