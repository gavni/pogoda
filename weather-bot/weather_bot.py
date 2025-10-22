import requests
import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)

BOT_TOKEN = "8121284557:AAGbNf3gx-01ky9eMvvDz1lBzeaVVSYy8YU"
WEATHER_API_KEY = "1f05fee41cdd2b188dab20e93e39d633"

WAITING_FOR_CITY = 1
user_settings = {}

def get_weather(city):
    url = "http://api.openweathermap.org/data/2.5/weather"
    params = {"q": city, "appid": WEATHER_API_KEY, "units": "metric", "lang": "ru"}
    r = requests.get(url, params=params)
    data = r.json()
    if data.get("cod") != 200:
        return "⚠️ Не удалось получить данные о погоде. Проверьте название города."
    temp = data["main"]["temp"]
    feels = data["main"]["feels_like"]
    desc = data["weather"][0]["description"].capitalize()
    humidity = data["main"]["humidity"]
    wind = data["wind"]["speed"]
    return (f"🌦 Погода в {city}:\n"
            f"Температура: {temp}°C (ощущается как {feels}°C)\n"
            f"Состояние: {desc}\n"
            f"Влажность: {humidity}%\n"
            f"Ветер: {wind} м/с")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_settings[user_id] = {"city": "Сигаево, Удмуртская Республика", "auto_update": False, "task": None}
    keyboard = [["🌍 Найти город", "🌤 Текущая погода", "🔁 Автообновление (вкл/выкл)"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    weather_info = get_weather(user_settings[user_id]["city"])
    await update.message.reply_text(f"👋 Привет!\n\n{weather_info}", reply_markup=reply_markup)

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    user = user_settings.get(user_id)
    if text == "🌍 Найти город":
        await update.message.reply_text("Введите название города:")
        return WAITING_FOR_CITY
    if text == "🌤 Текущая погода":
        if not user:
            await update.message.reply_text("Сначала напиши /start.")
        else:
            weather_info = get_weather(user["city"])
            await update.message.reply_text(f"🌤 Текущая погода в {user['city']}:\n\n{weather_info}")
        return ConversationHandler.END
    if text == "🔁 Автообновление (вкл/выкл)":
        if not user:
            await update.message.reply_text("Сначала напиши /start.")
            return ConversationHandler.END
        if user["auto_update"]:
            user["auto_update"] = False
            if user["task"]:
                user["task"].cancel()
                user["task"] = None
            await update.message.reply_text("⛔️ Автообновление отключено.")
        else:
            user["auto_update"] = True
            user["task"] = asyncio.create_task(auto_update_weather(update, context))
            await update.message.reply_text("✅ Автообновление включено (каждый час).")
    return ConversationHandler.END

async def set_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    city = update.message.text
    user_settings[user_id]["city"] = city
    weather_info = get_weather(city)
    await update.message.reply_text(f"✅ Город обновлён на {city}.\n\n{weather_info}")
    return ConversationHandler.END

async def auto_update_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    while user_settings[user_id]["auto_update"]:
        city = user_settings[user_id]["city"]
        weather_info = get_weather(city)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"⏰ Автообновление:\n\n{weather_info}")
        await asyncio.sleep(3600)

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = user_settings.get(user_id)
    if user and user["task"]:
        user["task"].cancel()
    user_settings[user_id] = {"auto_update": False, "task": None}
    await update.message.reply_text("🛑 Бот остановлен. Напиши /start, чтобы начать снова.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons)],
        states={WAITING_FOR_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_city)]},
        fallbacks=[]
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(conv_handler)
    print("✅ Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()