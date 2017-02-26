import json
import logging
import random
import string

from components.simple import send_to_chat, send_image_to_chat, send_object_to_chat
from core.telegram import send_message


def generate_hash(size=6, chars=string.ascii_uppercase + string.digits):
    """
    Generate unique string for callback URI (route)
    :param size: length in symbols
    :param chars: alphabet
    :return: string token
    """
    return ''.join(random.SystemRandom().choice(chars) for _ in range(size))


def send_text(message, chat_id, parse_mode=''):
    send_to_chat(message=message, chat_id=chat_id, parse_mode=parse_mode)


def send_image(caption, image_filename, chat_id):
    try:
        image = "modules/github/" + image_filename # TODO: Non-universal
    except Exception as e:
        logging.warning("Send_image. Image file exception: [{}]".format(e))
        return False
    else:
        result = send_image_to_chat(caption=caption, image_filename=image, chat_id=chat_id)


def send_keyboard(message, buttons, chat_id):
    send_object_to_chat(text=message,
                        reply_markup=json.dumps({'inline_keyboard': buttons}),
                        chat_id=chat_id
                        )
