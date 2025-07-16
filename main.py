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
    "Реакционные скрипты Литро": {
        "presentation": "presentations/реакционные скрипты Литро.pdf",
        "quiz": [
            {
                "q": "1. “Мне не нужна техпомощь, я сам справлюсь”",
                "options": [
                    "A) Хорошо, если вы уверены в себе, то вам действительно не нужна наша услуга",
                    "B) Понимаю, если всё идёт по плану, техпомощь может и не понадобиться. Но на дороге случаются неожиданные вещи: спустило колесо, села батарея, заглох двигатель, кончился бензин или ошибка в электронике. ЛИТРО — это круглосуточная поддержка и экономия ваших нервов и времени",
                    "C) Каждый водитель думает, что справится сам, но статистика показывает обратное",
                    "D) Техпомощь нужна всем без исключения, даже самым опытным водителям",
                    "E) Вы можете попробовать сами, но потом всё равно придётся обращаться к нам"
                ],
                "answer": 1
            },
            # ... другие вопросы
        ]
    },
    "Гарантия 365": {
        "presentation": "presentations/presentation.pdf",
        "quiz": [
            {
                "q": "1. Как долго действует Гарантия 365?",
                "options": [
                    "A) 30 дней",
                    "B) 6 месяцев",
                    "C) 12 месяцев",
                    "D) Пожизненно"
                ],
                "answer": 2
            }
        ]
    }
}

@bot.message_handler(commands=['start'])
def handle_start(message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("📌 Реакционные скрипты Литро", "📌 Гарантия 365")
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

@bot.message_handler(func=lambda m: True)
def handle_text(message):
    user_id = message.from_user.id
    text = message.text.strip()

    if text == "📌 Реакционные скрипты Литро":
        user_states[user_id] = {"mode": "theme", "theme": "Реакционные скрипты Литро", "current": 0, "score": 0}
        try:
            with open(THEMES["Реакционные скрипты Литро"]["presentation"], "rb") as doc:
                bot.send_document(message.chat.id, doc)
        except Exception as e:
            bot.send_message(message.chat.id, f"⚠️ Ошибка при отправке презентации: {e}")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🧪 Пройти квиз", callback_data="start_quiz"))
        bot.send_message(message.chat.id, "🧪 Когда будете готовы, нажмите кнопку ниже для начала квиза.", reply_markup=markup)

    elif text == "📌 Гарантия 365":
        user_states[user_id] = {"mode": "theme", "theme": "Гарантия 365", "current": 0, "score": 0}
        try:
            with open(THEMES["Гарантия 365"]["presentation"], "rb") as doc:
                bot.send_document(message.chat.id, doc, caption="🎥 Видео: https://youtu.be/fdVDF42lehU")
        except Exception as e:
            bot.send_message(message.chat.id, f"⚠️ Ошибка при отправке презентации: {e}")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🧪 Пройти квиз", callback_data="start_quiz_365"))
        bot.send_message(message.chat.id, "🧪 Когда будете готовы, нажмите кнопку ниже для начала квиза.", reply_markup=markup)

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

@bot.callback_query_handler(func=lambda call: call.data.startswith("start_quiz") or ":" in call.data)
def handle_callback(call):
    user_id = call.from_user.id
    data = call.data
    chat_id = call.message.chat.id

    if data.startswith("start_quiz"):
        theme = "Реакционные скрипты Литро" if data == "start_quiz" else "Гарантия 365"
        user_states[user_id]["mode"] = "quiz"
        user_states[user_id]["theme"] = theme
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

if __name__ == "__main__":
    print("🚀 Бот запущен на pyTelegramBotAPI!")
    bot.infinity_polling()