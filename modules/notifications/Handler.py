import logging

from aiohttp import web
from pymongo import MongoClient
from components.simple import register_commands
from configuration.globalcfg import DB_SETTINGS
from modules._common.CommonHandler import CommonHandler
from modules.notifications.Module import NotificationsModule


async def notifications_callback(request):
    try:
        data = await request.post()
        chat_hash = request.match_info['chat_hash']
        if 'message' not in data:
            logging.warning("Message not found in data.")
            return web.Response(text='ERROR')

        message = data.get("message", "")
        logging.info((chat_hash, data))

        await NotificationsHandler.run_web({"module": "notifications",
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


class NotificationsHandler(CommonHandler):

    def __init__(self, web_app):
        super().__init__(web_app)

    def set_routes(self):
        self.WEB_APP.router.add_post('/notifications/{chat_hash}', notifications_callback)

    def register_commands(self, global_commands):
        register_commands('notifications', ['help', 'start'], global_commands)

    @staticmethod
    async def run_telegram(params):
        module = NotificationsModule(NotificationsHandler.get_mongo(DB_SETTINGS['MONGO_HOST'],
                                                                    DB_SETTINGS['MONGO_PORT'],
                                                                    DB_SETTINGS['MONGO_DB_NAME']),
                                     NotificationsHandler.get_redis(DB_SETTINGS['REDIS_HOST'],
                                                                    DB_SETTINGS['REDIS_PORT']),
                                     )
        await module.run_telegram(params)

    @staticmethod
    async def run_web(params):
        module = NotificationsModule(NotificationsHandler.get_mongo(DB_SETTINGS['MONGO_HOST'],
                                                                    DB_SETTINGS['MONGO_PORT'],
                                                                    DB_SETTINGS['MONGO_DB_NAME']),
                                     NotificationsHandler.get_redis(DB_SETTINGS['REDIS_HOST'],
                                                                    DB_SETTINGS['REDIS_PORT']),
                                     )
        await module.run_web(params)
