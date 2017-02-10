import asyncio
import logging

import motor.motor_asyncio

from aiohttp import web
from core.telegram import Telegram
from configuration.globalcfg import MONGO_DB_NAME, MONGO_HOST, TELEGRAM_API_TOKEN, OPTIONS, WEB_HOST, WEB_PORT, \
    MONGO_PORT, COMMANDS, OBJECTS
from modules._common.CommonHandler import CommonHandler
from modules.github.Handler import GithubHandler

from modules.metrika.Handler import MetrikaHandler
from modules.notifications.Handler import NotificationsHandler
from modules.reminder.Handler import ReminderHandler

if __name__ == "__main__":

    ###
    # Create asyncio event loop and HTTP Application
    ###
    loop = asyncio.get_event_loop()
    app = web.Application(loop=loop)

    ###
    # Enable logging and set it to DEBUG level
    ###
    logging.getLogger('asyncio').setLevel(logging.DEBUG)
    logging.basicConfig(level=logging.DEBUG)

    ###
    # Enable MongoDB support
    ###
    MONGO_CLIENT = motor.motor_asyncio.AsyncIOMotorClient(MONGO_HOST, MONGO_PORT)
    MONGO_DB = MONGO_CLIENT[MONGO_DB_NAME]
    app['db'] = MONGO_DB

    ###
    # Activate modules
    ###
    MODULES = [
        (Telegram, (TELEGRAM_API_TOKEN, app), 'telegram'),
        (NotificationsHandler, (app,), 'notifications'),
        (GithubHandler, (app,), 'github'),
        (MetrikaHandler, (app, ), 'metrika'),
        # (ReminderHandler, (app,), 'reminder')
    ]

    ###
    # Check MongoDB connection TODO: Redis
    ###
    if not CommonHandler.check_connection():
        exit()

    for module in MODULES:
        obj = module[0](*module[1])
        obj.set_routes()
        obj.register_commands(COMMANDS)
        OBJECTS[module[2]] = obj

    if OPTIONS.get('set_webhook'):
        OBJECTS['telegram'].set_webhook()

    logging.debug(COMMANDS)

    ###
    # Start app
    ###
    web.run_app(app, host=WEB_HOST, port=WEB_PORT)
