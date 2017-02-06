import logging

from aiohttp import web
from pymongo import MongoClient
from components.simple import register_commands
from modules.notifications.Module import NotificationsModule
from .._common.configuration import MONGO_HOST, MONGO_PORT, MONGO_DB_NAME, QUEUE_SERVER


async def notifications_callback(request):
    try:
        data = await request.post()
        chat_hash = request.match_info['chat_hash']
        if 'message' not in data:
            logging.warning("Message not found in data.")
            return web.Response(text='ERROR')

        message = data.get("message", "")
        logging.info((chat_hash, data))

        NotificationsHandler.run({"module": "notifications",
                                  "url": request.rel_url.path,
                                  "type": 1,  # Notifications message
                                  "data": {
                                    "chat_hash": chat_hash,
                                    "payload": message
                                  }
                                  })
    except Exception as e:
        logging.warning("[notifications_callback] Message process error: [%s]" % e)

    return web.Response(text='OK')


class NotificationsHandler:

    def __init__(self, web_app):
        self.WEB_APP = web_app

    def set_routes(self):
        self.WEB_APP.router.add_post('/notifications/{chat_hash}', notifications_callback)

    def register_commands(self, global_commands):
        register_commands('notifications', ['help', 'start'], global_commands)

    @staticmethod
    def run(params):
        NotificationsHandler.notifications_run(params)

    @staticmethod
    def notifications_run(params):
        MONGO_CLIENT = MongoClient(MONGO_HOST, MONGO_PORT)
        MONGO_DB = MONGO_CLIENT[MONGO_DB_NAME]
        notifications_module = NotificationsModule(QUEUE_SERVER, MONGO_DB)
        notifications_module.callback(params)
