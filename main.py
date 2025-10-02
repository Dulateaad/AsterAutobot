from telebot import TeleBot, types

BOT_TOKEN = "8033791209:AAHZEszg8dT5SYjEpojaFDillogwmfldi5I
"   # ← сюда вставляешь токен
bot = TeleBot(BOT_TOKEN, parse_mode="HTML")

@bot.message_handler(commands=['start'])
def handle_start(message):
    # Inline-кнопка только для мини-аппа
    webapp_markup = types.InlineKeyboardMarkup()
    webapp_markup.add(
        types.InlineKeyboardButton(
            text="🚀 Открыть мини-приложение",
            web_app=types.WebAppInfo(
                url="https://studio--studio-3657135238-fd27e.us-central1.hosted.app"
            )
        )
    )

    bot.send_message(message.chat.id, "📲 Нажмите кнопку, чтобы открыть мини-приложение:", reply_markup=webapp_markup)

if __name__ == "__main__":
    print("🚀 Бот запущен!")
    bot.infinity_polling()
