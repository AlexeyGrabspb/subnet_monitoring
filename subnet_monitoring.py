"""
Служба, которая проверяет соединение подсетей по определенному промежутку ip адресов.

Данные, которые нам нужны для сканирования и некоторые настройки будут храниться в конфиге. Там же есть небольшое
    описание по каждому параметру и информация по логам.
"""

import os
import sys
from pythonping import ping
from configparser import ConfigParser
import re
import logging
from logging.handlers import RotatingFileHandler
import time
import datetime


root_path = os.path.dirname(os.path.abspath(sys.argv[0]))

# __file__ выдает нам путь до файла,abspath редактирует путь под систему откуда запускается файл, dirname получаем \
# путь до папки
# __file__ замене на sys.argv[0], по сути тоже самое, но в случае с __file__ pyinstaller не компелирует.
current_date = datetime.datetime.now().date().strftime('%d-%m-%Y')

config_path = os.path.join(root_path, 'subnets.ini')
config = ConfigParser(allow_no_value=True)
config.read(config_path)

try:
    os.makedirs(f'{root_path}/logs')
except OSError:
    pass

logger = logging.getLogger('subnet_monitoring')  # Лог, который при запуске скрипта будет создаваться в \
# директории запуска
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(filename=os.path.join(root_path, f'logs/subnet_monitoring_{current_date}.log'), maxBytes=200000)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


def get_status(ip: str, packets: int, timeout: float) -> str:
    """
    Получает статус от каждого активного хоста
    :param ip: хост
    :param packets: кол-во отправляемых пакетов для каждого адреса подсети
    :param timeout: время ожидания ответа
    :return: None
    """
    refresh_ip_status = ping(ip, count=packets, timeout=timeout)
    success_active_ip = refresh_ip_status.success()
    if success_active_ip:
        avg_ms = round(refresh_ip_status.rtt_avg * 1000, 2)
        packets_lost = refresh_ip_status.packets_lost
        str_response = 'Host {} | avg ping: {} ms | packet lost: {}'.format(ip, avg_ms, packets_lost)
        return str_response
    else:
        str_response = 'Host {} is not active.'
        return str_response


def get_active_ip(ip: str, timeout: float) -> str:
    """
    Пингует каждый хост подсети, проверяет на активность.
    :param ip: хост
    :param timeout: время ожидания между попытками
    :return: лист активных хостов
    """
    ping_ip = ping(ip, count=1, timeout=timeout)
    success_ip = ping_ip.success()
    if success_ip:
        return ip


def get_ip_list(subnet: str, range_start: int, range_stop: int) -> list:
    """
    Формирует список хостов.
    :param subnet: подсеть
    :param range_start: начальная цифра диапазона адресов
    :param range_stop: конечная цифра диапазона адресов
    :return: список хостов для сканированя
    """
    ip_list = []
    logger.info(f'Get a list of hosts on a subnet {subnet}')
    for i in range(range_start, range_stop):
        # Вычленили из адреса подсети все до последней точки
        format_ip = re.search(r'^((1\d\d|2([0-4]\d|5[0-5])|\d\d?)\.?){3}', subnet)
        ip_raw = format_ip[0]+str(i)
        ip_list.append(ip_raw)
    return ip_list


def subnets_cfg_list() -> list:
    """
    Достает из конфига список подсетей
    :return: список подсетей
    """
    subnet_list = []
    logger.info('Refresh subnets list')
    for subnet in config['subnets']:
        subnet_list.append(subnet)
    return subnet_list


def current_list_folders() -> list:
    """
    Возвращает текущий список папок, эта информация
    нужна для создания и удаления папок с логамию.
    :return: тот самый список
    """
    match_list = []
    list_folder = []
    for dir, folders, files in os.walk(root_path+'/logs'):
        for folder in folders:
            list_folder.append(folder)
        break
    for folder in list_folder:
        matches = re.findall(r'\d\d-\d\d-\d{4}', folder)
        if matches:
            for match in matches:
                match_list.append(match)
    return match_list


