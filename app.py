import os
from pathlib import Path
import requests
import json
from dotenv import load_dotenv  # Для безопасного хранения токена


# Загружаем переменные окружения из файла .env
load_dotenv()
YANDEX_TOKEN = os.getenv("YANDEX_DISK_TOKEN")
if not YANDEX_TOKEN:
    raise ValueError("Не найден токен Яндекс.Диска. Убедитесь, что он указан в файле .env.")


def get_current_ip() -> str:
    """Получает текущий публичный IP-адрес пользователя."""
    response = requests.get('https://api.ipify.org')
    return response.text.strip()


def get_geo_info(ip_address: str) -> dict:
    """
    Получает географическую информацию об IP через ipinfo.io.
    
    Args:
        ip_address: Публичный IPv4 адрес.
    
    Returns:
        Словарь с информацией о городе, регионе, стране и координатах.
    """
    url = f"https://ipinfo.io/{ip_address}/geo"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        # Оставляем только нужные поля
        geo_data = {
            'city': data.get('city', ''),
            'region': data.get('region', ''),
            'country': data.get('country', ''),
            'loc': data.get('loc', '')
        }
        return geo_data
    else:
        print(f"Ошибка при получении геоданных: {response.status_code} - {response.text}")
        return {}


def create_folder_on_yadisk(folder_name: str):
    """
    Создаёт папку на Яндекс.Диске или проверяет её существование.
    
    Args:
        folder_name: Название папки без слэшей.
    
    Returns:
        Полный путь к папке на Диске.
    """
    headers = {"Authorization": f"OAuth {YANDEX_TOKEN}"}
    remote_path = f"/{folder_name}"
    params = {'path': remote_path}

    # Проверяем, существует ли уже папка
    check_response = requests.get(
        "https://cloud-api.yandex.net/v1/disk/resources",
        headers=headers,
        params=params
    )
    if check_response.status_code == 200:
        print(f"Папка '{folder_name}' уже существует.")
        return remote_path

    # Если нет — создаём
    create_response = requests.put(
        "https://cloud-api.yandex.net/v1/disk/resources",
        headers=headers,
        params={'path': remote_path}
    )
    if create_response.status_code in [201, 409]:
        print(f"Создана папка '{folder_name}'.")
        return remote_path
    else:
        raise Exception(f"Не удалось создать папку: {create_response.status_code}, {create_response.text}")


def upload_json_to_yadisk(remote_folder: str, filename: str, content: bytes):
    """
    Загружает JSON-файл напрямую на Яндекс.Диск.
    
    Args:
        remote_folder: Путь к целевой папке.
        filename: Имя файла.
        content: Бинарные данные файла.
    """
    headers = {"Authorization": f"OAuth {YANDEX_TOKEN}"}
    full_remote_path = f"{remote_folder}/{filename}"

    # Шаг 1: Запрашиваем ссылку для загрузки
    params = {'path': full_remote_path, 'overwrite': 'true'}
    response = requests.get(
        "https://cloud-api.yandex.net/v1/disk/resources/upload",
        headers=headers,
        params=params
    )
    href = response.json().get('href')
    if not href:
        raise Exception(f"Не удалось получить ссылку для загрузки: {response.text}")

    # Шаг 2: Отправляем файл по полученной ссылке
    put_response = requests.put(href, data=content)
    if put_response.status_code != 201:
        raise Exception(f"Ошибка при загрузке файла: {put_response.status_code}, {put_response.text}")
    print(f"Успешно загружено: {full_remote_path}")


def main():
    current_ip = get_current_ip()
    print(f"Ваш текущий IP-адрес: {current_ip}")

    geo_data = get_geo_info(current_ip)
    print(f"Геоинформация: {geo_data}")

    # Формируем имя папки и файла
    folder_name = f"IP_{current_ip.replace('.', '_')}_GeoInfo"
    file_name = "geoinfo.json"

    # Сохраняем данные в байты (для прямой отправки на диск)
    json_bytes = json.dumps(geo_data, ensure_ascii=False, indent=4).encode('utf-8')

    # Работа с Яндекс.Диском
    remote_folder = create_folder_on_yadisk(folder_name)
    upload_json_to_yadisk(remote_folder, file_name, json_bytes)


if __name__ == "__main__":
    main()
