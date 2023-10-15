import argparse
import logging
from dataclasses import dataclass
from datetime import datetime

import backoff
import requests
import telegram
from environs import Env
from telegram.constants import PARSEMODE_HTML

BACKOFF_EXP_EXCEPTIONS = (requests.ConnectionError, requests.ConnectTimeout,
                          requests.HTTPError)


@dataclass
class PollingConf:
    bot: telegram.Bot
    chat_id: int
    headers: dict
    url: str = 'https://dvmn.org/api/long_polling/'
    # Timestamp, начиная с которого подтягивать данные о проверках.
    # Хранится в конфиге, чтобы состояние не терялось при перезапуске поллинг-функции
    # в случае ошибок.
    timestamp: float = datetime.now().timestamp()
    timeout: int = 120


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
        level=logging.ERROR
    )
    logging.getLogger('backoff').addHandler(logging.StreamHandler())
    logging.getLogger('backoff').setLevel(logging.ERROR)

    conf = PollingConf(
        bot=telegram.Bot(token=tg_bot_token),
        chat_id=tg_chat_id,
        headers={'Authorization': f'Token {token}'},
        timeout=120,
    )
    start_polling(conf)


# Перезапуск функции при возникновении ошибок (https://github.com/litl/backoff):
# - При `ReadTimeout` перезапуск произойдёт через рандомное время в пределах 1 сек.
# - При ошибках из `BACKOFF_EXP_EXCEPTIONS` функция будет экспоненциально
#   увеличивать интервал между попытками при каждой последующей неудаче до тех пор,
#   пока взаимодействие с сервером не нормализуется.
# - При `KeyError` (ответ пришёл без нужных полей) также начнутся перезапуски по
#   экспоненте, но будет сделано только `max_tries` попыток.
@backoff.on_exception(backoff.constant, requests.ReadTimeout, interval=0, logger=None)
@backoff.on_exception(backoff.expo, BACKOFF_EXP_EXCEPTIONS)
@backoff.on_exception(backoff.expo, KeyError, max_tries=20)
def start_polling(conf: PollingConf):
    while True:
        resp = requests.get(
            conf.url,
            headers=conf.headers,
            # Timestamp указывается всегда, чтобы в случае сбоев сети с последующей
            # задержкой не пропустить новых оповещений.
            params={'timestamp': conf.timestamp},
            timeout=conf.timeout
        )
        resp.raise_for_status()
        reviews = resp.json()

        if reviews['status'] == 'found':
            attempts = reviews['new_attempts']

            for attempt in attempts:
                is_approved = not attempt['is_negative']
                title = attempt['lesson_title']
                lesson_url = attempt['lesson_url']

                msg = ''
                if is_approved:
                    msg = f'✅ Урок «<a href="{lesson_url}">{title}</a>» принят!'
                else:
                    msg = f'🛠 По уроку «<a href="{lesson_url}">{title}</a>» есть замечания.'

                conf.bot.send_message(
                    chat_id=conf.chat_id,
                    text=msg, parse_mode=PARSEMODE_HTML,
                    disable_web_page_preview=True,
                )

            conf.timestamp = datetime.now().timestamp()
            continue

        if reviews['status'] == 'timeout':
            conf.timestamp = reviews['timestamp_to_request']
            continue


if __name__ == '__main__':
    main()
