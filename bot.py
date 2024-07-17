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

# Обработчик фото
async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Здесь должна быть проверка качества фото
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
        "Есть ли у вас чувствительность к каким-либо ингредиентам или аллергии? (да/нет, если да, укажите какие)",
        "Какой у вас питьевой режим? (например, пью 2 литра воды в день, редко пью воду)",
        "Какой у вас рацион? (например, сбалансированный, много сладкого, вегетарианский и т.д.)",
        "Есть ли у вас гормональные изменения или проблемы? (например, беременность, подростковый возраст, менопауза)",
        "Сколько времени вы проводите на улице каждый день? (например, менее часа, 1-3 часа, более 3 часов)",
        "Какой у вас уровень физической активности? (например, занимаюсь спортом 3 раза в неделю, малоактивный образ жизни)",
        "Какие у вас условия работы? (например, работа в офисе, работа на улице)",
        "Какой у вас уровень стресса и сколько вы спите каждую ночь? (например, высокий уровень стресса, сплю 7-8 часов)",
        "Как ваша кожа реагирует на сезонные изменения? (например, сухая зимой, жирная летом)",
        "Вы зарегистрированы у дерматолога? Если да, то с каким диагнозом и какое лечение назначено?",
        "Принимаете ли вы какие-либо лекарства/добавки? Если да, то какие?",
        "Сколько вам лет и есть ли у вас гормональные изменения? (например, мне 25, нет изменений)",
        "В каком городе вы живете?"
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
    context.user_data[f'answer_{context.user_data["current_question"]}'] = update.message.text
    return await ask_next_question(update, context)

# Функция для предоставления рекомендаций
async def provide_recommendations(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data = context.user_data

    # Формирование запроса к OpenAI
    prompt = f"""
    Пользователь прислал фото лица и ответил на несколько вопросов.
    Тип кожи: {user_data['skin_type']}
    Чувствительность: {user_data.get('answer_1')}
    Питьевой режим: {user_data.get('answer_2')}
    Рацион: {user_data.get('answer_3')}
    Гормональные изменения: {user_data.get('answer_4')}
    Время на улице: {user_data.get('answer_5')}
    Уровень физической активности: {user_data.get('answer_6')}
    Условия работы: {user_data.get('answer_7')}
    Уровень стресса и сон: {user_data.get('answer_8')}
    Сезонные изменения: {user_data.get('answer_9')}
    Диагноз дерматолога: {user_data.get('answer_10')}
    Лекарства/добавки: {user_data.get('answer_11')}
    Возраст и гормональные изменения: {user_data.get('answer_12')}
    Город: {user_data.get('answer_13')}
    Дай рекомендации по уходу, включая очищение, тонизирование, увлажнение, защиту от солнца и эксфолиацию. Выбери 3 различных наименования средств в каждой категории, доступных в регионе запроса. Учтите время года и погоду в вашем регионе.
    """

    response = openai.Completion.create(
        engine="davinci",
        prompt=prompt,
        max_tokens=300
    )

    recommendations = response.choices[0].text.strip()
    await update.message.reply_text(
        "Базовые правила ухода за кожей:\n"
        "• Результат ухода проявляется со временем. Используйте средства регулярно.\n"
        "• Подбирайте уход в зависимости от сезона и климата.\n"
        "• Всегда смывайте макияж перед сном.\n"
        "• Очищайте и ухаживайте за шеей и зоной декольте.\n"
        "• Защищайте кожу от солнца круглый год.\n"
        "• Пейте достаточно воды для поддержания здоровья кожи.\n"
        "• Меняйте постельное белье и используйте бумажные полотенца."
    )
    await update.message.reply_text(f'Спасибо за ответы. Вот ваши рекомендации по уходу за кожей:\n{recommendations}')
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