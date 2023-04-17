import logging
import os
import time
from http import HTTPStatus

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
    except telegram.TelegramError:
        logger.error(f'Cбой при отправке сообщения в Telegram: {message}.')
        raise exceptions.SendMessedge(
            f'Cбой при отправке сообщения в Telegram: {message}.'
        )


def get_api_answer(current_timestamp: int) -> dict:
    """Отправляем запрос к API и получаем список домашних работ.
    Также проверяем, что эндпоинт отдает статус 200.
    """
    timestamp = current_timestamp or int(time.time())
    params_request = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': timestamp},
    }
    message = ('Начало запроса к API. Запрос: {url}, {headers}, {params}.'
               ).format(**params_request)
    logging.info(message)
    try:
        response = requests.get(**params_request)
        if response.status_code != HTTPStatus.OK:
            raise exceptions.JsonNotDecode(
                f'Ответ API не возвращает 200. '
                f'Код ответа: {response.status_code}. '
                f'Причина: {response.reason}. '
                f'Текст: {response.text}.'
            )
        return response.json()
    except Exception as error:
        message = ('API не возвращает 200. Запрос: {url}, {headers}, {params}.'
                   ).format(**params_request)
        raise exceptions.JsonNotDecode(message, error)


def check_response(response):
    """Проверяет ответ API на корректность."""
    logger.info('Проверяем ответ API на корректность.')
    if not response:
        logger.error('Ответ от API - пустой словарь')
        raise exceptions.NotResponse('Ответ от API - пустой словарь')
    if type(response) is not dict:
        logger.error('Ответ от API не в виде словаря')
        raise exceptions.BananaType('Ответ от API не в виде словаря')
    if 'homeworks' not in response:
        logger.error('В ответе от API нет ключа homework')
        raise exceptions.HomeworksNotInResponse(
            'В ответе API нет ключа homework'
        )
    homeworks_list = response['homeworks']
    if type(homeworks_list) is not list:
        logger.error('В ответе API нет списка работ')
        raise exceptions.BananaType('В ответе API нет списка работ')
    return homeworks_list


def parse_status(homework):
    """
    Получает данные о статусе выполнения домашней работы и возвращает.
    строку с информацией о результате.
    """
    logger.info('Извлекаем информацию о конкретной домашней работе.')
    required_fields = ['homework_name', 'status']
    for field_name in required_fields:
        if field_name not in homework:
            logger.error(f'В homework нет ключа "{field_name}"')
            raise KeyError(f'В homework нет ключа "{field_name}"')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    if not verdict:
        logger.error('Вердикта нет в "HOMEWORK_VERDICTS"')
        raise exceptions.KeyNotInDict('Статуса нет в "HOMEWORK_VERDICTS"')
    logger.info(f'Изменился статус проверки работы "{homework_name}".'
                '{verdict}')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def get_current_timestamp():
    """Обновляет временную метку."""
    current_timestamp = int(time.time() - RETRY_PERIOD)
    return current_timestamp


def check_tokens():
    """Проверяем доступность переменных окружения."""
    logger.info('Проверяем доступность переменных окружения.')
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Отсутсвуют переменные окружения')
        raise KeyError('Отсутсвуют переменные окружения')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    cache = []
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks_list = check_response(response)
            try:
                (homeworks_list[0])
            except IndexError:
                logger.critical('Нет новых работ на проверку :(')
                raise exceptions.PetShopBoysError(
                    'Нет новых работ на проверку :('
                )
            homework = homeworks_list[0]
            message = parse_status(homework)
            current_timestamp = response.get('current_date')
        except Exception as error:
            message = f'Сбой в работе телеграмм-бота: {error}'
            logger.critical(
                f'Уведомление об ошибке отправлено в чат {message}'
            )
        finally:
            if message in cache:
                logger.debug('Новых статусов нет')
            else:
                cache.append(message)
                send_message(bot, message)
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
