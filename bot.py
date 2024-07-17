import os
import openai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Инициализация бота
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

openai.api_key = OPENAI_API_KEY

# Определение этапов разговора
PHOTO, SKIN_TYPE_TEST, QUESTIONS, REGION, RESULTS = range(5)

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Привет! Пожалуйста, отправьте фото вашего лица, и мы начнем диагностику."
    )
    return PHOTO

# Обработчик фото
async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Фото получено! Давайте определим ваш тип кожи. Если вы не знаете свой тип кожи, выполните следующий тест:\n\n"
        "✔ Умыться теплой водой без очищающих средств. На лице не должно быть косметики, пыли и других загрязнений, которые нарушат чистоту эксперимента.\n\n"
        "✔ Промокнуть кожу насухо, не растирая.\n\n"
        "✔ Для чистоты эксперимента подождать 30–40 минут, пока выработается нормальное для кожи количество себума.\n\n"
        "✔ В это время можно заниматься своими делами. Главное — исключить физические упражнения, не готовить на плите или в духовке и не находиться на открытом солнце.\n\n"
        "✔ Оценить состояние кожи и распределение жирного блеска. Можно приложить чистую салфетку ко лбу, носу, подбородку и обеим щекам. Желательно, чтобы разных участков лица касались разные части салфетки.\n\n"
        "Пожалуйста, выберите один из следующих вариантов:\n"
        "1. Кожа блестит равномерно, появилось неприятное ощущение пленки? Салфетка прилипает ко всем участкам, и на ней остаются следы? (Жирная кожа)\n"
        "2. Кожа блестит в Т-зоне, салфетка прилипает только ко лбу и носу, и эти же участки оставляют следы? (Комбинированная кожа)\n"
        "3. Кожа матовая, не стягивается, салфетка вообще не прилипает к лицу и остается абсолютно чистой? (Нормальная кожа)\n"
        "4. Салфетка не прилипает к лицу и остается чистой, а кожа зудит и стягивается? (Сухая кожа)"
    )
    return SKIN_TYPE_TEST

# Обработчик теста для определения типа кожи
async def skin_type_test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.lower()
    if "1" in text:
        skin_type = "Жирная кожа"
    elif "2" in text:
        skin_type = "Комбинированная кожа"
    elif "3" in text:
        skin_type = "Нормальная кожа"
    elif "4" in text:
        skin_type = "Сухая кожа"
    else:
        await update.message.reply_text(
            "Пожалуйста, выберите один из предложенных вариантов: 1, 2, 3 или 4."
        )
        return SKIN_TYPE_TEST
    
    context.user_data['skin_type'] = skin_type
    await update.message.reply_text(f"Ваш тип кожи: {skin_type}. Теперь ответьте на несколько вопросов о вашем здоровье и образе жизни.")
    await update.message.reply_text("Есть ли у вас чувствительность к каким-либо ингредиентам или аллергии? (да/нет, если да, укажите какие)")
    return QUESTIONS

# Обработчик вопросов
async def questions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['sensitivity'] = update.message.text
    await update.message.reply_text("Какой у вас питьевой режим? (например, пью 2 литра воды в день, редко пью воду)")
    return QUESTIONS + 1

