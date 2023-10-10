import argparse
import logging
from dataclasses import dataclass

import backoff
import requests
import telegram
from environs import Env
from telegram.constants import PARSEMODE_HTML


class DevmanValueError(ValueError):
    ...


LONG_POLLING_URL = 'https://dvmn.org/api/long_polling/'
BACKOFF_EXCEPTIONS = (requests.ReadTimeout, requests.ConnectionError,
                      requests.Timeout, ValueError, DevmanValueError)


@dataclass
class PollingConf:
    url: str
    bot: telegram.Bot
    chat_id: int
    headers: dict
    timeout: int = 60


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

    conf = PollingConf(
        url=LONG_POLLING_URL,
        bot=telegram.Bot(token=tg_bot_token),
        chat_id=tg_chat_id,
        headers={'Authorization': f'Token {token}'},
    )
    start_polling(conf)


@backoff.on_exception(backoff.expo, BACKOFF_EXCEPTIONS)
def start_polling(conf: PollingConf, params=None):
    resp = requests.get(conf.url, headers=conf.headers, timeout=conf.timeout)
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

        conf.bot.send_message(
            chat_id=conf.chat_id,
            text=msg, parse_mode=PARSEMODE_HTML,
            disable_web_page_preview=True,
        )

        return start_polling(conf)

    if reviews['status'] == 'timeout':
        params = {
            'timestamp': reviews['timestamp_to_request']
        }
        return start_polling(conf, params=params)

    msg = f'Bad reviews status: {reviews["status"]}'
    logging.error(msg)
    raise DevmanValueError(msg)


if __name__ == '__main__':
    main()
