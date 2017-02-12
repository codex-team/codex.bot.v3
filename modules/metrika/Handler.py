import logging

import requests
from aiohttp import web

from components.simple import register_commands
from configuration.globalcfg import MODULES
from .._common.CommonHandler import CommonHandler, DB_SETTINGS
from modules.metrika.Module import MetrikaModule


class MetrikaHandler(CommonHandler):

    settings = {
        'ID': '33702b364e714c899541eff4cd344342',
        'PASS': '691755c5ea614410b23b5eec7683d245',
        'OAUTH_TOKEN': 'AQAAAAAad3sxAAQMPJlBYuNkg01rhJwH1lwh9B4',
        'COUNTER_ID': '',
        'URL': 'https://api-metrika.yandex.ru/'
    }

    def __init__(self, web_app):
        super().__init__(web_app)

        assert MetrikaHandler.settings['OAUTH_TOKEN']

    def set_routes(self):
        self.WEB_APP.router.add_post('/metrika/{chat_hash}', self.metrika_callback)
        self.WEB_APP.router.add_get('/metrika/callback', self.metrika_yandex_callback)

    def register_commands(self, global_commands):
        register_commands('metrika', ['help', 'start', 'stop', 'add_counter', 'del_counter', 'today', 'weekly', 'monthly'], global_commands)

    async def run_telegram(self, params):
        module = MetrikaModule(MetrikaHandler.get_mongo(DB_SETTINGS['MONGO_HOST'], DB_SETTINGS['MONGO_PORT'],
                                                        DB_SETTINGS['MONGO_DB_NAME']),
                               MetrikaHandler.get_redis(DB_SETTINGS['REDIS_HOST'], DB_SETTINGS['REDIS_PORT'],
                                                        DB_SETTINGS['REDIS_PASSWORD']),
                               MetrikaHandler.settings)
        module.run_telegram(params)

    @staticmethod
    def run_web(params):
        module = MetrikaModule(MetrikaHandler.get_mongo(DB_SETTINGS['MONGO_HOST'], DB_SETTINGS['MONGO_PORT'],
                                                        DB_SETTINGS['MONGO_DB_NAME']),
                               MetrikaHandler.get_redis(DB_SETTINGS['REDIS_HOST'], DB_SETTINGS['REDIS_PORT']),
                               MetrikaHandler.settings)
        module.run_web(params)

    def metrika_callback(self, request):
        return "HELLO"

    async def metrika_yandex_callback(self, request):
        code = request.rel_url.query.get("code", "")
        chat_id = request.rel_url.query.get('state', '')

        logging.debug("Got Metrika_yandex_callback: {}".format(request.rel_url.path))

        if code and chat_id:
            try:
                s = requests.post('https://oauth.yandex.ru/token',
                                     data={'code': code, 'grant_type': 'authorization_code'},
                                     headers={'Content-type': 'application/x-www-form-urlencoded'},
                                     auth=(MODULES['metrika']['ID'], MODULES['metrika']['PASS'])) # TODO:

                access_token = s.json()['access_token']
                if access_token:
                    MetrikaHandler.run_web({"module": 'metrika',
                                         "url": request.rel_url.path,
                                         "type": 1,  # Web message
                                         "data": {
                                             "access_token": access_token,
                                             "chat_id": chat_id
                                            }
                                         })

            except Exception as e:
                logging.error("Error: %s" % e)

        return web.Response(text='OK')
