import asyncio
from flask import Flask, request, jsonify
import subprocess
import os
import logging

app = Flask(__name__)

os.makedirs('logs', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s',
    datefmt='%d-%m-%Y %H:%M:%S',
    handlers=[
        logging.FileHandler("logs/Flask.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

@app.route('/start_bot', methods=['POST'])
def start_bot():
    data = request.json
    sessionid = data.get('sessionid')
    api_id = data.get('api_id')
    api_hash = data.get('api_hash')
    phone_number = data.get('phone_number')
    password = data.get('password')
    username = data.get('username')

    if not (sessionid and api_id and api_hash and phone_number and username):
        return jsonify({"error": "Все параметры обязательны"}), 400

    bot_script = os.path.abspath('StartBots.py')
    session_file = f"sessions/{sessionid}.session"

    if not os.path.exists(session_file):
        need_code = True
    else:
        need_code = False

    screen_name = f"{sessionid}"
    command = f"screen -dmS {screen_name} python3 {bot_script} \"{sessionid}\" {api_id} \"{api_hash}\" \"{phone_number}\" \"{username}\" \"{password}\""

    try:
        subprocess.run(command, shell=True, check=True)
        logger.info(f"Запущен бот {sessionid} в screen сессии {screen_name}")

        if need_code:
            return jsonify({"error": f"need_code"}), 500            
        else:
            return jsonify({"message": f"Бот {sessionid} запущен в screen сессии {screen_name}"}), 200
    except subprocess.CalledProcessError as e:
        logger.error(f"Ошибка запуска бота {sessionid}: {str(e)}")
        return jsonify({"error": "Не удалось запустить бота"}), 500

@app.route('/stop_bot/<sessionid>', methods=['POST'])
def stop_bot(sessionid):
    screen_name = f"{sessionid}"

    try:
        command_list = "screen -ls"
        result_list = subprocess.run(command_list, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        screens = result_list.stdout.decode('utf-8')
        
        if screen_name not in screens:
            return jsonify({"error": f"Screen session {screen_name} не найдена"}), 404

        command = f"screen -S {screen_name} -X quit"
        subprocess.run(command, shell=True, check=True)
        logger.info(f"Бот {sessionid} остановлен и screen сессия {screen_name} завершена")
        return jsonify({"message": f"Бот {sessionid} остановлен и screen сессия {screen_name} завершена"}), 200

    except subprocess.CalledProcessError as e:
        logger.error(f"Ошибка остановки бота {sessionid}: {str(e)}")
        return jsonify({"error": "Не удалось остановить бота"}), 500

@app.route('/list_bots', methods=['GET'])
def list_bots():
    try:
        command = "screen -ls"
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        screens = result.stdout.decode('utf-8')

        logger.info("Запущенные screen сессии:\n" + screens)
        return jsonify({"screens": screens}), 200
    except subprocess.CalledProcessError as e:
        logger.error(f"Ошибка получения списка ботов: {str(e)}")
        return jsonify({"error": "Не удалось получить список ботов"}), 500
    
@app.route('/send_code', methods=['POST'])
def send_code():
    data = request.json
    sessionid = data.get('sessionid')
    code = data.get('code')

    if not (sessionid and code):
        return jsonify({"error": "sessionid и code обязательны"}), 400
    
    sanitized_code = code.replace("-", "")
    screen_name = f"{sessionid}"
    command = f"screen -S {screen_name} -p 0 -X stuff \"{sanitized_code}\\n\""

    try:
        subprocess.run(command, shell=True, check=True)
        logger.info(f"Код {code} отправлен в screen сессию {screen_name}")
        return jsonify({"message": f"Код {code} отправлен в screen сессию {screen_name}"}), 200
    except subprocess.CalledProcessError as e:
        logger.error(f"Ошибка отправки кода {code} в screen сессию {screen_name}: {str(e)}")
        return jsonify({"error": "Не удалось отправить код"}), 500
    
@app.route('/delete', methods=['POST'])
def delete():
    data = request.json
    sessionid = data.get('sessionid')

    try:
        session_file = f"sessions/{sessionid}.session"
        if os.path.exists(session_file):
            os.remove(session_file)
            os.remove(f"logs/{sessionid}.log")

        logger.info(f"Сессия {sessionid} удалена")
        return jsonify({"message": f"Сессия {sessionid} удалена"}), 200
    except subprocess.CalledProcessError as e:
        logger.error(f"Ошибка: {str(e)}")
        return jsonify({"error": "Ошибка удаления"}), 500
    
@app.route('/delete_all', methods=['POST'])
def delete_all():
    try:
        session_folder = "sessions"
        log_folder = "logs"

        if os.path.exists(session_folder):
            for file_name in os.listdir(session_folder):
                file_path = os.path.join(session_folder, file_name)
                if os.path.isfile(file_path):
                    os.remove(file_path)

        if os.path.exists(log_folder):
            for file_name in os.listdir(log_folder):
                file_path = os.path.join(log_folder, file_name)
                if os.path.isfile(file_path):
                    os.remove(file_path)

        logger.info("Все сессии и связанные логи удалены")
        return jsonify({"message": "Все сессии и связанные логи удалены"}), 200
    except Exception as e:
        logger.error(f"Ошибка при удалении всех файлов: {str(e)}")
        return jsonify({"error": "Ошибка удаления всех файлов"}), 500


import aiomysql

DB_CONFIG = {
    "host": "db",
    "port": 3306,
    "user": "user",
    "password": "root",
    "db": "grabber"
}

async def init_db():
    create_table_query = """
    CREATE TABLE IF NOT EXISTS bots (
        sessionid VARCHAR(255) NOT NULL,
        phone_number VARCHAR(20) NOT NULL,
        username VARCHAR(255),
        password VARCHAR(255),
        PRIMARY KEY (sessionid)
    );
    """
    conn = None  # <-- Добавили, чтобы переменная была объявлена всегда
    try:
        conn = await aiomysql.connect(**DB_CONFIG)
        async with conn.cursor() as cursor:
            await cursor.execute(create_table_query)
            await conn.commit()
        print("Table 'bots' checked/created successfully")
    except Exception as e:
        print(f"Error while creating table: {e}")
    # finally:
    #     if conn:  # <-- Проверяем, определён ли conn
    #         conn.close()

async def fetch_bots():
    """Получаем данные о ботах из базы."""
    query = "SELECT sessionid, phone_number, username, password FROM bots"
    conn = None
    try:
        conn = await aiomysql.connect(**DB_CONFIG)
        async with conn.cursor() as cursor:
            await cursor.execute(query)
            return await cursor.fetchall()
    except Exception as e:
        print(f"Ошибка при получении данных из базы: {e}")
        return []
    finally:
        if conn:
            conn.close()

async def add_bot(sessionid: str, phone_number: str, username: str, password: str):
    """Добавляем нового бота в базу данных."""
    insert_query = """
    INSERT INTO bots (sessionid, phone_number, username, password)
    VALUES (%s, %s, %s, %s)
    """
    conn = None
    try:
        conn = await aiomysql.connect(**DB_CONFIG)
        async with conn.cursor() as cursor:
            await cursor.execute(insert_query, (sessionid, phone_number, username, password))
            await conn.commit()
        print(f"Бот {sessionid} успешно добавлен в базу")
    except Exception as e:
        print(f"Ошибка при добавлении бота: {e}")
    finally:
        if conn:
            conn.close()

def start_bots():
    """Запускаем ботов из базы данных."""
    bot_script = os.path.abspath('StartBots.py')

    bots = asyncio.run(fetch_bots())

    if not bots:
        print("Боты не найдены в базе.")
        return

    for bot in bots:
        sessionid, phone_number, username, password = bot
        api_id = "20576074"
        api_hash = "cbaa8377df5a3fa7f538fd869f02a51b"

        screen_name = f"{sessionid}"
        command = (
            f"screen -dmS {screen_name} python3 {bot_script} "
            f"\"{sessionid}\" {api_id} \"{api_hash}\" \"{phone_number}\" \"{username}\" \"{password}\""
        )

        try:
            subprocess.run(command, shell=True, check=True)
            print(f"Запущен бот {sessionid} в screen сессии {screen_name}")
        except subprocess.CalledProcessError as e:
            print(f"Ошибка запуска бота {sessionid}: {e}")

if __name__ == "__main__":
    asyncio.run(init_db())

    wd = os.path.abspath('console')

    command = f"screen -dmS GrabberBot python3 GrabberAuth.py"
    start_node = f'screen -dmS NodeConsole bash -c "cd console; node server.js"'

    stopcommand = f"screen -S GrabberBot -X quit"
    stop_node = f"screen -S NodeConsole -X quit"

    try:
        subprocess.run(stopcommand, shell=True, check=True)
        subprocess.run(stop_node, shell=True, check=True)
    except Exception as e:
        print('Нельзя запустить')

    subprocess.run(command, shell=True, check=True)
    logger.info(f"Запущен GrabberBot")

    subprocess.run(start_node, shell=True, check=True)
    logger.info(f"Запущен NodeJS")

    start_bots()

    app.run(host='0.0.0.0', port=5000)
        