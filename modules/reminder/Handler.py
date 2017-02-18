import asyncio
import logging

from components.simple import register_commands
from modules.reminder.Module import ReminderModule
from .._common.CommonHandler import CommonHandler, DB_SETTINGS


class ReminderHandler(CommonHandler):

    def __init__(self, web_app):
        super().__init__(web_app)

    def set_routes(self):
        pass

    def register_commands(self, global_commands):
        register_commands('reminder', ['help', 'start', 'remind', 'notes', 'noteadd', 'notedel', 'reminder_del'], global_commands)

    async def run_telegram(self, params):
        module = ReminderModule(ReminderHandler.get_mongo(DB_SETTINGS['MONGO_HOST'], DB_SETTINGS['MONGO_PORT'],
                                                        DB_SETTINGS['MONGO_DB_NAME']),
                                ReminderHandler.get_redis(DB_SETTINGS['REDIS_HOST'], DB_SETTINGS['REDIS_PORT']))
        await module.run_telegram(params)
