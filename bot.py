import os
import openai
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackContext, JobQueue
import datetime

# Инициализация бота
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

if not TELEGRAM_TOKEN:
    raise ValueError("No TELEGRAM_TOKEN provided")
if not OPENAI_API_KEY:
    raise ValueError("No OPENAI_API_KEY provided")

openai.api_key = OPENAI_API_KEY

# Определение этапов разговора
PHOTO, SKIN_TYPE, TEST, QUESTIONS, RESULTS, TRACK_PROGRESS, SET_REMINDER, REMINDER_TIME = range(8)

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Привет! Я AI бот, созданный для предоставления общих советов по уходу за кожей на основе ваших ответов и данных AI. "
        "Помните, что мои рекомендации не являются персонализированными и не заменяют консультацию с профессиональным дерматологом. "
        "Для начала отправьте фото вашего лица."
    )
    return PHOTO

# Обработчик фото
async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    photo_file = await update.message.photo[-1].get_file()
    photo_path = f'/tmp/{photo_file.file_id}.jpg'

    # Загрузка файла
    await photo_file.download_to_drive(photo_path)

    # Проверка качества фотографии через OpenAI
    with open(photo_path, "rb") as image_file:
        response = openai.Image.create_variation(
            image=image_file,
            n=1,
            size="1024x1024"
        )

    description = response['data'][0]['url']

    if "лицо" not in description or "плохо видно" in description:
        await update.message.reply_text("Фото не подходит. Пожалуйста, сделайте новое фото, убедитесь, что ваше лицо хорошо видно и освещено.")
        return PHOTO

    await update.message.reply_text("Фото получено! Давайте определим ваш тип кожи.")
    keyboard = [
        [KeyboardButton("Жирная кожа"), KeyboardButton("Комбинированная кожа")],
        [KeyboardButton("Нормальная кожа"), KeyboardButton("Сухая кожа")],
        [KeyboardButton("Я не знаю")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text("Выберите ваш тип кожи:", reply_markup=reply_markup)
    return SKIN_TYPE

# Обработчик выбора типа кожи
async def skin_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text == "Я не знаю":
        await update.message.reply_text(
            "Пройдите тест:\n"
            "1. Умыться теплой водой без очищающих средств.\n"
            "2. Промокнуть кожу насухо, не растирая.\n"
            "3. Подождать 30–40 минут.\n"
            "4. Оценить состояние кожи и распределение жирного блеска.\n"
            "Выберите один из следующих вариантов:\n"
            "1. Кожа блестит равномерно (Жирная кожа)\n"
            "2. Кожа блестит в Т-зоне (Комбинированная кожа)\n"
            "3. Кожа матовая (Нормальная кожа)\n"
            "4. Кожа стягивается (Сухая кожа)"
        )
        return TEST
    else:
        context.user_data['skin_type'] = text
        return await ask_next_question(update, context)

# Обработчик теста
async def test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    skin_types = {
        "1": "Жирная кожа",
        "2": "Комбинированная кожа",
        "3": "Нормальная кожа",
        "4": "Сухая кожа"
    }
    if text in skin_types:
        context.user_data['skin_type'] = skin_types[text]
        return await ask_next_question(update, context)
    else:
        await update.message.reply_text("Пожалуйста, выберите один из предложенных вариантов: 1, 2, 3 или 4.")
        return TEST

# Функция для задания следующего вопроса
async def ask_next_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    questions = [
        "Есть ли у вас чувствительность к каким-либо ингредиентам или аллергии? Какой у вас питьевой режим? (да/нет, если да, укажите какие; например, пью 2 литра воды в день, редко пью воду)",
        "Какой у вас рацион? (например, сбалансированный, много сладкого, вегетарианский и т.д.)",
        "Есть ли у вас гормональные изменения или проблемы? (например, беременность, подростковый возраст, менопауза)",
        "Сколько вам лет и в каком городе вы живете?"
    ]

    current_question = context.user_data.get('current_question', 0)
    if current_question < len(questions):
        await update.message.reply_text(questions[current_question])
        context.user_data['current_question'] = current_question + 1
        return QUESTIONS
    else:
        return await provide_recommendations(update, context)

# Обработчик ответов на вопросы
async def questions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    current_question = context.user_data.get('current_question', 0)
    context.user_data[f'answer_{current_question - 1}'] = update.message.text
    return await ask_next_question(update, context)

# Функция для предоставления рекомендаций
async def provide_recommendations(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data = context.user_data

    # Формирование запроса к OpenAI
    prompt = f"""
    Пользователь прислал фото лица и ответил на несколько вопросов.
    Тип кожи: {user_data['skin_type']}
    Чувствительность и питьевой режим: {user_data.get('answer_0')}
    Рацион: {user_data.get('answer_1')}
    Гормональные изменения: {user_data.get('answer_2')}
    Возраст и город: {user_data.get('answer_3')}
    Дай рекомендации по уходу, включая очищение, тонизирование, увлажнение, защиту от солнца и эксфолиацию. Выбери 3 различных наименования средств в каждой категории, доступных в регионе запроса. Учтите время года и погоду в вашем регионе.
    """

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    )

    recommendations = response['choices'][0]['message']['content'].strip()

    await update.message.reply_text(
        "Базовые правила ухода за кожей:\n"
        "• Терпение и регулярность: Результат ухода проявляется со временем. Используйте средства регулярно.\n"
        "• Сезонная косметика: Подбирайте уход в зависимости от сезона и климата.\n"
        "• Удаление макияжа: Всегда смывайте макияж перед сном.\n"
        "• Забота о шее и декольте: Очищайте и ухаживайте за шеей и зоной декольте.\n"
        "• Использование SPF: Защищайте кожу от солнца круглый год.\n"
        "• Гидратация: Пейте достаточно воды для поддержания здоровья кожи.\n"
        "• Чистота: Меняйте постельное белье и используйте бумажные полотенца."
    )

    await update.message.reply_text(
        f'Спасибо за ответы. Вот ваши рекомендации по уходу за кожей:\n{recommendations}'
    )

    keyboard = [
        [KeyboardButton("Да"), KeyboardButton("Нет")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text("Хотите ли вы начать следить за прогрессом состояния кожи?", reply_markup=reply_markup)
    return TRACK_PROGRESS

# Обработчик выбора отслеживания прогресса
async def track_progress(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text == "Да":
        await update.message.reply_text("Отлично! Давайте настроим уведомления. Введите время утра в формате HH:MM.")
        return SET_REMINDER
    else:
        await update.message.reply_text("Если вы передумаете, просто дайте знать. Спасибо!")
        return ConversationHandler.END

# Обработчик установки времени уведомлений
async def set_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    time = update.message.text
    try:
        hours, minutes = map(int, time.split(':'))
        context.user_data['morning_time'] = time
        await update.message.reply_text(f"Уведомление утром установлено на {time}. Теперь введите время вечера в формате HH:MM.")
        return REMINDER_TIME
    except ValueError:
        await update.message.reply_text("Неверный формат времени. Пожалуйста, введите время в формате HH:MM.")
        return SET_REMINDER

# Обработчик установки времени уведомлений вечером
async def reminder_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    time = update.message.text
    try:
        hours, minutes = map(int, time.split(':'))
        context.user_data['evening_time'] = time
        await update.message.reply_text(f"Уведомление вечером установлено на {time}. Спасибо! Мы будем отправлять вам напоминания утром и вечером.")
        
        # Настройка уведомлений
        job_queue = context.job_queue
        morning_time = context.user_data['morning_time']
        evening_time = context.user_data['evening_time']

        job_queue.run_daily(morning_notification, time=datetime.time(hour=int(morning_time.split(':')[0]), minute=int(morning_time.split(':')[1])), context=update.message.chat_id)
        job_queue.run_daily(evening_notification, time=datetime.time(hour=int(evening_time.split(':')[0]), minute=int(evening_time.split(':')[1])), context=update.message.chat_id)

        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Неверный формат времени. Пожалуйста, введите время в формате HH:MM.")
        return REMINDER_TIME

# Уведомление утром
async def morning_notification(context: CallbackContext) -> None:
    job = context.job
    await context.bot.send_message(job.context, text="Доброе утро! Не забудьте провести утренний ритуал ухода за кожей и отправить фото с датой.")

# Уведомление вечером
async def evening_notification(context: CallbackContext) -> None:
    job = context.job
    await context.bot.send_message(job.context, text="Добрый вечер! Не забудьте провести вечерний ритуал ухода за кожей и отправить фото с датой.")

# Основная функция
def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            PHOTO: [MessageHandler(filters.PHOTO, photo)],
            SKIN_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, skin_type)],
            TEST: [MessageHandler(filters.TEXT & ~filters.COMMAND, test)],
            QUESTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, questions)],
            TRACK_PROGRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, track_progress)],
            SET_REMINDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_reminder)],
            REMINDER_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, reminder_time)]
        },
        fallbacks=[]
    )

    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == '__main__':
    main()