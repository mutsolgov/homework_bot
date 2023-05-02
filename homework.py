import logging
import os
import time
from http import HTTPStatus
import json

import requests
import telegram
from dotenv import load_dotenv

import exceptions

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.INFO,
    filename='main.log',
    encoding='UTF-8',
    format='%(asctime)s, %(name)s, %(levelname)s, %(message)s',
)
logger = logging.getLogger(__name__)
handler = logging.StreamHandler(stream='sys.stdout')
logger.addHandler(handler)


def send_message(bot, message):
    """Отправляем сообщение в чат."""
    try:
        logger.debug(f'Начало отправки сообщения в Telegram: {message}.')
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except telegram.error.TelegramError as error:
        logger.error(
            f'При отправке сообщения в Telegram произошел сбой: {error}.'
        )


def get_api_answer(timestamp):
    """Проверяем список домашних работ."""
    timestamp = timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT,
                                headers=HEADERS,
                                params=params)
        if response.status_code != HTTPStatus.OK:
            raise exceptions.StatusNotCode(
                'Ошибка при запросе к API не возвращает статус 200.'
            )
        return response.json()
    except json.JSONDecodeError as e:
        raise exceptions.InvalidJSONError(
            f'Ошибка преобразования ответа в JSON: {e}'
        )
    except requests.RequestException as error:
        raise exceptions.ApiStatus(f'Произошла ошибка:{error}')


def check_response(response):
    """Проверяет ответ API на корректность."""
    if not response:
        raise exceptions.ResponseAnswerEmpty('Пустой Ответ')
    if not isinstance(response, dict):
        raise exceptions.ResponseAnswerNotDict('Ответ от не в виде словаря')
    if 'homeworks' not in response:
        raise exceptions.HomeworksNotKeys(
            'В ответе нет ключа homework'
        )
    if 'current_date' not in response:
        raise exceptions.HomeworksNotKeysData(
            'В ответе нет ключа current_date'
        )
    homeworks_list = response.get("homeworks", "current_date")
    if not isinstance(homeworks_list, list):
        raise exceptions.ResponseAnswerNlist('В ответе нет списка работ')
    return homeworks_list


def parse_status(homework):
    """Узнаем статус отправленного проекта."""
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    verdict = HOMEWORK_VERDICTS.get(status)
    if not status:
        raise exceptions.CheckApiResponseStat('Нет ответа от status')
    if not homework_name:
        raise exceptions.CheckApiResponseKey('Нет ответа от homework_name')

    if status not in HOMEWORK_VERDICTS:
        raise exceptions.CheckApiResponse(
            'Получен некорректный статус работы.'
        )

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def get_current_timestamp():
    """Обновляет временную метку."""
    current_timestamp = int(time.time() - RETRY_PERIOD)
    return current_timestamp


def check_tokens():
    """Проверяем доступность переменных окружения."""
    logger.info('Проверяем доступность переменных окружений.')
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Отсутствует переменные окружения')
        raise ValueError('Проверьте переменные окружения')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    send_message(bot, 'Начало работы телеграмм бота')
    timestamp = int(time.time())
    cache = []
    while True:
        try:
            response = get_api_answer(timestamp)
            current_report = check_response(response)
            if current_report:
                send_message(bot, parse_status(current_report[0]))
                timestamp = response.get('current_date')
            else:
                message = "Новых статусов нет"
                logging.debug(message)
            if cache != message:
                cache = message
                send_message(bot, message)
            else:
                logging.info(message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
