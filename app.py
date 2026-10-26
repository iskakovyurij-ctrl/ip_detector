import os
import json
import requests
from dotenv import load_dotenv


class IpifyClient:
    def __init__(self, base_url: str = "https://api.ipify.org", timeout: int = 10):
        self.base_url = base_url
        self.timeout = timeout

    def get_current_ip(self) -> str:
        response = requests.get(self.base_url, timeout=self.timeout)
        response.raise_for_status()
        return response.text.strip()


class IpInfoClient:
    def __init__(self, base_url: str = "https://ipinfo.io", timeout: int = 10):
        self.base_url = base_url
        self.timeout = timeout

    def get_geo_info(self, ip_address: str) -> dict:
        url = f"{self.base_url}/{ip_address}/geo"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        return {
            "city": data.get("city", ""),
            "region": data.get("region", ""),
            "country": data.get("country", ""),
            "loc": data.get("loc", ""),
        }


class YandexDiskClient:
    def __init__(
        self,
        token: str,
        base_url: str = "https://cloud-api.yandex.net/v1/disk",
        timeout: int = 30,
    ):
        self.token = token
        self.base_url = base_url
        self.timeout = timeout

    @property
    def _auth_headers(self) -> dict:
        return {"Authorization": f"OAuth {self.token}"}

    def create_folder(self, folder_name: str) -> str:
        remote_path = f"/{folder_name}"
        response = requests.put(
            f"{self.base_url}/resources",
            headers=self._auth_headers,
            params={"path": remote_path},
            timeout=self.timeout,
        )
        if response.status_code == 201:
            print(f"Создана папка '{folder_name}'.")
            return remote_path
        if response.status_code == 409:
            print(f"Папка '{folder_name}' уже существует.")
            return remote_path
        response.raise_for_status()
        raise RuntimeError(
            f"Не удалось создать папку: {response.status_code}, {response.text}"
        )

    def upload_json(self, remote_folder: str, filename: str, content: bytes) -> None:
        full_remote_path = f"{remote_folder}/{filename}"
        response = requests.get(
            f"{self.base_url}/resources/upload",
            headers=self._auth_headers,
            params={"path": full_remote_path, "overwrite": "true"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        href = response.json().get("href")
        if not href:
            raise RuntimeError(f"Не удалось получить ссылку для загрузки: {response.text}")

        put_response = requests.put(href, data=content, timeout=self.timeout)
        put_response.raise_for_status()
        if put_response.status_code != 201:
            raise RuntimeError(
                f"Ошибка при загрузке файла: {put_response.status_code}, {put_response.text}"
            )
        print(f"Успешно загружено: {full_remote_path}")


def main():
    load_dotenv()
    token = os.getenv("YANDEX_DISK_TOKEN")
    if not token:
        raise ValueError(
            "Не найден токен Яндекс.Диска. Убедитесь, что он указан в файле .env."
        )

    ipify = IpifyClient()
    ipinfo = IpInfoClient()
    yadisk = YandexDiskClient(token=token)

    current_ip = ipify.get_current_ip()
    print(f"Ваш текущий IP-адрес: {current_ip}")

    geo_data = ipinfo.get_geo_info(current_ip)
    print(f"Геоинформация: {geo_data}")

    folder_name = f"IP_{current_ip.replace('.', '_')}_GeoInfo"
    file_name = "geoinfo.json"
    json_bytes = json.dumps(geo_data, ensure_ascii=False, indent=4).encode("utf-8")

    remote_folder = yadisk.create_folder(folder_name)
    yadisk.upload_json(remote_folder, file_name, json_bytes)


if __name__ == "__main__":
    main()