async def water_intake(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['water_intake'] = update.message.text
    await update.message.reply_text("Какой у вас рацион? (например, сбалансированный, много сладкого, вегетарианский и т.д.)")
    return QUESTIONS + 2

async def diet_questions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['diet'] = update.message.text
    await update.message.reply_text("Есть ли у вас гормональные изменения или проблемы? (например, беременность, подростковый возраст, менопауза)")
    return QUESTIONS + 3

async def hormones_questions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['hormones'] = update.message.text
    await update.message.reply_text("Сколько времени вы проводите на улице каждый день? (например, менее часа, 1-3 часа, более 3 часов)")
    return QUESTIONS + 4

async def outdoor_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['outdoor_time'] = update.message.text
    await update.message.reply_text("Какой у вас уровень физической активности? (например, занимаюсь спортом 3 раза в неделю, малоактивный образ жизни)")
    return QUESTIONS + 5

async def physical_activity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['physical_activity'] = update.message.text
    await update.message.reply_text("Какие у вас условия работы? (например, работа в офисе, работа на улице)")
    return QUESTIONS + 6

async def work_conditions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['work_conditions'] = update.message.text
    await update.message.reply_text("Какой у вас уровень стресса и сколько вы спите каждую ночь? (например, высокий уровень стресса, сплю 7-8 часов)")
    return QUESTIONS + 7

async def stress_sleep(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['stress_sleep'] = update.message.text
    await update.message.reply_text("Как ваша кожа реагирует на сезонные изменения? (например, сухая зимой, жирная летом)")
    return QUESTIONS + 8

async def seasonal_changes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['seasonal_changes'] = update.message.text
    await update.message.reply_text("Сколько вам лет и есть ли у вас гормональные изменения? (например, мне 25, нет изменений)")
    return QUESTIONS + 9

async def age_hormones(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['age_hormones'] = update.message.text
    await update.message.reply_text("В каком регионе вы находитесь? (например, Москва, Россия)")
    return REGION

# Обработчик завершения
async def region(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['region'] = update.message.text
    user_data = context.user_data

    # Формирование запроса к OpenAI
    prompt = f"""
    Пользователь прислал фото лица и ответил на несколько вопросов.
    Тип кожи: {user_data['skin_type']}
    Чувствительность к ингредиентам: {user_data['sensitivity']}
    Питьевой режим: {user_data['water_intake']}
    Рацион: {user_data['diet']}
    Гормональные изменения: {user_data['hormones']}
    Время на улице: {user_data['outdoor_time']}
    Уровень физической активности: {user_data['physical_activity']}
    Условия работы: {user_data['work_conditions']}
    Уровень стресса и сон: {user_data['stress_sleep']}
    Сезонные изменения: {user_data['seasonal_changes']}
    Возраст и гормональные изменения: {user_data['age_hormones']}
    Регион: {user_data['region']}
    Дайте рекомендации по домашнему уходу за кожей, включающие очищение, тонизирование, увлажнение, защиту от солнца и эксфолиацию.
    Включите в каждую категорию 3 различных наименования средств, доступных в регионе пользователя.
    """
    response = openai.Completion.create(
        engine="davinci",
        prompt=prompt,
        max_tokens=300
    )

    recommendations = response.choices[0].text.strip()
    await update.message.reply_text(f'Спасибо за ответы. Вот ваши рекомендации по уходу за кожей:\n{recommendations}')
    return ConversationHandler.END

# Основная функция
def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            PHOTO: [MessageHandler(filters.PHOTO, photo)],
            SKIN_TYPE_TEST: [MessageHandler(filters.TEXT & ~filters.COMMAND, skin_type_test)],
            QUESTIONS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, questions),
                MessageHandler(filters.TEXT & ~filters.COMMAND, water_intake),
                MessageHandler(filters.TEXT & ~filters.COMMAND, diet_questions),
                MessageHandler(filters.TEXT & ~filters.COMMAND, hormones_questions),
                MessageHandler(filters.TEXT & ~filters.COMMAND, outdoor_time),
                MessageHandler(filters.TEXT & ~filters.COMMAND, physical_activity),
                MessageHandler(filters.TEXT & ~filters.COMMAND, work_conditions),
                MessageHandler(filters.TEXT & ~filters.COMMAND, stress_sleep),
                MessageHandler(filters.TEXT & ~filters.COMMAND, seasonal_changes),
                MessageHandler(filters.TEXT & ~filters.COMMAND, age_hormones)
            ],
            REGION: [MessageHandler(filters.TEXT & ~filters.COMMAND, region)],
            RESULTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, region)]
        },
        fallbacks=[]
    )

    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == '__main__':
    main()