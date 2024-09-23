import os
import sys
import asyncio
import logging
import aioconsole
from pyrogram import Client, connection, storage
from pyrogram.session import internals
from pyrogram.errors import UsernameInvalid, exceptions
import aiohttp
from random import randint, choice

proxy_list = [
    {"hostname": "38.154.227.167", "port": 5868, "username": "lrazvxuf", "password": "71uopj8c2tox"},
    {"hostname": "45.127.248.127", "port": 5128, "username": "lrazvxuf", "password": "71uopj8c2tox"},
    {"hostname": "64.64.118.149", "port": 6732, "username": "lrazvxuf", "password": "71uopj8c2tox"},
    {"hostname": "167.160.180.203", "port": 6754, "username": "lrazvxuf", "password": "71uopj8c2tox"},
    {"hostname": "166.88.58.10", "port": 5735, "username": "lrazvxuf", "password": "71uopj8c2tox"},
    {"hostname": "173.0.9.70", "port": 5653, "username": "lrazvxuf", "password": "71uopj8c2tox"},
    {"hostname": "204.44.69.89", "port": 6342, "username": "lrazvxuf", "password": "71uopj8c2tox"},
    {"hostname": "173.0.9.209", "port": 5792, "username": "lrazvxuf", "password": "71uopj8c2tox"},
    {"hostname": "206.41.172.74", "port": 6634, "username": "lrazvxuf", "password": "71uopj8c2tox"}
]

class UsernameChecker(Client):
    def __init__(self, sessionid, api_id, api_hash, phone_number, username, *args, **kwargs):
        super().__init__(name=sessionid, api_id=api_id, api_hash=api_hash, phone_number=phone_number, workdir='sessions', *args, **kwargs)
        self.id = sessionid
        self.username = username
        self.is_paused = False
        self.attempts = 1
        self.console_task = None
        self.media = False
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s: %(message)s',
            datefmt='%d-%m-%Y %H:%M:%S',
            handlers=[
                logging.FileHandler(f"logs/{self.username}.log"),
                logging.StreamHandler()
            ]
        )

        self.logger = logging.getLogger(sessionid)

    async def start(self):
        await super().start()
        self.logger.info(f"{self.id} запущен")            

        # Запуск проверки имени пользователя
        self.console_task = asyncio.create_task(self.run_console())
        await self.check_username()

    async def check_username(self):
        while True:
            if self.is_paused:
                await asyncio.sleep(1)
                continue
                
            try:
                chat = await self.get_chat(self.username)

                if chat.username == self.username:
                    self.logger.info(f"{self.id}: Ник {self.username} нельзя сменить")
                else:
                    self.logger.info(chat)
                    raise exceptions.bad_request_400.UsernameNotOccupied("Username is not occupied")

            except (UsernameInvalid, exceptions.bad_request_400.UsernameNotOccupied):
                self.logger.info(f"{self.id}: Не удалось найти пользователя {self.username}")
                self.logger.info(f"{self.id}: Меняю ник")

                try:
                    await self.set_username(self.username)
                    await self.send_message_async('5189072355', f"<i>{self.id}: Ник {self.username} подменен</i>")
                    self.is_paused = True
            
                except exceptions.flood_420.FloodWait as e:
                    self.logger.warning(f"Ошибка {self.id}: Конец блокировки: {e.value + 5} сек. Пытаюсь сменить прокси.")
                    await asyncio.sleep(e.value + 5)

                except Exception as e:
                    self.logger.error(f'Ошибка {self.id}: {e}')
                    
                    # if self.attempts < 1:
                        # await self.send_message_async('5189072355', f"<i>{self.id}: Бот приостановлен для избежания блокировки</i>")                

                    if self.attempts < 5:
                        self.attempts = self.attempts + 1

                    await asyncio.sleep(randint(70, 100) * self.attempts)

            except Exception as e:
                self.logger.error(f"{self.id}: Ошибка - {e}")

            await asyncio.sleep(5)

    async def send_message_async(self, chat_id, message_text):
        API_URL = f'https://api.telegram.org/bot7422880413:AAFKP5z59eesD3HKsA2CC6wDSqDkdJJvK08/sendMessage'

        params = {
            'chat_id': chat_id,
            'text': message_text,
            'parse_mode': 'HTML'
        }

        # Асинхронное выполнение запроса
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, json=params) as response:
                if response.status == 200:
                    self.logger.info(f"Сообщение успешно отправлено пользователю {chat_id}")
                else:
                    self.logger.error(f"Ошибка отправки сообщения пользователю {chat_id}: {response.status} - {await response.text()}")



    async def run_console(self):
        """Асинхронная консоль для управления ботом."""
        while True:
            command = await aioconsole.ainput(f"[{self.id}] Введите команду: \n")
            if command.lower() == "pause":
                self.is_paused = True
                self.logger.info(f"{self.id}: Проверка приостановлена")
            elif command.lower() == "resume":
                self.is_paused = False
                self.logger.info(f"{self.id}: Проверка возобновлена")
            elif command.lower() == "restart":
                await self.restart()
                self.logger.info(f"{self.id}: Перезагрузка")
            elif command.lower() == "status":
                status = "приостановлена" if self.is_paused else "активна"
                self.logger.info(f"{self.id}: Проверка {status}")
            elif command.lower() == "stop":
                self.logger.info(f"{self.id}: Завершение работы")
                await self.stop()
            elif command.lower() == "start":
                self.logger.info(f"{self.id}: Запуск")
                await self.start()                                
            else:
                self.logger.warning(f"Неизвестная команда: {command}\n")

async def main():
    sessionid = sys.argv[1]
    api_id = int(sys.argv[2])
    api_hash = sys.argv[3]
    phone_number = sys.argv[4]
    username = sys.argv[5]
    password = sys.argv[6]

    client = UsernameChecker(
        sessionid=sessionid,
        api_id=api_id,
        api_hash=api_hash,
        phone_number=phone_number,
        username=username,
        password=password,        
    )
    
    await client.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Боты остановлены")


