import json
import logging
import random
import string


def generate_hash(size=6, chars=string.ascii_uppercase + string.digits):
    """
    Generate unique string for callback URI (route)
    :param size: length in symbols
    :param chars: alphabet
    :return: string token
    """
    return ''.join(random.SystemRandom().choice(chars) for _ in range(size))


def send_message(params):
    from core.telegram import send_message
    print(params)
    send_message(params)


def send_text(message, chat_id):
    send_message({"cmd": "send_message", "message": message, "chat_id": chat_id})


def send_image(caption, image_filename, chat_id):
    try:
        image = "modules/github/" + image_filename
    except Exception as e:
        logging.warning("Send_image. Image file exception: [{}]".format(e))
        return False
    else:
        send_message({"cmd": "send_image", "caption": caption, "image_filename": image, "chat_id": chat_id})


def send_keyboard(message, buttons, chat_id):
    send_message({"cmd": "send_keyboard", "message": message,
                  "buttons": json.dumps({'inline_keyboard': buttons}), "chat_id": chat_id})
