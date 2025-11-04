"""
Приклад використання presigned URL для роботи з S3.

Цей файл демонструє як правильно використовувати presigned URL
для безпечного завантаження та завантаження файлів з S3.
"""

import os

import requests
from django.conf import settings

from apps.shared.storage.s3_utils import S3Service

# Використовуємо змінні середовища замість хардкодованих ключів
AWS_ACCESS_KEY_ID = os.getenv('YOUR_ACCESS_KEY_S3')
AWS_SECRET_ACCESS_KEY = os.getenv('YOUR_SECRET_KEY_S3')
AWS_S3_REGION_NAME = 'eu-north-1'
S3_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME_S3', 'media-flow')


def demonstrate_presigned_url_usage():
    """
    Демонстрація використання presigned URL для роботи з S3.
    """
    s3_service = S3Service()

    # Приклад 1: Генерація URL для завантаження файлу
    print('=== Приклад 1: Генерація URL для завантаження ===')
    upload_key = 'test-folder/example-upload.txt'

    try:
        upload_url = s3_service.generate_upload_url(
            key=upload_key,
            expiration=3600,  # 1 година
            content_type='text/plain',
        )
        print(f'Upload URL: {upload_url}')

        # Завантаження файлу через presigned URL
        test_content = 'Це тестовий файл, завантажений через presigned URL!'
        response = requests.put(upload_url, data=test_content, headers={'Content-Type': 'text/plain'})

        if response.status_code == 200:
            print('✅ Файл успішно завантажено!')
        else:
            print(f'❌ Помилка завантаження: {response.status_code}')

    except Exception as e:
        print(f'❌ Помилка генерації upload URL: {e}')

    # Приклад 2: Генерація URL для завантаження файлу
    print('\n=== Приклад 2: Генерація URL для завантаження ===')

    try:
        download_url = s3_service.generate_download_url(
            key=upload_key, expiration=3600, filename='downloaded-example.txt'
        )
        print(f'Download URL: {download_url}')

        # Завантаження файлу через presigned URL
        response = requests.get(download_url)

        if response.status_code == 200:
            print(f'✅ Файл успішно завантажено! Розмір: {len(response.content)} байт')
            print(f'Вміст: {response.text}')
        else:
            print(f'❌ Помилка завантаження: {response.status_code}')

    except Exception as e:
        print(f'❌ Помилка генерації download URL: {e}')

    # Приклад 3: Отримання метаданих файлу
    print('\n=== Приклад 3: Отримання метаданих ===')

    try:
        metadata = s3_service.get_object_metadata(upload_key)
        print('Метадані файлу:')
        print(f"  - Тип контенту: {metadata.get('content_type')}")
        print(f"  - Розмір: {metadata.get('content_length')} байт")
        print(f"  - Остання модифікація: {metadata.get('last_modified')}")
        print(f"  - ETag: {metadata.get('etag')}")

    except Exception as e:
        print(f'❌ Помилка отримання метаданих: {e}')

    # Приклад 4: Генерація URL для видалення файлу
    print('\n=== Приклад 4: Видалення файлу ===')

    try:
        delete_url = s3_service.generate_delete_url(upload_key, expiration=300)  # 5 хвилин
        print(f'Delete URL: {delete_url}')

        # Видалення файлу через presigned URL
        response = requests.delete(delete_url)

        if response.status_code == 204:
            print('✅ Файл успішно видалено!')
        else:
            print(f'❌ Помилка видалення: {response.status_code}')

    except Exception as e:
        print(f'❌ Помилка генерації delete URL: {e}')

    # Приклад 5: Масове завантаження файлів
    print('\n=== Приклад 5: Масове завантаження ===')

    test_keys = ['test-folder/file1.txt', 'test-folder/file2.jpg', 'test-folder/file3.pdf']

    try:
        bulk_urls = s3_service.generate_bulk_download_urls(test_keys, expiration=1800)  # 30 хвилин

        print('URL для масового завантаження:')
        for key, url in bulk_urls.items():
            if url:
                print(f'  {key}: {url}')
            else:
                print(f'  {key}: ❌ Помилка генерації URL')

    except Exception as e:
        print(f'❌ Помилка масового завантаження: {e}')


def demonstrate_security_features():
    """
    Демонстрація безпечних особливостей presigned URL.
    """
    print('\n=== Безпечні особливості Presigned URL ===')

    s3_service = S3Service()

    # 1. Обмежений час життя
    print('1. Обмежений час життя:')
    print('   - URL діє тільки протягом вказаного часу')
    print('   - Після закінчення терміну URL стає недійсним')

    # 2. Конкретний об'єкт
    print("2. Конкретний об'єкт:")
    print('   - URL працює тільки для одного файлу')
    print('   - Не можна використовувати для доступу до інших файлів')

    # 3. Конкретна операція
    print('3. Конкретна операція:')
    print('   - Upload URL тільки для завантаження')
    print('   - Download URL тільки для завантаження')
    print('   - Delete URL тільки для видалення')

    # 4. Без необхідності в публічних бакетах
    print('4. Без публічних бакетів:')
    print('   - Файли можуть залишатися приватними')
    print('   - Доступ тільки через presigned URL')


if __name__ == '__main__':
    print('🚀 Демонстрація використання Presigned URL в S3')
    print('=' * 50)

    demonstrate_presigned_url_usage()
    demonstrate_security_features()

    print('\n' + '=' * 50)
    print('✅ Демонстрація завершена!')
    print('\n💡 Основні переваги presigned URL:')
    print('   - Безпечний доступ до приватних файлів')
    print('   - Контроль часу доступу')
    print('   - Немає необхідності в публічних бакетах')
    print('   - Можна встановити обмеження (IP, заголовки)')
