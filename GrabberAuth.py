from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, CallbackContext
import requests

# Замените на свой токен
TOKEN = '7427495689:AAGm1PsIAtEyjcqCPLiAHN879AYYbKGyUcg'
API_URL = 'http://localhost:5000'  # URL вашего Flask API

main_keyboard = [
    [InlineKeyboardButton("Активные боты", callback_data='list_bots')],
    [InlineKeyboardButton("Добавить нового бота", callback_data='add_bot')]
] 

main_reply_markup = InlineKeyboardMarkup(main_keyboard)

async def start(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [InlineKeyboardButton("Активные боты", callback_data='list_bots')],
        [InlineKeyboardButton("Добавить нового бота", callback_data='add_bot')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if not (update.callback_query):
        await update.message.reply_text('Выберите действие:', reply_markup=reply_markup)
    else:
        await update.callback_query.message.edit_text('Выберите действие:', reply_markup=reply_markup)
        await update.callback_query.answer()

whitelist = ["Node", "Flask", "Grabber"]

async def list_bots(update: Update, context: CallbackContext) -> None:
    response = requests.get(f'{API_URL}/list_bots')
    if response.status_code == 200:
        data = response.json()
        screens = data['screens']

        keyboard = []

        for line in screens.splitlines():
            if not any(word in line for word in whitelist):
                continue

            if line.startswith('\t'):
                start_index = line.index('.') + 1
                end_index = line.index('(', start_index)

                sessionid = line[start_index:end_index].strip()
                keyboard.append([InlineKeyboardButton(sessionid, callback_data=f'manage_bot_{sessionid}')])

        keyboard.append([InlineKeyboardButton("Назад", callback_data='start')])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.callback_query.message.edit_text('Выберите бота для управления:', reply_markup=reply_markup)
    else:
        await update.callback_query.message.edit_text('Ошибка получения списка ботов.')

async def manage_bot(update: Update, context: CallbackContext) -> None:
    sessionid = update.callback_query.data.split('_')[2]

    keyboard = [
        [InlineKeyboardButton("Остановить", callback_data=f'stop_bot_{sessionid}')],
        [InlineKeyboardButton("Назад", callback_data='list_bots')]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.edit_text(f'Вы управляете ботом {sessionid}. Выберите действие:', reply_markup=reply_markup)

async def stop_bot(update: Update, context: CallbackContext) -> None:
    sessionid = update.callback_query.data.split('_')[2]
    response = requests.post(f'{API_URL}/stop_bot/{sessionid}')
    if (response.status_code == 200):
        keyboard = [
            [InlineKeyboardButton("Удалить", callback_data=f'delete_bot_{sessionid}')],
            [InlineKeyboardButton("Назад", callback_data='list_bots')]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.message.edit_text(f'Бот {sessionid} остановлен. Выберите действие:', reply_markup=reply_markup)
    else:
        await update.callback_query.message.edit_text(f'Ошибка остановки бота {sessionid}.')

async def start_bot(update: Update, context: CallbackContext) -> None:
    sessionid = update.callback_query.data.split('_')[2]
    context.user_data['start_bot_sessionid'] = sessionid
    await update.callback_query.message.reply_text(f'Введите параметры для запуска бота {sessionid} \nИМЯ\nPHONE\nUSERNAME\nPASSOWRD:')

async def add_bot(update: Update, context: CallbackContext) -> None:
    context.user_data['add_bot'] = True
    await update.callback_query.message.reply_text('Введите параметры для нового бота \nИМЯ\nPHONE\nUSERNAME\nPASSOWRD:')

async def delete_bot(update: Update, context: CallbackContext) -> None:
    sessionid = update.callback_query.data.split('_')[2]
    
    response = requests.post(f'{API_URL}/delete', json={
        'sessionid': sessionid,        
    })
    
    if (response.status_code == 200):
        await update.callback_query.message.edit_text(f'Бот {sessionid} удален.', reply_markup=main_reply_markup)
    else:
        await update.callback_query.message.edit_text(f"Ошибка при удалении {sessionid}.", reply_markup=main_reply_markup)

async def handle_message(update: Update, context: CallbackContext) -> None:
    if 'add_bot' in context.user_data:
        params = update.message.text.split("\n")

        if len(params) >= 4:
            # sessionid = f'{update.message.from_user.id}'

            response = requests.post(f'{API_URL}/start_bot', json={
                'sessionid': params[0],
                'api_id': 20576074,
                'api_hash': 'cbaa8377df5a3fa7f538fd869f02a51b',
                'phone_number': params[1],
                'username': params[2],
                'password': params[3]
            })
            
            if (response.status_code == 200):
                await update.message.reply_text(f'Бот {params[0]} запущен.', reply_markup=main_reply_markup)
            elif response.json()['error'] == 'need_code':
                context.user_data['code_typing'] = params[0]
                await update.message.reply_text(f"{params[0]}: Введи код авторизации:")

            del context.user_data['add_bot']
        else:
            await update.message.reply_text('Неверное количество параметров. Введите \nИМЯ\nPHONE\nUSERNAME\nPASSOWRD')

    elif 'code_typing' in context.user_data:
        code = update.message.text
        
        response = requests.post(f'{API_URL}/send_code', json={
            'sessionid': context.user_data['code_typing'],
            'code': code
        })

        if response.status_code == 200:
            await update.message.reply_text(f"{context.user_data['code_typing']}: Успешная авторизация", reply_markup=main_reply_markup)            
        else:
            await update.message.reply_text(f"{context.user_data['code_typing']}: Ошибка при авторизации", reply_markup=main_reply_markup)

        del context.user_data['code_typing']

    elif 'start_bot_sessionid' in context.user_data:
        # Обработка ввода параметров для запуска бота
        params = update.message.text.split("\n")

        if len(params) >= 3:
            response = requests.post(f'{API_URL}/start_bot', json={
                'sessionid': context.user_data['start_bot_sessionid'],
                'api_id': 20576074,
                'api_hash': 'cbaa8377df5a3fa7f538fd869f02a51b',
                'phone_number': params[0] if len(params) > 1 else "",
                'username': params[1] if len(params) > 1 else "",
                'password': params[2] if len(params) > 1 else "",
            })

            if (response.status_code == 200):
                await update.message.reply_text(f'Бот {context.user_data["start_bot_sessionid"]} запущен.', reply_markup=main_reply_markup)
            else:
                await update.message.reply_text('Ошибка запуска бота.', reply_markup=main_reply_markup)
            del context.user_data['start_bot_sessionid']
        else:
            await update.message.reply_text('Неверное количество параметров. Введите api_id, api_hash, phone_number и username через пробел.')

    else:
        await update.message.reply_text('Сначала используйте команды /start или /add_bot.')

def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(start, pattern='^start$'))
    application.add_handler(CallbackQueryHandler(list_bots, pattern='^list_bots$'))
    application.add_handler(CallbackQueryHandler(add_bot, pattern='^add_bot$'))
    application.add_handler(CallbackQueryHandler(delete_bot, pattern='^delete_bot_'))
    application.add_handler(CallbackQueryHandler(manage_bot, pattern='^manage_bot_'))
    application.add_handler(CallbackQueryHandler(stop_bot, pattern='^stop_bot_'))
    application.add_handler(CallbackQueryHandler(start_bot, pattern='^start_bot_'))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()

if __name__ == '__main__':
    main()
