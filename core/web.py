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

        chat_id = message['chat']['id']
        user_id = message['from']['id']

        profile_update(request.app['db'], user_id, message['from'])

        if not message['text'].startswith("/") and BOT_NAME not in message['text']:
            return web.Response(text='OK')

        message['text'] = message['text'].replace(BOT_NAME, "")
        command_prefix = message['text'].split(' ')[0]
        module = COMMANDS.get(command_prefix)

        logging.info("Telegram. Got cmd={}, module={}".format(command_prefix, module))

        if not module:
            Telegram.unknown_command(chat_id)
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
                                 }
                                 })
    except Exception as e:
        logging.warning("Message process error: [%s]" % e)

    return web.Response(text='OK')
