import asyncio
import logging

from components.simple import create_buttons_list
from core.telegram import Telegram
from modules._common.functions import send_text, send_keyboard


class ReminderModule:
    def __init__(self, db, redis):
        self.db = db
        self.redis = redis

    async def run_telegram(self, params):
        try:
            command_prefix = params['data']['command_prefix']
            payload = params['data']['payload']
            if not params['data']['inline']:
                await self.make_answer(command_prefix, payload)
            else:
                self.process_inline_command(command_prefix, payload)

        except Exception as e:
            logging.error("Metrika module run_telegram error: {}".format(e))

    def process_inline_command(self, command_prefix, message):
        try:
            chat_id = message['chat']['id']

            if command_prefix == "/reminder_del":
                cache_id = message["text"].split("#")[-1]
                self.remove_note_by_id(cache_id, chat_id)

        except Exception as e:
            logging.error("Error while Metrika process_inline_command: {}".format(e))

    async def make_answer(self, command_prefix, message):
        try:
            chat_id = message['chat']['id']

            if command_prefix == "/help":
                return send_text("Hello. This module can remind you about everything.\nJust press /remind <text>", chat_id)

            if command_prefix == "/start":
                return send_text("Just press /remind <text>", chat_id)

            if command_prefix == "/remind":
                return await self.reminder_telegram_remind(message, chat_id)

            if command_prefix == "/noteadd":
                self.add_note(message, chat_id)
                return

            if command_prefix == "/notedel":
                self.remove_note(message, chat_id)
                return

            if command_prefix == "/notes":
                self.show_notes(chat_id)
                return

            Telegram.unknown_command(chat_id)

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

    def add_note(self, message, chat_id):
        note_text = message['text'].split(' ', 1)
        if len(note_text) < 2:
            send_text("Input message after /noteadd command. \nExample: /noteadd Implement new super feature.", chat_id)
            return
        else:
            id = self.db.reminder_notes.count({'chat_id': chat_id}) + 1
            self.db.reminder_notes.insert_one({'note': note_text[1], 'chat_id': chat_id, 'id': id})
            send_text("Оки. :)", chat_id)

    def show_notes(self, chat_id):
        notes = list(self.db.reminder_notes.find({'chat_id': chat_id}))
        if not len(notes):
            send_text("Записей не найдено", chat_id)
        else:
            msg = 'Записи: \n'
            for note in notes:
                msg += "#{} – {}\n".format(note.get('id', ''), note.get('note', ''))
            send_text(msg, chat_id)

    def remove_note(self, message, chat_id):
        id = message['text'].split(' ', 1)
        if len(id) < 2:
            notes = list(self.db.reminder_notes.find({'chat_id': chat_id}))
            # send_text("Input note id /notedel command. \nExample: /notedel 24", chat_id)
            if len(notes):
                send_keyboard("Выберите записку, которую хотите удалить.\n",
                          create_buttons_list(notes, lambda x: {'text': x.get('note', ''), 'callback_data': '/reminder_del #{}'.format(x.get('id', ''))}),
                          chat_id)
            else:
                send_text("Записей не найдено", chat_id)
            return
        else:
            self.remove_note_by_id(id[1], chat_id)

    def remove_note_by_id(self, id, chat_id):
        result = self.db.reminder_notes.delete_many({'id': int(id), 'chat_id': chat_id})
        if result.deleted_count == 1:
            send_text("Удалена запись #{}".format(id), chat_id)
        else:
            send_text("Ошибка. Такая запись не найдена.", chat_id)