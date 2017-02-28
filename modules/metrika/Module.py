import logging

import time
from datetime import timedelta

import pytz as pytz

from configuration.globalcfg import scheduler
from components.simple import generate_hash, create_buttons_list
from core.telegram import Telegram
from modules.metrika.MetrikaAPI import MetrikaAPI
from .._common.functions import send_text, send_keyboard



class MetrikaModule:
    def __init__(self, db, redis, settings):
        self.db = db
        self.redis = redis
        self.settings = settings

    def run_telegram(self, params):
        try:
            payload = params['data']['payload']
            if not params['data']['inline']:
                self.make_answer(payload)
            else:
                self.process_inline_command(payload)

        except Exception as e:
            logging.error("Metrika module run_telegram error: {}".format(e))

    def run_web(self, params):
        try:
            access_token = params['data'].get("access_token", "")
            chat_id = params['data'].get("chat_id", "")
            metrika_api = MetrikaAPI(access_token, '', chat_id)

            logging.debug("run_web with params: {}".format(access_token, chat_id))

            if not self.db.metrika_tokens.find_one({'access_token': access_token}):
                self.db.metrika_tokens.insert_one({'id': generate_hash(12),
                                                   'chat_id': chat_id,
                                                   'access_token': access_token})

            self.metrika_telegram_start(chat_id)

        except Exception as e:
            logging.error("Metrika module run_web error: {}".format(e))

    def make_answer(self, message):
        try:
            command_prefix = message['text'].split(' ')[0]
            chat_id = message['chat']['id']

            if command_prefix.startswith("/help") or command_prefix.startswith("/metrika_help"):
                send_text(self.metrika_telegram_help(chat_id), chat_id)
                return

            if command_prefix.startswith("/start") or command_prefix.startswith("/metrika_start"):
                self.metrika_telegram_start(chat_id)
                return

            if command_prefix.startswith("/stop") or command_prefix.startswith("/metrika_stop"):
                self.metrika_telegram_stop(chat_id)
                return

            if command_prefix.startswith("/today") or command_prefix.startswith("/metrika_today"):
                self.metrika_telegram_daily("today", chat_id)
                return

            if command_prefix.startswith("/weekly") or command_prefix.startswith("/metrika_weekly"):
                self.metrika_telegram_daily("weekly", chat_id)
                return

            if command_prefix.startswith("/monthly") or command_prefix.startswith("/metrika_monthly"):
                self.metrika_telegram_daily("monthly", chat_id)
                return

            if command_prefix.startswith("/subscribe") or command_prefix.startswith("/metrika_subscribe"):
                self.metrika_telegram_subscribe(chat_id)
                return

            if command_prefix.startswith("/unsubscribe") or command_prefix.startswith("/metrika_unsubscribe"):
                self.metrika_telegram_unsubscribe(chat_id)
                return

            Telegram.unknown_command(chat_id)

        except Exception as e:
            logging.error("Error while Metrika make_answer: {}".format(e))

    def process_inline_command(self, message):
        try:
            command_prefix = message['text'].split(' ')[0]
            chat_id = message['chat']['id']

            if command_prefix.startswith("/add_counter") or command_prefix.startswith("/metrika_add_counter"):
                cache_id = message["text"].split("#")[-1]
                cached_data = self.redis.hgetall(cache_id)
                if cached_data:
                    self.metrika_telegram_add(chat_id, cached_data)

            if command_prefix.startswith("/del_counter") or command_prefix.startswith("/metrika_del_counter"):
                cache_id = message["text"].split("#")[-1]
                cached_data = self.redis.hgetall(cache_id)
                if cached_data:
                    self.metrika_telegram_del(chat_id, cached_data)

            if command_prefix.startswith("/subscribe") or command_prefix.startswith("/metrika_subscribe"):
                hour = message['text'].split()[1]
                self.metrika_telegram_inline_subscribe(hour, chat_id)
                send_text('Вы успешно подписались на ежедневный дайджест в {}:00'.format(hour), chat_id)

            if command_prefix.startswith("/unsubscribe") or command_prefix.startswith("/metrika_unsubscribe"):
                command = message['text'].split()
                self.metrika_telegram_inline_unsubscribe(chat_id)

                if len(command) > 1:
                    self.metrika_telegram_subscribe(chat_id)
                else:
                    send_text('Вы отписались от дайджеста', chat_id)

        except Exception as e:
            logging.error("Error while Metrika process_inline_command: {}".format(e))

    ### MESSAGES ###

    def metrika_telegram_help(self, chat_id):
        msg = "Этот модуль поможет вам следить за статистикой сайта. Возможности модуля: \n\n" \
              "- моментальное получение текущих значений счетчиков (DAU, просмотры, источники) за период (день, неделя, месяц)\n" \
              "- уведомление о достижении целей (например, бот сообщит о достижении показателя в 10k уникальных посетителей)"

        metrikas = list(self.db.metrika_counters.find({'chat_id': chat_id}))
        if not len(metrikas):
            msg += "\n\nВ данный момент модуль не активирован.\n\nДля настройки модуля, используйте команду /metrika_start"
        else:
            msg += "\n\nПодключенные сайты.\n\n"
            for metrika in metrikas:
                msg += "%s\n" % metrika['counter_name']
            msg += "\nДля отключения счетчика используйте команду /metrika_stop\n" \
                   "Подключить еще один сайт можно с помощью команды /metrika_start\n\n" \
                   "Меню модуля: /metrika_help"
        return msg

    def metrika_telegram_start(self, chat_id):
        msg = ""

        metrikas = list(self.db.metrika_tokens.find({'chat_id': chat_id}))
        if not len(metrikas):
            msg +=   "Для подключения счетчика, вам нужно авторизовать бота. " \
                     "Для этого, пройдите по ссылке и подтвердите доступ к счетчику. \n\n" \
                     "https://oauth.yandex.ru/authorize?response_type=code&client_id={}&state={}\n".format(
                        self.settings['ID'],
                        chat_id
                     )
            send_text(msg, chat_id)
        else:
            buttons = self.get_counters(metrikas[0], "start")
            if not len(buttons):
                send_text("У вас нет доступных счетчиков Яндекс Метрики.", chat_id)
            else:
                send_keyboard("Теперь выберите сайт, статистику которого хотите получать.\n",
                          buttons,
                          chat_id)

    def metrika_telegram_stop(self, chat_id):
        msg = ""

        metrikas = list(self.db.metrika_counters.find({'chat_id': chat_id}))
        if not len(metrikas):
            send_text("Подключенных счетчиков не найдено.", chat_id)
        else:
            send_keyboard("Выберите сайт, который хотите отключить.\n",
                          self.get_chat_counters(metrikas, chat_id),
                          chat_id)

    def metrika_telegram_add(self, chat_id, params):
        counter = self.db.metrika_counters.find_one({'chat_id': chat_id, 'counter_id': params['counter_id']})
        if counter:
            send_text("Счетчик <{}> уже прикреплен к данному чату.".format(params['name']), chat_id)
        else:
            self.db.metrika_counters.insert_one({
                'chat_id': chat_id,
                'counter_id': params['counter_id'],
                'counter_name': params['name'],
                'access_token': params['access_token']
            })
            send_text("Готово! Сайт <{}> успешно подключен.".format(params['name']), chat_id)
            self.metrika_telegram_help(chat_id)

    def metrika_telegram_del(self, chat_id, params):
        result = self.db.metrika_counters.delete_one({'chat_id': chat_id, 'counter_id': params['counter_id']})
        if result.deleted_count:
            send_text("Счетчик <{}> успешно откреплен от данного чата.".format(params['name']), chat_id)
        else:
            send_text("Счетчик <{}> к данному чату не подключен.".format(params['name']), chat_id)

    def metrika_telegram_daily(self, cmd, chat_id):
        metrikas = list(self.db.metrika_counters.find({'chat_id': chat_id}))
        message = "%s\n\n" % self.stats(cmd)
        for metrika in metrikas:
            try:
                metrikaAPI = MetrikaAPI(metrika['access_token'], metrika['counter_id'], chat_id)
                result = metrikaAPI.get_visit_statistics(cmd)
                if result:
                    users, hits = result
                    message += "%s:\n%d уникальных посетителей\n%d просмотров\n\n" % (metrika['counter_name'],
                                                                                      users, hits)
            except Exception as e:
                logging.warning("Metrika API exception: %s" % e)

        send_text(message, chat_id)

    ### SUPPORT ###

    def get_counters(self, token, cmd):
        metrikaAPI = MetrikaAPI(token['access_token'], '', token['chat_id'])
        counters = metrikaAPI.get_counters()
        buttons = []
        buttons_row = []
        for counter in counters:
            cache_link = generate_hash(18)
            buttons_row.append(
                {
                    'text': counter["name"],
                    'callback_data': "/metrika_add_counter #{}#{}".format(cmd, cache_link)
                }
            )
            self.redis.hmset(cache_link, {'access_token': token['access_token'],
                                          'counter_id': counter['id'],
                                          'cmd': "start",
                                          'name': counter['name']})

            if len(buttons_row) == 2:
                buttons.append(buttons_row[:])
                buttons_row = []
        if len(buttons_row):
            buttons.append(buttons_row[:])
        return buttons

    def get_chat_counters(self, metrikas, chat_id):
        buttons = []
        buttons_row = []
        for counter in metrikas:
            cache_link = generate_hash(18)
            buttons_row.append({
                'text': counter['counter_name'],
                'callback_data': "/metrika_del_counter #{}#{}".format("stop", cache_link)
            })
            self.redis.hmset(cache_link, {'counter_id': counter['counter_id'],
                                          'chat_id': chat_id,
                                          'cmd': "stop",
                                          'name': counter['counter_name']})

            if len(buttons_row) == 2:
                buttons.append(buttons_row[:])
                buttons_row = []
        if len(buttons_row):
            buttons.append(buttons_row[:])
        return buttons

    def stats(self, period="today"):
        def month(n):
            d = {1: "января", 2: "февраля", 3: "марта", 4: "апреля", 5: "мая", 6: "июня",
                 7: "июля", 8: "августа", 9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"}
            return d[n]

        def week(n):
            d = {0: "понедельник", 1: "вторник", 2: "среда", 3: "четверг", 4: "пятница", 5: "суббота",
                 6: "воскресенье"}
            return d[n]

        import datetime
        t = datetime.datetime.now(pytz.timezone('Europe/Moscow'))

        dt = time.strftime('%Y%m%d')
        do = datetime.datetime.strptime(dt, '%Y%m%d')
        message = ""

        if period == "today":
            message = "Сегодня %s %s, %s. Данные к %s:%s" % (str(t.day).zfill(2),
                                                             month(t.month),
                                                             week(t.weekday()),
                                                             str(t.hour).zfill(2),
                                                             str(t.minute).zfill(2))
        if period == "weekly":
            start = do - timedelta(days=do.weekday())
            start.strftime('%Y%m%d')
            message = "С понедельника, %s %s по сегодняшний день." % (str(start.day).zfill(2), month(start.month))
        if period == "monthly":
            message = "Данные за текущий месяц."

        return message

    def metrika_telegram_subscribe(self, chat_id):

        if scheduler.get_job(str(chat_id)):
            self.metrika_telegram_unsubscribe(chat_id)
            return

        hours = ['19', '20', '21', '22', '23', '00']

        buttons = create_buttons_list(hours, lambda x: {'text': '{}:00'.format(x), 'callback_data': '/metrika_subscribe {}'.format(x)})

        send_keyboard('Выберите время:', buttons, chat_id)

        return

    def metrika_telegram_inline_subscribe(self, hour, chat_id):

        scheduler.add_job(self.metrika_telegram_daily, args=['today', chat_id] , trigger='cron', hour=hour, id=str(chat_id))

        if not self.db.metrika_subscribes.find_one({'chat_id': chat_id}):
            self.db.metrika_subscribes.insert_one({'chat_id': chat_id, 'time': hour})

        return

    def metrika_telegram_unsubscribe(self, chat_id):

        buttons = [[{'text': 'Выбрать другое время', 'callback_data': '/metrika_unsubscribe resubscribe'}],
                   [{'text': 'Отписаться', 'callback_data': '/metrika_unsubscribe'}]]

        data = self.db.metrika_subscribes.find_one({'chat_id': chat_id})

        if not data:
            send_text('Вы не подписаны на дайджест', chat_id)
            return

        hour = data.get('time')

        send_keyboard('Вы подписаны на ежедневный дайджест в {}:00'.format(hour), buttons, chat_id)

        return

    def metrika_telegram_inline_unsubscribe(self, chat_id):

        scheduler.remove_job(str(chat_id))
        self.db.metrika_subscribes.delete_one({'chat_id': chat_id})

        return
