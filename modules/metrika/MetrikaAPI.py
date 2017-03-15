# -*- coding: utf-8 -*-

import json
import time
import random
from datetime import timedelta, date, datetime

import requests
import logging

from urllib.parse import urlencode


class MetrikaAPI(object):

    def __init__(self, oauth_token, counter_id, chat_id):

        try:
            self.OAUTH_TOKEN = oauth_token
            self.COUNTER_ID = counter_id
            self.chat_id = chat_id
            self.URL = 'https://api-metrika.yandex.ru/'
            self.HEADERS = {'Accept': 'application/x-yametrika+json'}

        except Exception as e:
            logging.error("Error: %s" % e)

    def get(self):
        greeting = MetrikaAPI.get_greeting()
        visits = self.get_visit_statistics()
        counter_name = self.get_counter_name()

        telegram_message = (("Hello, %s\n%s\n\n%s") % (counter_name, greeting, (visits + links)))
        return telegram_message

    def get_counter_name(self):
        params = urlencode(self.get_params())

        try:
            result_json = requests.get(self.URL + 'management/v1/counter/{}'.format(self.COUNTER_ID),
                                       params=params,
                                       headers=self.HEADERS,
                                       timeout=5).json()
            logging.debug(result_json)
            message = "{} ({})".format(result_json['counter']['name'], result_json['counter']['site'])

        except Exception as e:
            print("There was an error: %r" % e)
            return Exception

        return message

    def get_counters(self):
        params = urlencode(self.get_params())
        counters = []

        try:
            result_json = requests.get(self.URL + 'management/v1/counters',
                                       params=params,
                                       headers=self.HEADERS,
                                       timeout=5).json()

            for counter in result_json['counters']:
                counters.append(counter)

        except Exception as e:
            print("There was an error: %r" % e)
            return []

        return counters

    @staticmethod
    def get_login(token):
        params = {'oauth_token': token}

        try:
            result_json = requests.get('https://login.yandex.ru/info',
                                       params=params,
                                       headers={'Accept': 'application/x-yametrika+json'},
                                       timeout=5).json()

            login = result_json['login']

        except Exception as e:
            print("There was an error: %r" % e)
            return ''

        return login

    @staticmethod
    def get_greeting():
        greeting = ['Hey guys, look what i\'ve got here...',
                    'Wow, so many hits!', 'I have some statistics for today.',
                    'Hi team, look what i\'ve got...', 'Today',
                    'Today was a hard day...',
                    'Anyone reading me??? Okay, here\'s the statistics :(',
                    'I talked with Yandex API and it gave me a message for you.',
                    'Hi, team, how are your pull requests today?',
                    'Hey, CodeX! Codex.bot is sending you greetings, he wants to join our chat.']

        return random.choice(greeting)

    def get_visit_statistics(self, period="today"):
        """
        method returns string of unique users, page_views for today
        example:
            users: 100
            Hits : 300
        """

        params = {'id': self.COUNTER_ID, 'oauth_token': self.OAUTH_TOKEN,
                  'date2': time.strftime('%Y%m%d'),
                  'metrics': 'ym:s:visits,ym:s:pageviews,ym:s:users'}
        dt = time.strftime('%Y%m%d')
        do = datetime.strptime(dt, '%Y%m%d')
        if period == "today":
            params['date1'] = dt
        if period == "weekly":
            start = do - timedelta(days=do.weekday())
            params['date1'] = start.strftime('%Y%m%d')
        if period == "monthly":
            start = date(do.year, do.month, 1)
            params['date1'] = start.strftime('%Y%m%d')

        print(params)

        try:
            result_json = requests.get(self.URL + 'stat/v1/data/bytime', params=params, timeout=5).json()

            stat = result_json['totals'][0]
            users = int(stat[2])
            hits = int(stat[1])

        except Exception as e:
            return None

        return (users, hits)

    def get_params(self, date1=False, date2=False):
        params = {'id': self.COUNTER_ID, 'oauth_token': self.OAUTH_TOKEN}
        if date1:
            params['date1'] = time.strftime('%Y%m%d')
        if date2:
            params['date2'] = time.strftime('%Y%m%d')
        return params
