import os
import datetime
import openai
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    MessageHandler, CallbackQueryHandler, filters
)
from config import TELEGRAM_BOT_TOKEN, OPENAI_API_KEY

client = openai.OpenAI(api_key=OPENAI_API_KEY)
user_states = {}
user_results = {}

THEMES = {
    "Гарантия 365": {
        "presentation": "files/presentation.pdf",
        "video_url": "https://youtu.be/fdVDF42lehU",
        "quiz": [
            {
                "q": "1. Что входит в гарантийный ремонт по программе \"\u0413арантия 365\"?",
                "options": [
                    "A) Только работа",
                    "B) Только запчасти",
                    "C) Только расходные материалы",
                    "D) Работа, запчасти и расходные материалы"
                ],
                "answer": 3
            },
            {
                "q": "2. Есть ли ограничение по количеству обращений?",
                "options": [
                    "A) Да, не более трёх",
                    "B) Да, не более пяти",
                    "C) Нет ограничений по количеству обращений",
                    "D) Только одно обращение"
                ],
                "answer": 2
            }
        ]
    }
}

# Остальные функции (start, handle_message, handle_callback, send_question, main) остаются без изменений
