import logging
import backoff
import requests
from environs import Env
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

LONG_POLLING_URL = 'https://dvmn.org/api/long_polling/'


def main():
    env = Env()
    env.read_env()
    token = env.str('DEVMAN_API_TOKEN')
    tgbot_token = env.str('TGBOT_API_TOKEN')

    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )

    headers = {
        'Authorization': f'Token {token}'
    }
    start_polling(LONG_POLLING_URL, headers=headers)


    # application = ApplicationBuilder().token(tgbot_token).build()

    # start_handler = CommandHandler('start', start)
    # application.add_handler(start_handler)

    # application.run_polling()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Hello!!")

backoff_exceptions = (requests.ReadTimeout, requests.ConnectionError,
                      requests.Timeout)


@backoff.on_exception(backoff.expo, backoff_exceptions)
def start_polling(url, headers, params=None, timeout=60):
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    reviews = resp.json()

    if reviews['status'] == 'found':
        print('Found!', reviews)
        return start_polling(url, headers, params, timeout)

    if reviews['status'] == 'timeout':
        print('Timeout!', reviews)
        timestamp = reviews['timestamp_to_request']
        params = {
            'timestamp': timestamp
        }
        return start_polling(url, headers, params, timeout)

    msg = ''
    if 'status' in reviews:
        msg = f'Bad reviews status: {reviews["status"]}'
    else:
        msg = 'Response has no reviews status not found.'
    logging.error(msg)
    raise ValueError(msg)


if __name__ == '__main__':
    main()
