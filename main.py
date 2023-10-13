import argparse
import logging

import backoff
import requests
import telegram
from environs import Env
from telegram.constants import PARSEMODE_HTML


class DevmanValueError(ValueError):
    ...


LONG_POLLING_URL = 'https://dvmn.org/api/long_polling/'
BACKOFF_EXCEPTIONS = (requests.ReadTimeout, requests.ConnectionError,
                      requests.Timeout, DevmanValueError)


def main():
    env = Env()
    env.read_env()
    token = env.str('DEVMAN_API_TOKEN')
    tg_bot_token = env.str('TG_BOT_API_TOKEN')

    parser = argparse.ArgumentParser(
        prog='Send Devman lessons status to Telegram.')
    parser.add_argument('chat_id', type=int,
                        help="Telegram Chat ID (a 9-digit number).")
    args = parser.parse_args()
    tg_chat_id = args.chat_id

    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )

    start_polling(
        url=LONG_POLLING_URL,
        bot=telegram.Bot(token=tg_bot_token),
        chat_id=tg_chat_id,
        headers={'Authorization': f'Token {token}'},
    )


@backoff.on_exception(backoff.expo, BACKOFF_EXCEPTIONS)
def start_polling(url, bot, chat_id, headers, timeout=60):
    params = None
    while True:
        resp = requests.get(url, headers=headers,
                            params=params, timeout=timeout)
        resp.raise_for_status()
        reviews = resp.json()

        if 'status' not in reviews:
            msg = 'Reviews status not found in server response.'
            logging.error(msg)
            raise DevmanValueError(msg)

        if reviews['status'] == 'found':
            attempt = reviews['new_attempts'][0]

            is_approved = not attempt['is_negative']
            title = attempt['lesson_title']
            url = attempt['lesson_url']

            msg = ''
            if is_approved:
                msg = f'✅ Урок «<a href="{url}">{title}</a>» принят!'
            else:
                msg = f'🛠 По уроку «<a href="{url}">{title}</a>» есть замечания.'

            bot.send_message(
                chat_id=chat_id,
                text=msg, parse_mode=PARSEMODE_HTML,
                disable_web_page_preview=True,
            )

            params = None
        elif reviews['status'] == 'timeout':
            params = {
                'timestamp': reviews['timestamp_to_request']
            }
            continue
        else:
            msg = f'Bad reviews status: {reviews["status"]}'
            logging.error(msg)
            raise DevmanValueError(msg)


if __name__ == '__main__':
    main()
