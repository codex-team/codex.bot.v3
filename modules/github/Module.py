import logging
import requests

from configuration.globalcfg import URL
from core.telegram import Telegram
from .._common.functions import send_text, send_image, generate_hash, send_keyboard
from .GithubParser import GithubParser
from modules.github.authcfg import APP, AUTH_SCOPE


class GithubModule:
    def __init__(self, db, redis):
        self.db = db
        self.redis = redis
        self.chat_id = ''

    async def run_web(self, params):
        try:

            if params['type'] == 1:
                chat_hash = params['data']['chat_hash']
                headers = params['data']['headers']
                payload = params['data']['payload']

                # If we've got an unexpected chat_id
                if not self.check_chat(chat_hash):
                    logging.warning("Github. Callback. Warning: chat {} does not exist.".format(chat_hash))
                    return

                if headers.get('X-GitHub-Event', '') == "ping":
                    self.ping_event(payload['repository'], chat_hash)
                    logging.warning("Github. Ping event sent. chat={}, repo={}".format(chat_hash, payload['repository']))
                    return

                gh = GithubParser(payload)
                gh.process()
                chat_id = self.get_chat_id_by_hash(chat_hash)
                send_text(gh.get_output(), chat_id, parse_mode='HTML')
                return

            if params['type'] == 2:
                user_hash = params['data']['user_hash']
                chat_hash = params['data']['chat_hash']
                access_token = params['data']['access_token']

                chat_id = self.get_chat_id_by_hash(chat_hash)

                if not self.db.telegram_users.find_one({'hash': user_hash}):
                    logging.warning("Github. Auth callback. Warning: user {} does not exist.".format(user_hash))
                    return

                if not self.db.github_users.find_one({'hash': user_hash}):
                    self.db.github_users.insert_one({'hash': user_hash, 'token': access_token})
                    send_text("Аккаунт успешно привязан", chat_id)
                else:
                    send_text("Ваш аккаунт уже был привязан", chat_id)

        except Exception as e:
            logging.error("Notifications module run_web error: {}".format(e))

    async def run_telegram(self, params):
        try:
            command_prefix = params['data']['command_prefix']
            payload = params['data']['payload']
            inline = params['data']['inline']
            self.chat_id = payload['chat'].get('id', '')

            if inline:
                if command_prefix == '/github_delete':
                    repository_id = inline.split(" ")[-1]
                    self.github_delete_repository(repository_id)
            else:
                self.make_answer(command_prefix, payload)

        except Exception as e:
            logging.error("Notifications module run_telegram error: {}".format(e))

    def make_answer(self, command_prefix, message):
        try:
            if command_prefix == "/help":
                send_text(self.github_telegram_help(), self.chat_id)
                return

            if command_prefix == "/start":
                self.github_telegram_start()
                return

            if command_prefix == "/stop":
                self.github_telegram_stop()
                return

            if command_prefix == "/auth":
                self.github_telegram_auth(message['from'], message['chat'])
                return

            Telegram.unknown_command(self.chat_id)

        except Exception as e:
            logging.error("Error while Github make_answer: {}".format(e))

    ############### MESSAGES ################

    def github_telegram_help(self):
        msg = "Модуль для работы с сервисом GitHub.\n\n- Оповещения о новых Push-событиях\n- Оповещения о создании Pull-реквестов\n- Оповещения о создании Issues"

        logging.warning(self.chat_id)
        repositories = list(self.db.github_repositories.find({'chats': self.chat_id}))

        if not repositories:
            msg += "\n\nВ данный момент модуль не активирован.\n\nДля настройки модуля, используйте команду /github_start"
        else:
            msg += "\n\nПодключенные репозитории.\n\n"
            for repository in repositories:
                msg += "{}\n".format(repository["name"])
            msg += "\nДля отключения репозитория используйте команду /github_stop\n" \
                   "Подключить еще один репозиторий можно с помощью команды /github_start\n\n" \
                   "Меню модуля: /github_help"
        return msg

    def github_telegram_start(self):
        send_text("Чтобы подключить репозиторий, выполните три простых шага.\n", self.chat_id)
        send_image("1) Откройте настройки вашего репозитория", "images/github_start_step_1.jpg", self.chat_id)
        send_image("2) Зайдите в раздел Webhooks & services и нажмите кнопку Add Webhook",
                   "images/github_start_step_2.jpg", self.chat_id)

        token = self.get_chat_token()
        c_uri = URL + "github/" + token
        msg = "3) Вставьте в поле Payload URL следующую ссылку.\n\n{}\n\n" \
              "В поле «Which events would you like to trigger this webhook?» \nвыберите \n" \
              "«Let me select individual events» и отметье следующие флажки: \n\n" \
              "- Issues\n- Pull request\n- Push\n\nНажмите на кнопку «Add Webhook»\n\n".format(c_uri)

        send_text(msg, self.chat_id)

    def github_telegram_stop(self):

        repositories = list(self.db.github_repositories.find({'chats': self.chat_id}))

        if not len(repositories):
            send_text("У вас не подключено ни одного репозитория.", self.chat_id)
        else:
            buttons = [{'text': repository['name'],
                        'callback_data': "/github_delete {}".format(str(repository['id']))
                        } for repository in repositories
                       ]
            send_keyboard("Выберите репозиторий, который хотите отключить.\n", [buttons], self.chat_id)

    def github_delete_repository(self, repository_id):
        repo = self.db.github_repositories.find_one({'id': int(repository_id), 'chats': self.chat_id})
        if not repo:
            return

        chats = repo['chats']
        chats.remove(self.chat_id)
        if repo:
            send_text("Репозиторий {} отключен.".format(repo['name']), self.chat_id)
            self.db.github_repositories.update_one({'_id': repo['_id']}, {'$set': {'chats': chats}})

    def github_telegram_auth(self, user, chat):

        user_hash = generate_hash()
        chat_type = chat['type']

        if chat_type != 'private':
            send_text('Привязать github аккаунт возможно только в личном чате с ботом', self.chat_id)
            return

        chat_hash = self.get_chat_token()

        if not self.db.telegram_users.find_one({'id': user['id']}):
            self.db.telegram_users.insert_one({'id': user['id'], 'hash': user_hash})
        else:
            user_hash = self.db.telegram_users.find_one({'id': user['id']})['hash']

        send_text('Чтобы привязать аккаунт, пройдите по ссылке: \n\n'+
                  'https://github.com/login/oauth/authorize?'+
                  'client_id={}&scope={}&state={}&redirect_uri={}github/auth/{}'.format(APP['CLIENT_ID'],
                                                                                        ','.join(AUTH_SCOPE),
                                                                                        chat_hash,
                                                                                        URL,
                                                                                        user_hash), self.chat_id)

    ############### EVENTS ################

    def ping_event(self, repository, chat_hash):
        try:
            repo = self.get_repository(repository["id"])
            chat_id = self.get_chat_id_by_hash(chat_hash)
            if not repo:
                self.db.github_repositories.insert_one({
                    'id': repository["id"],
                    'name': repository["name"],
                    'chats': [chat_id, ]
                })
                send_text("Репозиторий {} был подключен".format(repository["name"]), chat_id)

            elif chat_id not in repo['chats']:
                chats = repo['chats']
                chats.append(chat_id)
                self.db.github_repositories.update_one({'_id': repo['_id']}, {'$set': {'chats': chats}})
                send_text("Репозиторий {} был подключен".format(repository["name"]), chat_id)

            else:
                pass

        except Exception as e:
            logging.error("Github. Ping event. Error: [{}]".format(e))

    ############### HELPERS ################

    def check_chat(self, chat_hash):
        return self.db.github_chats.find_one({'hash': chat_hash})

    def get_repository(self, repository_id):
        return self.db.github_repositories.find_one({'id': repository_id})

    def get_chat_token(self):
        """
            Return or generate new token (unique hash) for the chat
            :return: unique chat hash (as route)
        """
        chat = self.db.github_chats.find_one({'id': self.chat_id})
        if not chat:
            hash = generate_hash(size=8)
            self.db.github_chats.insert_one({'id': self.chat_id, 'hash': hash})
            return hash
        else:
            return chat['hash']

    def get_chat_id_by_hash(self, chat_hash):
        chat = self.db.github_chats.find_one({'hash': chat_hash})
        if not chat:
            return False
        else:
            return chat["id"]
