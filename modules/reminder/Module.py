import asyncio
import logging

from modules._common.functions import send_text


class ReminderModule:
    def __init__(self, db, redis):
        self.db = db
        self.redis = redis

    async def run_telegram(self, params):
        try:
            payload = params['data']['payload']
            await self.make_answer(payload)

        except Exception as e:
            logging.error("Metrika module run_telegram error: {}".format(e))

    async def make_answer(self, message):
        try:
            command_prefix = message['text'].split(' ')[0]
            chat_id = message['chat']['id']

            if command_prefix.startswith("/help") or command_prefix.startswith("/reminder_help"):
                return send_text("Hello. This module can remind you about everything.\nJust press /remind <text>", chat_id)

            if command_prefix.startswith("/start") or command_prefix.startswith("/reminder_start"):
                return send_text("Just press /remind <text>", chat_id)

            if command_prefix.startswith("/remind"):
                return await self.reminder_telegram_remind(message, chat_id)

            send_text('%%i_dont_know_such_a_command%%', chat_id)

        except Exception as e:
            logging.error("Error while Reminder make_answer: {}".format(e))

    async def reminder_telegram_remind(self, message, chat_id):
        message_to_remind = message['text'].split(' ', 1)
        if len(message_to_remind) < 2:
            send_text("Input message after /remind command. \nExample: /remind Buy some candies.", chat_id)
            return
        else:
            await asyncio.sleep(5)
            send_text("Hi! Do you remember about: '{}'?".format(message_to_remind[1]), chat_id)
