import logging
import backoff
import requests
from environs import Env
import telegram

LONG_POLLING_URL = 'https://dvmn.org/api/long_polling/'


def main():
    env = Env()
    env.read_env()
    token = env.str('DEVMAN_API_TOKEN')
    tg_bot_token = env.str('TG_BOT_API_TOKEN')
    tg_chat_id = env.str('TG_CHAT_ID')

    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )

    bot = telegram.Bot(token=tg_bot_token)

    headers = {
        'Authorization': f'Token {token}'
    }
    start_polling(bot, tg_chat_id, LONG_POLLING_URL, headers=headers)


backoff_exceptions = (requests.ReadTimeout, requests.ConnectionError,
                      requests.Timeout)


@backoff.on_exception(backoff.expo, backoff_exceptions)
def start_polling(bot: telegram.Bot, chat_id, url, headers, params=None, timeout=60):
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    reviews = resp.json()

    if reviews['status'] == 'found':
        print('Found!', reviews)
        bot.send_message(chat_id=chat_id, text=f'Found! {reviews}')
        return start_polling(bot, chat_id, url, headers, params, timeout)

    if reviews['status'] == 'timeout':
        print('Timeout!', reviews)
        timestamp = reviews['timestamp_to_request']
        params = {
            'timestamp': timestamp
        }
        return start_polling(bot, chat_id, url, headers, params, timeout)

    msg = ''
    if 'status' in reviews:
        msg = f'Bad reviews status: {reviews["status"]}'
    else:
        msg = 'Response has no reviews status not found.'
    logging.error(msg)
    raise ValueError(msg)


if __name__ == '__main__':
    main()
