import logging
from components.simple import generate_hash
from .._common.functions import send_text
from .._common.configuration import URL


class NotificationsModule:
    def __init__(self, host, db):
        self.host = host
        self.db = db

    def callback(self, params):
        try:

            # Process commands from Web
            if params['type'] == 1:
                chat_hash = params['data']['chat_hash']
                payload = params['data']['payload']
                self.send_notification(payload, chat_hash)

            # Process commands from Telegram Bot
            if params['type'] == 0:
                payload = params['data']['payload']
                self.make_answer(payload)

        except Exception as e:
            logging.error("Notifications module error: {}".format(e))

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

    def make_answer(self, message):
        try:
            command_prefix = message['text'].split(' ')[0]
            chat_id = message['chat']['id']

            if command_prefix.startswith("/help") or command_prefix.startswith("/notifications_help"):
                send_text("/notifications_start - получить ссылку для передачи сообщений в данный чат.", chat_id)
                return

            if command_prefix.startswith("/start") or command_prefix.startswith("/notifications_start"):
                token = self.get_chat_token(chat_id)
                message = "Ссылка для отправки сообщений в данный чат: {}notifications/{}\n\n" + \
                          "Сообщение отправляйте в POST параметре message."
                send_text(message.format(URL, token), chat_id)
                return

            send_text('%%i_dont_know_such_a_command%%', chat_id)

        except Exception as e:
            logging.error("Error while Notifications make_answer: {}".format(e))
