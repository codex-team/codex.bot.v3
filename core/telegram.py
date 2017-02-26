import base64
import random

import requests
import logging
from urllib.parse import urlencode
from components.simple import send_to_chat, register_commands, send_image_to_chat, send_object_to_chat
from configuration.globalcfg import TELEGRAM_WEBHOOK, OBJECTS
from core.web import telegram_callback


def send_message(params):
    try:
        cmd = params.get("cmd", "")
        if cmd == "send_message":
            send_to_chat(message=params.get("message", ""),
                         chat_id=params.get("chat_id", "")
                         )

        if cmd == "send_image":
            result = send_image_to_chat(caption=params.get("caption", ""),
                                        image_filename=params.get("image_filename", ""),
                                        chat_id=params.get("chat_id", "")
                                        )
            logging.warning(result.content)
        if cmd == "send_keyboard":
            send_object_to_chat(text=params.get("message", ""),
                                reply_markup=params.get("buttons", ""),
                                chat_id=params.get("chat_id", "")
                                )
    except Exception as e:
        logging.error("Send message Error: [{}]".format(e))


class Telegram:

    def __init__(self, api_token, web_app):
        """
        Инициализирует aiohttp APP и Telegram API Token
        :param api_token:
        :param web_app:
        """
        self.API_TOKEN = api_token
        self.WEB_APP = web_app

    def set_webhook(self):
        """
        Обновляет веб-хук для бота на текущий сервер
        :return:
        """
        query = 'https://api.telegram.org/bot%s/setWebhook?%s' % (self.API_TOKEN, urlencode({
            'url': TELEGRAM_WEBHOOK
        }))
        try:
            result = requests.get(query)
        except Exception as e:
            logging.debug(e)
        else:
            logging.debug(result.content)

    def set_routes(self):
        """
        Устанавливает роуты, которые будет обрабатывать модуль.
            - /telegram/callback - сообщения от Telegram.
        :return:
        """
        self.WEB_APP.router.add_post('/telegram/callback', telegram_callback)

    def register_commands(self, global_commands):
        """
        Описывает какие команды переадресовывать данному модулю.
            - help - справка.
            - start - приветствие.
        :param global_commands:
        :return:
        """
        register_commands('telegram', ['help', 'start'], global_commands)

    @staticmethod
    def make_answer(message):
        """
        Обрабатывает сообщения
        :param message:
        :return:
        """
        try:
            command_prefix = message['text'].split(' ')[0]
            chat_id = message['chat']['id']

            if command_prefix.startswith("/help") or command_prefix.startswith("/telegram_help"):
                msg = 'Инструкция по работе с ботом. Выберите раздел для просмотра доступных команд.\n'

                for name in OBJECTS:
                    if hasattr(OBJECTS[name], 'get_description'):
                        msg += '\n' + OBJECTS[name].get_description()

                send_to_chat(msg, chat_id)

                return

            if command_prefix.startswith("/start") or command_prefix.startswith("/telegram_start"):
                send_to_chat("Отлично, работаем дальше.", chat_id)
                return

            Telegram.unknown_command(chat_id)

        except Exception as e:
            logging.error("Error while Telegram make_answer: {}".format(e))

    @staticmethod
    def unknown_command(chat_id):
        """
        Отправляет сообщение об ошибке.
        :param chat_id: Telegram ID чата (int)
        :return:
        """
        try:
            send_to_chat(random.choice([
                'Не знаю такой команды', 'Что-то не понимаю', 'Сложная команда :('
            ]), chat_id)

        except Exception as e:
            logging.error("Error while Telegram unknown_command: {}".format(e))