def folder_manager() -> None:
    """
    Удаляет папки со всем содержимым созданные
    более 14 дней назад и создает папку по
    текущей дате.
    :return: None
    """
    logger.debug('Checking folders that need to be deleted after 14 days')
    for folder in current_list_folders:
        match_date = re.search(r'\d\d', folder)
        match_date = int(match_date[0])
        if current_month_day - match_date >= 14:
            logger.debug(f'Folder {folder} will be remove, because it was created >= 14 days ago.')
            os.system(f'rm -rf {root_path}/logs/{folder}')

    logger.debug('Checking if a folder with the name of today\'s date exists')
    if current_date not in current_list_folders:
        logger.debug(f'Folder {current_date} does not exist and will be created.')
        os.system(f'mkdir {root_path}/logs/{current_date}')
    else:
        logger.debug(f'Folder {current_date} already exists.')


def logger_manager() -> None:
    """
    Удаляет на следующий день,
    основной лог, нужный для отлова багов.
    :return: None
    """
    logger.debug('Delete subnet_monitoring log for the last day')
    for dir, folders, files in os.walk(root_path+'/logs'):
        for file in files:
            matches = re.findall(r'subnet_monitoring_\d\d', file)
            for match in matches:
                if match:
                    match_date = int(re.search(r'\d\d', match)[0])
                    if current_month_day != match_date:
                        os.system(f'rm {root_path}/logs/{file}')
                        logger.debug(f'{file} has been removed.')
                        pass
        break


def get_subnet_log() -> None:
    """
    Создает логи для каждой подсети отдельный файлом
    :return: None
    """
    for num, subnet in enumerate(subnet_list):
        log_name_dict[f'{num}'] = logging.getLogger(f'{subnet}')
        log_name_dict[f'{num}'].setLevel(logging.INFO)

        log_handler_dict[f'{num}'] = logging.FileHandler(filename=os.path.join(
            root_path, f'logs/{current_date}/{subnet}.log'), mode='w')
        log_name_dict[f'{num}'].addHandler(log_handler_dict[f'{num}'])


if __name__ == '__main__':
    current_date = datetime.datetime.now().date().strftime('%d-%m-%Y')
    current_month_day = int(re.search(r'\d\d', current_date)[0])
    current_list_folders = current_list_folders()
    logger_manager()
    folder_manager()
    logger.info('Starting a subnet scan...')
    packets = int(config.get('settings', 'packets_count'))
    range_start, range_stop = int(config.get('settings', 'range_start')), int(config.get('settings', 'range_stop'))
    timeout_reply = float(config.get('settings', 'timeout_reply'))
    timeout_scan = int(config.get('settings', 'timeout_scan'))
    subnet_list = subnets_cfg_list()
    all_active_ip = {}
    log_name_dict = {}
    log_handler_dict = {}
    get_subnet_log()
    for num, subnet in enumerate(subnet_list):
        active_ip_subnet = []
        ip_list = get_ip_list(subnet, range_start, range_stop)
        for ip in ip_list:
            active_ip = get_active_ip(ip, timeout_reply)
            if active_ip:
                logger.info(f'Host {ip} is active. Added to tracking list')
                active_ip_subnet.append(active_ip)
        all_active_ip[subnet] = active_ip_subnet
    logger.info('Tracking list of all active hosts formed')
    while True:
        for num, subnet in enumerate(subnet_list):
            log_name_dict[f'{num}'].info(f'Scanner date: {datetime.datetime.now()}')
            log_name_dict[f'{num}'].info('Online devices: {}'.format(len(all_active_ip[f'{subnet}'])))
            log_name_dict[f'{num}'].info('Offline devices: {}\n'.format(254-len(all_active_ip[f'{subnet}'])))
            logger.info('-' * 70)
            logger.info(f'Updating hosts statuses for subnet: {subnet}')
            for ip in all_active_ip[f'{subnet}']:
                response = get_status(ip, packets, timeout_reply)
                log_name_dict[f'{num}'].info(f'{response}\n')
            log_name_dict[f'{num}'].info('Done.')
        logger.info('Done')
        time.sleep(timeout_scan)
        for dir, folders, files in os.walk(f'{root_path}/logs/{current_date}/'):  # Чистим логи перед очередным сканом
            for file in files:
                os.system(f'rm {root_path}/logs/{current_date}/{file}')
        get_subnet_log()
