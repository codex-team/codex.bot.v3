import base64
import json
import random

import requests
import logging
from urllib.parse import urlencode

from aiohttp import web

from components.simple import send_to_chat, register_commands, send_image_to_chat, send_object_to_chat
from configuration.globalcfg import TELEGRAM_WEBHOOK, SLACK_ID, SLACK_SECRET, URL
from core.web import telegram_callback, slack_callback
from slackclient import SlackClient



class Slack:

    def __init__(self, api_token, web_app):
        """
        Инициализирует aiohttp APP и Telegram API Token
        :param api_token:
        :param web_app:
        """
        self.API_TOKEN = api_token
        self.WEB_APP = web_app
        self.REDIRECT_URI = "{}slack/auth".format(URL)

    def set_webhook(self):
        """
        Обновляет веб-хук для бота на текущий сервер
        :return:
        """
        sc = SlackClient(self.API_TOKEN)
        sc.api_call('')
        # try:
        #     result = requests.get(query)
        # except Exception as e:
        #     logging.debug(e)
        # else:
        #     logging.debug(result.content)

    def set_routes(self):
        """
        Устанавливает роуты, которые будет обрабатывать модуль.
            - /telegram/callback - сообщения от Telegram.
        :return:
        """
        self.WEB_APP.router.add_post('/slack/callback', slack_callback)
        self.WEB_APP.router.add_get('/slack/auth', self.slack_auth)

    def register_commands(self, global_commands):
        """
        Описывает какие команды переадресовывать данному модулю.
            - help - справка.
            - start - приветствие.
        :param global_commands:
        :return:
        """
        register_commands('slack', ['help', 'start'], global_commands)

    async def slack_auth(self, request):
        """
        Process messages from telegram bot
        :return:
        """

        try:
            code = request.rel_url.query.get("code", "")

            if code:
                result = requests.get("https://slack.com/api/oauth.access?client_id={}&client_secret={}&code={}&redirect_uri={}"
                             .format(SLACK_ID, SLACK_SECRET, code, self.REDIRECT_URI))
                if result.status_code == 200:
                    token = result.json().get("access_token", "")
                    self.API_TOKEN = token
                    logging.info(token)

            return web.Response(text="OK")

        except Exception as e:
            logging.error(e)