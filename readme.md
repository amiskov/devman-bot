# Devman Bot
Телеграм-бот для оповещения о статусе проверок уроков на Девмане.

## Установка
Добавьте зависимости через [Poetry](https://python-poetry.org):

```sh
poetry install
```

Создайте файл `.env` и добавьте в него токены:

```ini
DEVMAN_API_TOKEN=...
TG_BOT_API_TOKEN=...
```

- `DEVMAN_API_TOKEN` можно узнать [здесь](https://dvmn.org/api/docs/).
- `TG_BOT_API_TOKEN` выдаст `@BotFather` после регистрации бота в Телеграмме.

Запустите бота, заменив `YOUR_CHAT_ID` на нужный вам Chat ID:

```sh
poetry run python main.py YOUR_CHAT_ID
```

Chat ID обычно он состоит из 9 цифр, узнать его моно у бота `@getmyid_bot`, 
