import os
import datetime
import telebot
from telebot import types
from dotenv import load_dotenv
from knowledge_base import find_relevant_chunks, load_documents, knowledge_base
import openai

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
openai.api_key = OPENAI_API_KEY

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

# == Команды ==

@bot.message_handler(commands=['start'])
def handle_start(message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("📌 Гарантия 365")
    keyboard.add("📂 Мои результаты", "❓ Задать вопрос")
    keyboard.add("🧠 Потренироваться")
    bot.send_message(message.chat.id, "👋 Добро пожаловать! Выберите тему или режим:", reply_markup=keyboard)

@bot.message_handler(commands=["обновить_базу"])
def reload_knowledge(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "⛔ Только админ может обновить базу.")
        return
    try:
        knowledge_base.clear()
        knowledge_base.extend(load_documents())
        bot.send_message(message.chat.id, "🔄 База знаний успешно обновлена!")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка при обновлении базы: {e}")

# == Обработка текстовых сообщений ==

@bot.message_handler(func=lambda m: True)
def handle_text(message):
    user_id = message.from_user.id
    text = message.text.strip()

    if text == "📌 Гарантия 365":
        user_states[user_id] = {"mode": "theme", "theme": "Гарантия 365", "current": 0, "score": 0}
        with open(THEMES["Гарантия 365"]["presentation"], "rb") as doc:
            bot.send_document(message.chat.id, doc)
        bot.send_message(message.chat.id, f"🎬 Видео: {THEMES['Гарантия 365']['video_url']}")
        btn = types.InlineKeyboardMarkup()
        btn.add(types.InlineKeyboardButton("🧪 Пройти квиз", callback_data="start_quiz"))
        bot.send_message(message.chat.id, "🧪 Нажмите кнопку ниже для начала квиза.", reply_markup=btn)

    elif text == "📂 Мои результаты":
        results = user_results.get(user_id, [])
        if not results:
            bot.send_message(message.chat.id, "📭 Вы ещё не проходили квизы.")
        else:
            result_text = "🗂 Ваши результаты:\n" + "\n".join(
                [f"• {r['theme']} — {r['score']}/{r['total']} ({r['date']})" for r in results]
            )
            bot.send_message(message.chat.id, result_text)

    elif text == "❓ Задать вопрос":
        user_states[user_id] = {"mode": "chat"}
        bot.send_message(message.chat.id, "✍️ Введите свой вопрос:")

    elif text == "🧠 Потренироваться":
        user_states[user_id] = {"mode": "select_role"}
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("🙋‍♂️ Я клиент", "💼 Я менеджер")
        bot.send_message(message.chat.id, "Выберите роль:", reply_markup=markup)

    elif text == "🙋‍♂️ Я клиент":
        user_states[user_id] = {"mode": "train", "role": "client"}
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("⬅️ Назад в меню")
        bot.send_message(message.chat.id, "Задайте вопрос как клиент.", reply_markup=markup)

    elif text == "💼 Я менеджер":
        user_states[user_id] = {"mode": "train", "role": "manager"}
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("⬅️ Назад в меню")
        bot.send_message(message.chat.id, "Задайте вопрос как менеджер.", reply_markup=markup)

    elif text == "⬅️ Назад в меню":
        handle_start(message)

    else:
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
                bot.send_message(message.chat.id, response['choices'][0]['message']['content'].strip())
            except Exception as e:
                bot.send_message(message.chat.id, f"⚠ Ошибка OpenAI: {e}")

# == Квизы ==

@bot.callback_query_handler(func=lambda call: call.data == "start_quiz" or ":" in call.data)
def handle_callback(call):
    user_id = call.from_user.id
    data = call.data
    chat_id = call.message.chat.id

    if data == "start_quiz":
        user_states[user_id]["mode"] = "quiz"
        user_states[user_id]["current"] = 0
        user_states[user_id]["score"] = 0
        send_question(chat_id, user_id)
    else:
        q_index, selected = map(int, data.split(":"))
        theme = user_states[user_id]["theme"]
        correct = THEMES[theme]["quiz"][q_index]["answer"]
        if selected == correct:
            user_states[user_id]["score"] += 1
        user_states[user_id]["current"] += 1
        send_question(chat_id, user_id)

def send_question(chat_id, user_id):
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
        bot.send_message(chat_id, f"✅ Квиз завершён!\nВы ответили правильно на {score} из {total}.")
        return

    q = quiz[index]
    markup = types.InlineKeyboardMarkup()
    for i, option in enumerate(q["options"]):
        markup.add(types.InlineKeyboardButton(option, callback_data=f"{index}:{i}"))
    bot.send_message(chat_id, f"🧪 {q['q']}", reply_markup=markup)

# == Запуск ==

if __name__ == "__main__":
    print("🚀 Бот запущен на pyTelegramBotAPI!")
    bot.infinity_polling()