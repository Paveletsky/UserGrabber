from flask import Flask, request, jsonify
import subprocess
import os
import logging

app = Flask(__name__)

os.makedirs('logs', exist_ok=True)

# Настройка логирования
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

    # Путь к вашему Python-скрипту
    bot_script = os.path.abspath('StartBots.py')
    session_file = f"sessions/{sessionid}.session"

    if not os.path.exists(session_file):
        need_code = True
    else:
        need_code = False

    # Запуск нового screen сессии
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
        # Команда для отображения всех screen сессий
        command_list = "screen -ls"
        result_list = subprocess.run(command_list, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        screens = result_list.stdout.decode('utf-8')
        
        if screen_name not in screens:
            return jsonify({"error": f"Screen session {screen_name} не найдена"}), 404

        # Команда для остановки screen сессии
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
        # Команда для отображения всех screen сессий
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
    

if __name__ == "__main__":
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

    app.run(host='0.0.0.0', port=5000)
        