import logging

from configuration.globalcfg import URL
from .._common.functions import send_message, send_text, send_image, generate_hash, send_keyboard
from .GithubParser import GithubParser


class GithubModule:
    def __init__(self, db, redis):
        self.db = db
        self.redis = redis

    async def run_web(self, params):
        try:
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
            send_text(gh.get_output(), chat_id)

        except Exception as e:
            logging.error("Notifications module run_web error: {}".format(e))

    async def run_telegram(self, params):
        try:
            command_prefix = params['data']['command_prefix']
            payload = params['data']['payload']
            inline = params['data']['inline']

            if inline:
                if inline.startswith('/github_delete'):
                    repository_id = inline.split(" ")[-1]
                    chat_id = payload['chat']['id']
                    self.github_delete_repository(repository_id, chat_id)
            else:
                self.make_answer(payload)

        except Exception as e:
            logging.error("Notifications module run_telegram error: {}".format(e))

    def make_answer(self, message):
        try:
            command_prefix = message['text'].split(' ')[0]
            chat_id = message['chat']['id']

            if command_prefix.startswith("/help") or command_prefix.startswith("/github_help"):
                send_message({"cmd": "send_message",
                                            "message": self.github_telegram_help(chat_id),
                                            "chat_id": chat_id
                                            })
                return

            if command_prefix.startswith("/start") or command_prefix.startswith("/github_start"):
                self.github_telegram_start(chat_id)
                return

            if command_prefix.startswith("/stop") or command_prefix.startswith("/github_stop"):
                self.github_telegram_stop(chat_id)
                return

            send_text('%%i_dont_know_such_a_command%%', chat_id)

        except Exception as e:
            logging.error("Error while Github make_answer: {}".format(e))

    ############### MESSAGES ################

    def github_telegram_help(self, chat_id):
        msg = "Модуль для работы с сервисом GitHub.\n\n- Оповещения о новых Push-событиях\n- Оповещения о создании Pull-реквестов\n- Оповещения о создании Issues"

        logging.warning(chat_id)
        repositories = list(self.db.github_repositories.find({'chats': chat_id}))

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

    def github_telegram_start(self, chat_id):
        send_text("Чтобы подключить репозиторий, выполните три простых шага.\n", chat_id)
        send_image("1) Откройте настройки вашего репозитория", "images/github_start_step_1.jpg", chat_id)
        send_image("2) Зайдите в раздел Webhooks & services и нажмите кнопку Add Webhook",
                   "images/github_start_step_2.jpg", chat_id)

        token = self.get_chat_token(chat_id)
        c_uri = URL + "github/" + token
        msg = "3) Вставьте в поле Payload URL следующую ссылку.\n\n{}\n\n" \
              "В поле «Which events would you like to trigger this webhook?» \nвыберите \n" \
              "«Let me select individual events» и отметье следующие флажки: \n\n" \
              "- Issues\n- Pull request\n- Push\n\nНажмите на кнопку «Add Webhook»\n\n".format(c_uri)

        send_text(msg, chat_id)

    def github_telegram_stop(self, chat_id):

        repositories = list(self.db.github_repositories.find({'chats': chat_id}))

        if not len(repositories):
            send_text("У вас не подключено ни одного репозитория.", chat_id)
        else:
            buttons = [{'text': repository['name'],
                        'callback_data': "/github_delete {}".format(str(repository['id']))
                        } for repository in repositories
                       ]
            send_keyboard("Выберите репозиторий, который хотите отключить.\n", [buttons], chat_id)

    def github_delete_repository(self, repository_id, chat_id):
        repo = self.db.github_repositories.find_one({'id': int(repository_id), 'chats': chat_id})
        if not repo:
            return

        chats = repo['chats']
        chats.remove(chat_id)
        if repo:
            send_text("Репозиторий {} отключен.".format(repo['name']), chat_id)
            self.db.github_repositories.update_one({'_id': repo['_id']}, {'$set': {'chats': chats}})

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

    def get_chat_token(self, chat_id):
        """
            Return or generate new token (unique hash) for the chat
            :param chat_id: Telegram chat id (integer)
            :return: unique chat hash (as route)
        """
        chat = self.db.github_chats.find_one({'id': chat_id})
        if not chat:
            hash = generate_hash(size=8)
            self.db.github_chats.insert_one({'id': chat_id, 'hash': hash})
            return hash
        else:
            return chat['hash']

    def get_chat_id_by_hash(self, chat_hash):
        chat = self.db.github_chats.find_one({'hash': chat_hash})
        if not chat:
            return False
        else:
            return chat["id"]
