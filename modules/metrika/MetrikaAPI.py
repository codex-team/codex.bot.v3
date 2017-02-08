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
        links = self.get_ref_links()
        counter_name = self.get_counter_name()

        telegram_message = (("Hello, %s\n%s\n\n%s") % (counter_name, greeting, (visits + links)))
        return telegram_message

    def get_counter_name(self):
        params = urlencode(self.get_params())
        message = ""

        try:
            result_json = requests.get(self.URL + 'counter/%s/' % self.COUNTER_ID,
                                       params=params,
                                       headers=self.HEADERS,
                                       timeout=5).json()

            message = "%s (%s)" % (result_json['counter']['name'], result_json['counter']['site'])

        except Exception as e:
            print("There was an error: %r" % e)
            return "There was an error: %r" % e

        return message

    def get_counters(self):
        params = urlencode(self.get_params())
        counters = []

        try:
            result_json = requests.get(self.URL + 'counters',
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

        params = {'id': self.COUNTER_ID, 'oauth_token': self.OAUTH_TOKEN, 'date2': time.strftime('%Y%m%d')}
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
            result_json = requests.get(self.URL + 'stat/traffic/summary.json', params=params, timeout=5).json()

            stat = result_json['totals']
            users = int(stat['visitors'])
            hits = int(stat['page_views'])

        except Exception as e:
            return None

        return (users, hits)

    def get_ref_links(self):
        """
        method returns string of refferal links and number of visits
        :param date1 string - date in format YYYYMMDD
        :param date2 string - date in format YYYYMMDD
        example
            https://example.com : 500
            https://example1.com : 100
        """

        message = None
        params = urlencode(self.get_params(date1=True, date2=True))

        try:
            result_json = requests.get(self.URL + 'stat/sources/sites.json', params=params, timeout=5).json()

        except Exception as e:
            return "There was an error: %r" % e

        if result_json['rows'] != 0:
            for link_info in result_json['data']:
                message.append((link_info['visits'], link_info['url']))
            return message
        else:
            return None

    def get_search_engine_stats(self):
        """
        method returns string, name of search engine and number of visits from them
        :param date1 string - date in format YYYYMMDD
        :param date2 string - date in format YYYYMMDD
        example
            Google: 500
            Yandex: 300
        """

        message = ''
        params = urlencode(self.get_params(date1=True, date2=True))

        req = requests.get(self.URL + 'stat/sources/search_engines.json', params=params)
        try:
            res = requests.get(req)

        except Exception as e:
            return "There was an error: %r" % e

        stat = json.load(res)

        for search_engine in stat['data']:
            message += "%s: %d\n" % (search_engine['name'].split(',')[0], search_engine['visits'])

        return message

    def get_params(self, date1=False, date2=False):
        params = {'id': self.COUNTER_ID, 'oauth_token': self.OAUTH_TOKEN}
        if date1:
            params['date1'] = time.strftime('%Y%m%d')
        if date2:
            params['date2'] = time.strftime('%Y%m%d')
        return params

    def send(self):
        if not self.error:
            send_to_chat(self.get(), self.chat_id, CConfig.MODULES['api_token'])
