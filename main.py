import logging
from dataclasses import dataclass
import backoff
import requests
from environs import Env
import telegram

LONG_POLLING_URL = 'https://dvmn.org/api/long_polling/'
BACKOFF_EXCEPTIONS = (requests.ReadTimeout, requests.ConnectionError,
                      requests.Timeout)


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
    tg_chat_id = env.int('TG_CHAT_ID')

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
def start_polling(poller: PollingConf, params=None):
    resp = requests.get(poller.url, headers=poller.headers,
                        timeout=poller.timeout)
    resp.raise_for_status()
    reviews = resp.json()

    if 'status' not in reviews:
        msg = 'Reviews status not found in server response.'
        logging.error(msg)
        raise ValueError(msg)

    if reviews['status'] == 'found':
        print('Found!', reviews)
        poller.bot.send_message(chat_id=poller.chat_id,
                                text=f'Found! {reviews}')
        return start_polling(poller)

    if reviews['status'] == 'timeout':
        print('Timeout!', reviews)
        params = {
            'timestamp': reviews['timestamp_to_request']
        }
        return start_polling(poller, params=params)

    msg = f'Bad reviews status: {reviews["status"]}'
    logging.error(msg)
    raise ValueError(msg)


if __name__ == '__main__':
    main()
