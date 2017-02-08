import asyncio
import logging

import motor.motor_asyncio

from aiohttp import web
from core.telegram import Telegram
from configuration.globalcfg import MONGO_DB_NAME, MONGO_HOST, TELEGRAM_API_TOKEN, OPTIONS, WEB_HOST, WEB_PORT, \
    MONGO_PORT, COMMANDS, OBJECTS, MODULES, DB_SETTINGS

from modules.metrika.Handler import MetrikaHandler


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
        # (NotificationsHandler, (app,), 'notifications'),
        # (GithubHandler, (app,), 'github'),
        (MetrikaHandler, (app, ), 'metrika')
    ]

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
