import asyncio
import logging
import random
import string
from urllib.parse import urlencode

import requests
import time

from configuration.globalcfg import TELEGRAM_API_TOKEN


def generate_hash(size=6, chars=string.ascii_uppercase + string.digits):
    """
    Generate unique string for using as GitHub callback URI (route)
    :param size: size in symbols
    :param chars: letters used
    :return: string token
    """
    return ''.join(random.SystemRandom().choice(chars) for _ in range(size))


def send_to_chat(message, chat_id, api_token=TELEGRAM_API_TOKEN, disable_web_page_preview=True, parse_mode='HTML'):
    """
    Sends message to the chat with chat_id
    :param message: Text
    :param chat_id: Int
    :param api_token: Token for Telegram access (https://core.telegram.org/bots#botfather)
    :param disable_web_page_preview: Bool
    :param parse_mode: Text ('HTML' or 'Markdown')
    :return: {True}
    """

    data = {
        'text': message,
        'chat_id': chat_id,
        'disable_web_page_preview': 'true' if disable_web_page_preview else 'false',
        'parse_mode': parse_mode
    }

    query = 'https://api.telegram.org/bot%s/sendMessage?%s' % (api_token, urlencode(data))
    logging.info("message send to '{}': [{}]".format(chat_id, query))

    return requests.get(query)


def send_image_to_chat(caption, image_filename, chat_id, api_token=TELEGRAM_API_TOKEN):
    """
    Sends message to the chat with chat_id
    :param message: Text
    :param chat_id: Int
    :param api_token: Token for Telegram access (https://core.telegram.org/bots#botfather)
    :param disable_web_page_preview: Bool
    :return: {True}
    """

    data = {
        'caption': caption,
        'chat_id': chat_id,
    }

    files = {
        'photo': open(image_filename, 'rb')
    }

    query = 'https://api.telegram.org/bot%s/sendPhoto?%s' % (api_token, urlencode(data))
    logging.info("send message to '%s': [%s]" % (chat_id, query))

    return requests.post(query, files=files)


def send_object_to_chat(text, reply_markup, chat_id, api_token=TELEGRAM_API_TOKEN):
    """
    Sends message to the chat with chat_id
    :param message: Text
    :param chat_id: Int
    :param api_token: Token for Telegram access (https://core.telegram.org/bots#botfather)
    :param disable_web_page_preview: Bool
    :return: {True}
    """

    data = {
        'chat_id': chat_id,
        'text': text,
    }

    query = 'https://api.telegram.org/bot%s/sendMessage?%s' % (api_token, urlencode(data))
    logging.info("send message to '%s': [%s]" % (chat_id, query))

    return requests.post(query, json={'reply_markup': reply_markup})


def register_commands(module, cmds, global_commands):
    for cmd in cmds:
        command_token = "/{}".format(cmd)
        if command_token not in global_commands:
            global_commands[command_token] = module

        command_token = "/{}_{}".format(module, cmd)
        if command_token not in global_commands:
            global_commands[command_token] = module


def profile_update(db, user_id, model):
    user = db.users.find_one({'id': user_id})
    if not user:
        model['time'] = time.time()
        db.users.insert_one(model)
    else:
        db.users.update_one({'id': user_id}, {'$set': {'time': time.time()}})


def create_buttons_list(arr, func=None):
    buttons = []
    buttons_row = []
    for element in arr:
        if func:
            imp = func(element)
        else:
            imp = element
        buttons_row.append(imp)
        if len(buttons_row) == 2:
            buttons.append(buttons_row[:])
            buttons_row = []
    if len(buttons_row):
        buttons.append(buttons_row[:])
    return buttons
