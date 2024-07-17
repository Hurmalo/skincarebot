import os
import openai
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Инициализация бота
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

if not TELEGRAM_TOKEN:
    raise ValueError("No TELEGRAM_TOKEN provided")
if not OPENAI_API_KEY:
    raise ValueError("No OPENAI_API_KEY provided")

openai.api_key = OPENAI_API_KEY

# Определение этапов разговора
PHOTO, SKIN_TYPE, TEST, QUESTIONS, RESULTS = range(5)

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Привет! Я AI бот, созданный для предоставления общих советов по уходу за кожей на основе ваших ответов и данных AI. "
        "Помните, что мои рекомендации не являются персонализированными и не заменяют консультацию с профессиональным дерматологом. "
        "Для начала отправьте фото вашего лица."
    )
    return PHOTO

# Обработчик фото (с сохранением ссылки на фото)
async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    photo_file = await update.message.photo[-1].get_file()
    photo_path = f'/tmp/{photo_file.file_id}.jpg'
    await photo_file.download_to_drive(photo_path)

    # Сохранение пути к файлу в данных пользователя
    context.user_data['photo_url'] = photo_path

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
    Фото пользователя: {user_data['photo_url']}
    Основываясь на данных и фотографии, дай рекомендации в зависимости от ответов и рекомендацию по уходу за кожей, включая основной уход и дополнительный, также выбери 3 различных наименования средств в каждой категории, доступных в регионе пользователя. Учти время года и погоду в регионе.
    """

    try:
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
            "Результат ухода проявляется со временем. Используйте средства регулярно.\n"
            "Подбирайте уход в зависимости от сезона и климата.\n"
            "Всегда смывайте макияж перед сном.\n"
            "Очищайте и ухаживайте за шеей и зоной декольте.\n"
            "Защищайте кожу от солнца круглый год.\n"
            "Пейте достаточно воды для поддержания здоровья кожи.\n"
            "Меняйте постельное белье и используйте бумажные полотенца."
        )

        await update.message.reply_text(
            f'Спасибо за ответы. Вот ваши рекомендации по уходу за кожей:\n{recommendations}'
        )

    except openai.error.RateLimitError:
        await update.message.reply_text(
            "Извините, в данный момент я не могу обработать ваш запрос из-за превышения лимита. Пожалуйста, попробуйте позже."
        )

    return ConversationHandler.END

# Основная функция
def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            PHOTO: [MessageHandler(filters.PHOTO, photo)],
            SKIN_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, skin_type)],
            TEST: [MessageHandler(filters.TEXT & ~filters.COMMAND, test)],
            QUESTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, questions)]
        },
        fallbacks=[]
    )

    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == '__main__':
    main()