import asyncio
import json
import logging

from aiohttp import web

from components.simple import profile_update
from configuration.globalcfg import COMMANDS, OBJECTS, BOT_NAME


async def telegram_callback(request):
    """
    Process messages from telegram bot
    :return:
    """

    from core.telegram import Telegram

    try:
        data = await request.text()
        update = json.loads(data)
        logging.info(update)

        request.app['db'].log_telegram_messages.insert_one(update)

        inline = False
        if 'callback_query' in update:
            message = update['callback_query']['message']
            inline = update['callback_query']['data']
            message['text'] = inline
        else:
            message = update['message']

        entities = message['entities']
        commands = list(map(lambda x: message['text'][x['offset']:x['offset']+x['length']], entities))
        chat_id = message['chat']['id']
        user_id = message['from']['id']
        mentioned = False

        profile_update(request.app['db'], user_id, message['from'])

        if not message['text'].startswith("/") and BOT_NAME not in message['text']:
            return web.Response(text='NOT OK')

        if BOT_NAME in message['text']:
            mentioned = True
            message['text'] = message['text'].replace(BOT_NAME, "")

        command_prefix = message['text'].split(' ')[0]
        module = COMMANDS.get(command_prefix)

        logging.info("Telegram. Got cmd={}, module={}".format(command_prefix, module))

        if not module:
            if mentioned:
                Telegram.unknown_command(chat_id)
            else:
                # Ignore unknown messages without @BOT_NAME
                pass
        elif module == "telegram":
            Telegram.make_answer(message)
        else:
            await OBJECTS[module].run_telegram({"module": module,
                                 "url": request.rel_url.path,
                                 "type": 0,  # Telegram message
                                 "data": {
                                     "command_prefix": command_prefix,
                                     "payload": message,
                                     "inline": inline
                                 },
                                 "commands": commands
                                 })
    except Exception as e:
        logging.warning("Message process error: [%s]" % e)

    return web.Response(text='OK')

async def slack_callback(request):
    """
    Process messages from telegram bot
    :return:
    """

    try:
        data = await request.text()

        # request.app['db'].log_telegram_messages.insert_one(update)
        logging.info(data)
        #
        # if 'challenge' in update:
        #     return web.Response(text=update['challenge'])
        #
        # chat_id = update['event']['channel']
        # message = update['event']['text']
        # user_id = update['event']['user']

        return web.Response(text="OK")

    except Exception as e:
        logging.error(e)
