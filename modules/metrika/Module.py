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
        self.chat_id = ''

    def run_telegram(self, params):
        try:
            payload = params['data']['payload']
            self.chat_id = params['data']['payload']['chat']['id']
            command_prefix = params['data']['command_prefix']

            if not params['data']['inline']:
                self.make_answer(command_prefix, payload)
            else:
                self.process_inline_command(command_prefix, payload)

        except Exception as e:
            logging.error("Metrika module run_telegram error: {}".format(e))

    def run_web(self, params):
        try:
            access_token = params['data'].get("access_token", "")
            self.chat_id = params['data'].get('chat_id', '')
            metrika_api = MetrikaAPI(access_token, '', self.chat_id)
            login = metrika_api.get_login(access_token)

            logging.debug("run_web with params: {} {}".format(access_token, self.chat_id))

            if not self.db.metrika_tokens.find_one({'access_token': access_token, 'chat_id': self.chat_id}):
                self.db.metrika_tokens.insert_one({'id': generate_hash(12),
                                                   'chat_id': self.chat_id,
                                                   'access_token': access_token,
                                                   'login': login})

            self.metrika_telegram_available()

        except Exception as e:
            logging.error("Metrika module run_web error: {}".format(e))

    def make_answer(self, command_prefix, message):
        try:
            if command_prefix == "/help":
                send_text(self.metrika_telegram_help(), self.chat_id)
                return

            if command_prefix == "/settings" or command_prefix == "/metrika":
                self.metrika_telegram_settings()
                return

            if command_prefix == "/start" or command_prefix == "/add":
                self.metrika_telegram_start()
                return

            if command_prefix == "/available":
                self.metrika_telegram_available()
                return

            if command_prefix == "/counters":
                self.metrika_telegram_counters()
                return

            if command_prefix == "/access":
                self.metrika_telegram_access()
                return

            if command_prefix == "/stop":
                self.metrika_telegram_stop()
                return

            if command_prefix == "/today":
                self.metrika_telegram_daily("today")
                return

            if command_prefix == "/weekly":
                self.metrika_telegram_daily("weekly")
                return

            if command_prefix == "/monthly":
                self.metrika_telegram_daily("monthly")
                return

            if command_prefix == "/subscribe":
                self.metrika_telegram_subscribe()
                return

            if command_prefix == "/unsubscribe":
                self.metrika_telegram_unsubscribe()
                return

            Telegram.unknown_command(self.chat_id)

        except Exception as e:
            logging.error("Error while Metrika make_answer: {}".format(e))

    def process_inline_command(self, command_prefix, message):
        try:

            if command_prefix == "/help":
                send_text(self.metrika_telegram_help(), self.chat_id)
                return

            if command_prefix == "/start":
                self.metrika_telegram_start()
                return

            if command_prefix == "/available":
                self.metrika_telegram_available()
                return

            if command_prefix == "/counters":
                self.metrika_telegram_counters()
                return

            if command_prefix == "/stop":
                self.metrika_telegram_stop()
                return

            if command_prefix == "/subscriptions":
                self.metrika_telegram_subscribe()
                return

            if command_prefix == "/access":
                self.metrika_telegram_access()
                return

            if command_prefix == "/logout":
                login = message['text'].split(' ')[1]
                self.metrika_telegram_logout(login)
                return

            if command_prefix == "/add_counter":

                data = message['text'].split(' ')
                logging.debug(data)

                self.metrika_telegram_add(data[1], data[2])

            if command_prefix == "/del_counter":
                data = message['text'].split(' ')
                self.metrika_telegram_del(data[1])

            if command_prefix == "/subscribe":
                hour = message['text'].split()[1]
                self.metrika_telegram_inline_subscribe(hour)

                data = self.db.metrika_subscriptions.find_one({'chat_id': self.chat_id})

                if not data:
                    self.db.metrika_subscriptions.insert_one({'chat_id': self.chat_id, 'time': hour})
                elif data.get('time') != hour:
                    self.db.metrika_subscriptions.find_and_modify(query={'chat_id': self.chat_id},
                                                                  update={"$set": {'time': hour}})

                send_text('Вы успешно подписались на ежедневный дайджест в {}:00'.format(hour), self.chat_id)

            if command_prefix == "/unsubscribe":
                command = message['text'].split()

                if len(command) > 1:
                    self.metrika_telegram_subscribe(True)
                else:
                    self.metrika_telegram_inline_unsubscribe()

        except Exception as e:
            logging.error("Error while Metrika process_inline_command: {}".format(e))

    ### MESSAGES ###

    def metrika_telegram_help(self):
        msg = "Этот модуль поможет вам следить за статистикой сайта. Возможности модуля: \n\n" \
              "- моментальное получение текущих значений счетчиков (DAU, просмотры, источники) за период (день, неделя, месяц)\n" \
              "- уведомление о достижении целей (например, бот сообщит о достижении показателя в 10k уникальных посетителей)\n\n"

        msg += "/metrika_settings - перечень команд\n" \
               "/metrika_add - добавление нового пользователя Яндекс.Метрика\n" \
               "/metrika_subscriptions - настройка ежедневных отчётов\n" \
               "/metrika_stop - отключение счетчиков\n" \
               "/metrika_counters - список подключенных счётчиков\n" \
               "/metrika_access - отключение пользователей от чата"

        return msg

    def metrika_telegram_start(self):

        msg = "Для подключения счетчика, вам нужно авторизовать бота. Для этого перейдите по ссылке и подтвердите доступ:"

        button = [[{
            'text': 'Авторизовать бота',
            'url':  "https://oauth.yandex.ru/authorize?response_type=code&client_id={}&state={}".format(
                    self.settings['ID'],
                    self.chat_id
               )
        }]]
        send_keyboard(msg, button, self.chat_id)

    def metrika_telegram_settings(self):
        buttons = [[{
                'text': 'Добавить пользователя',
                'callback_data': '/metrika_start'
            }],
            [{
                'text': 'Добавить счетчик',
                'callback_data': '/metrika_available'
            }],
            [{
                'text': 'Регулярные отчеты',
                'callback_data': '/metrika_subscriptions'
            }],
            [{
                'text': 'Удалить счетчик',
                'callback_data': '/metrika_stop'
            }],
            [{
                'text': 'Подключенные счетчики',
                'callback_data': '/metrika_counters'
            }],
            [{
                'text': 'Управление доступом',
                'callback_data': '/metrika_access'
            }],
            [{
                'text': 'Помощь',
                'callback_data': '/metrika_help'
            }]]

        send_keyboard('Действия:', buttons, self.chat_id)

    def metrika_telegram_available(self):

        tokens = list(self.db.metrika_tokens.find({'chat_id': str(self.chat_id)}))

        users = []

        for token in tokens:
            users.append({'counters': self.get_counters(token, "start"),
                          'login': MetrikaAPI.get_login(token['access_token'])})

        buttons = []

        for user in users:

            for counter in user['counters']:
                if not self.db.metrika_counters.find_one({'chat_id': self.chat_id,
                                                          'counter_id': counter['id']}):
                    buttons.append([{
                        'text': counter['name'],
                        'callback_data': '/metrika_add_counter {} {}'.format(counter['id'], user['login'])
                    }])

        if len(buttons) == 0:
            send_text('Доступных для подключения счетчиков не осталось', self.chat_id)
        else:
            send_keyboard('Выберите счетчик для подключения', buttons, self.chat_id)

    def metrika_telegram_counters(self):

        counters = list(self.get_chat_counters())

        if not len(counters):
            send_text('Подключенных счетчиков нет.\n\nЧтобы подключить доступные счетчики, используйте /metrika_available', self.chat_id)
            return

        users = {}
        for counter in counters:
            login = counter.get('login')
            counter_name = counter.get('counter_name')
            if login in users:
                users[login].append(counter_name)
            else:
                users[login] = [counter_name]

        message = 'Подключенные счетчики:\n\n'
        for login in users.keys():
            message += '<b>@{}</b>\n'.format(login)
            for counter in users[login]:
                message += '{}\n'.format(counter)
            message += '\n'

        message += '\nЧтобы удалить счетчик, используйте команду /metrika_stop\n\n'+\
                   'Чтобы отключить все счетчики пользователя, используйте /metrika_access'
        send_text(message, self.chat_id, 'HTML')


    def metrika_telegram_stop(self):
        msg = ""

        counters = list(self.get_chat_counters())
        if not len(counters):
            send_text("Подключенных счетчиков не найдено.", self.chat_id)
            return

        buttons = []
        for counter in counters:
            buttons.append([{
                'text': counter['counter_name'],
                'callback_data': '/metrika_del_counter {}'.format(counter['counter_id'])
            }])


        send_keyboard("Выберите счетчик, который хотите отключить.\n",
                      buttons,
                      self.chat_id)

    def metrika_telegram_access(self):
        users = list(self.db.metrika_tokens.find({'chat_id': str(self.chat_id)}))

        if not len(users):
            send_text('Не авторизовано ни одного пользователя\n\nИспользуйте /metrika_add для авторизации', self.chat_id)
            return

        buttons = []
        for user in users:
            buttons.append([{
                'text': '@{}'.format(user['login']),
                'callback_data': '/metrika_logout {}'.format(user['login'])
            }])



        send_keyboard('Выберите пользователя, которого хотите отключить:', buttons, self.chat_id)

    def metrika_telegram_logout(self, login):
        self.db.metrika_tokens.delete_one({'chat_id': str(self.chat_id), 'login': login})
        self.db.metrika_counters.delete_many({'chat_id': self.chat_id, 'login': login})

        send_text('Пользователь <b>@{}</b> и его счетчики успешно отключены'.format(login), self.chat_id, 'HTML')

    def metrika_telegram_add(self, counter_id, login):

        counter = self.db.metrika_counters.find_one({'chat_id': self.chat_id, 'counter_id': counter_id})
        if counter:
            send_text("Счетчик <b>{}</b> уже прикреплен к данному чату.".format(counter['counter_name']), self.chat_id, 'HTML')
            return

        token = self.db.metrika_tokens.find_one({'chat_id': str(self.chat_id), 'login': login})

        try:
            api = MetrikaAPI(token['access_token'], counter_id, self.chat_id)
            counter_name = api.get_counter_name()

        except Exception as e:
            send_text('Не могу получить данные о счетчике :(', self.chat_id)
            return

        self.db.metrika_counters.insert_one({
            'chat_id': self.chat_id,
            'counter_id': counter_id,
            'counter_name': counter_name,
            'login': login
        })

        send_text("Готово! Счетчик <b>{}</b> успешно подключен.".format(counter_name), self.chat_id, 'HTML')
        self.metrika_telegram_help()

    def metrika_telegram_del(self, counter_id):
        counter = self.db.metrika_counters.find_one({'chat_id': self.chat_id, 'counter_id': counter_id})
        result = self.db.metrika_counters.delete_one({'chat_id': self.chat_id, 'counter_id': counter_id})

        send_text("Счетчик <b>{}</b> успешно откреплен от данного чата.".format(counter.get('counter_name')), self.chat_id, 'HTML')

    def metrika_telegram_daily(self, cmd):
        tokens = list(self.db.metrika_tokens.find({'chat_id': str(self.chat_id)}))
        message = "%s\n\n" % self.stats(cmd)

        if not len(tokens):
            message = 'Не авторизован ни один пользователь\n\nДля авторизации используйте /metrika_add'

        for token in tokens:
            try:
                counters = list(self.db.metrika_counters.find({'chat_id': self.chat_id, 'login': token['login']}))

                if not len(counters):
                    message = 'Не подключен ни один счетчик\n\nДля подключения доступных счетчиков используйте /metrika_available.'


                for counter in counters:
                    metrikaAPI = MetrikaAPI(token['access_token'], counter['counter_id'], self.chat_id)
                    result = metrikaAPI.get_visit_statistics(cmd)
                    if result:
                        print(result)
                        users, hits = result
                        message += "%s:\n%d уникальных посетителей\n%d просмотров\n\n" % (counter['counter_name'],
                                                                                      users, hits)

            except Exception as e:
                logging.warning("Metrika API exception: %s" % e)

        send_text(message, self.chat_id)

    ### SUPPORT ###

    def get_counters(self, token, cmd=None):
        metrikaAPI = MetrikaAPI(token['access_token'], '', token['chat_id'])
        return metrikaAPI.get_counters()

        '''
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
        '''
        return buttons

    def get_chat_counters(self):

        counters = self.db.metrika_counters.find({'chat_id': self.chat_id})

        return counters

        """
        buttons = []
        buttons_row = []
        for counter in metrikas:
            cache_link = generate_hash(18)
            buttons_row.append({
                'text': counter['counter_name'],
                'callback_data': "/metrika_del_counter #{}#{}".format("stop", cache_link)
            })
            self.redis.hmset(cache_link, {'counter_id': counter['counter_id'],
                                          'chat_id': self.chat_id,
                                          'cmd': "stop",
                                          'name': counter['counter_name']})

            if len(buttons_row) == 2:
                buttons.append(buttons_row[:])
                buttons_row = []
        if len(buttons_row):
            buttons.append(buttons_row[:])
        return buttons
        """
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

    def metrika_telegram_subscribe(self, resubscribe=False):

        if scheduler.get_job(str(self.chat_id)) and not resubscribe:
            self.metrika_telegram_unsubscribe(self.chat_id)
            return

        hours = ['19', '20', '21', '22', '23', '00']

        buttons = create_buttons_list(hours, lambda x: {'text': '{}:00'.format(x), 'callback_data': '/metrika_subscribe {}'.format(x)})

        send_keyboard('Выберите время:', buttons, self.chat_id)

        return

    def metrika_telegram_inline_subscribe(self, hour, chat_id=False):

        if not chat_id:
            chat_id = self.chat_id

        scheduler.add_job(self.metrika_telegram_daily, args=['today'], trigger='cron', hour=hour, id=str(chat_id), replace_existing=True)

        return

    def metrika_telegram_unsubscribe(self):

        buttons = [[{'text': 'Выбрать другое время', 'callback_data': '/metrika_unsubscribe resubscribe'}],
                   [{'text': 'Отписаться', 'callback_data': '/metrika_unsubscribe'}]]

        data = self.db.metrika_subscriptions.find_one({'chat_id': self.chat_id})

        if not data:
            send_text('Вы не подписаны на дайджест', self.chat_id)
            return

        hour = data.get('time')

        send_keyboard('Вы подписаны на ежедневный дайджест в {}:00'.format(hour), buttons, self.chat_id)

        return

    def metrika_telegram_inline_unsubscribe(self):

        if scheduler.get_job(str(self.chat_id)):
           scheduler.remove_job(str(self.chat_id))
           send_text('Вы отписались от дайджеста', self.chat_id)
        else:
            send_text('Вы не подписаны на дайджест', self.chat_id)

        self.db.metrika_subscriptions.delete_one({'chat_id': self.chat_id})

        return
