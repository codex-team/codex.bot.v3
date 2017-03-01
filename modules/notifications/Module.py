import logging
from components.simple import generate_hash
from configuration.globalcfg import URL
from core.telegram import Telegram
from .._common.functions import send_text


class NotificationsModule:
    def __init__(self, db, redis):
        self.db = db
        self.redis = redis

    async def run_web(self, params):
        try:
            chat_hash = params['data']['chat_hash']
            payload = params['data']['payload']
            self.send_notification(payload, chat_hash)
        except Exception as e:
            logging.error("Notifications module run_web error: {}".format(e))

    async def run_telegram(self, params):
        try:
            command_prefix = params['data']['command_prefix']
            payload = params['data']['payload']
            self.make_answer(command_prefix, payload)
        except Exception as e:
            logging.error("Notifications module run_telegram error: {}".format(e))

    def get_chat_token(self, chat_id):
        """
            Return or generate new token for the chat
            :param chat_id: Telegram chat id
            :return: unique chat hash (as route)
        """
        user = self.db.notifications_chats.find_one({'id': chat_id})
        if not user:
            hash = generate_hash(size=8)
            self.db.notifications_chats.insert_one({'id': chat_id, 'hash': hash})
            return hash
        else:
            return user['hash']

    def send_notification(self, message, chat_hash):
        chat_id = self.db.notifications_chats.find_one({'hash': chat_hash})

        if chat_id:
            send_text(message, chat_id['id'])
        else:
            logging.warning("Message not sent. Hash = {}".format(chat_hash))

    def make_answer(self, command_prefix, message):
        try:
            chat_id = message['chat']['id']

            if command_prefix == "/help":
                send_text("/notifications_start - получить ссылку для передачи сообщений в данный чат.", chat_id)
                return

            if command_prefix == "/start":
                token = self.get_chat_token(chat_id)
                message = "Ссылка для отправки сообщений в данный чат: {}notifications/{}\n\n" + \
                          "Сообщение отправляйте в POST параметре message."
                send_text(message.format(URL, token), chat_id)
                return

            Telegram.unknown_command(chat_id)

        except Exception as e:
            logging.error("Error while Notifications make_answer: {}".format(e))
