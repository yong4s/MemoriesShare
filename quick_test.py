#!/usr/bin/env python3
"""
Швидкий тест Presigned URL.

Простий скрипт для тестування завантаження файлу через presigned URL.
"""

import os
import sys
import requests
from datetime import datetime

# Додаємо шлях до Django проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Налаштування Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.main')

import django
django.setup()

from apps.shared.s3_utils import S3Service


def quick_test():
    """Швидкий тест presigned URL."""
    print("🚀 Швидкий тест Presigned URL")
    print("=" * 40)
    
    s3_service = S3Service()
    
    # Створюємо тестовий файл
    test_file = "quick_test.txt"
    test_content = f"Тестовий файл\nСтворено: {datetime.now()}\nЦе працює! 🎉"
    
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_content)
    
    try:
        print("📤 Крок 1: Генерація presigned URL для завантаження")
        
        # Генеруємо presigned URL
        s3_key = f"test-folder/quick_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        upload_url = s3_service.generate_upload_url(
            key=s3_key,
            expiration=3600,
            content_type="text/plain"
        )
        
        print(f"📋 S3 Key: {s3_key}")
        print(f"🔗 Upload URL: {upload_url[:80]}...")
        
        print("\n📤 Крок 2: Завантаження файлу")
        
        # Завантажуємо файл
        with open(test_file, 'rb') as f:
            response = requests.put(
                upload_url,
                data=f,
                headers={'Content-Type': 'text/plain'}
            )
        
        if response.status_code == 200:
            print("✅ Файл успішно завантажено!")
            
            print("\n📥 Крок 3: Генерація presigned URL для завантаження")
            
            # Генеруємо URL для завантаження
            download_url = s3_service.generate_download_url(
                key=s3_key,
                expiration=3600,
                filename="downloaded_test.txt"
            )
            
            print(f"🔗 Download URL: {download_url[:80]}...")
            
            print("\n📥 Крок 4: Завантаження файлу")
            
            # Завантажуємо файл
            download_response = requests.get(download_url)
            
            if download_response.status_code == 200:
                print("✅ Файл успішно завантажено!")
                print(f"📄 Вміст файлу:")
                print("-" * 20)
                print(download_response.text)
                print("-" * 20)
                
                print("\n🎉 Тест пройшов успішно!")
                print(f"📁 Файл збережено в S3: {s3_key}")
                
            else:
                print(f"❌ Помилка завантаження: {download_response.status_code}")
                print(f"Відповідь: {download_response.text}")
        else:
            print(f"❌ Помилка завантаження: {response.status_code}")
            print(f"Відповідь: {response.text}")
            
    except Exception as e:
        print(f"❌ Помилка: {e}")
    finally:
        # Очищуємо тестовий файл
        if os.path.exists(test_file):
            os.remove(test_file)
            print(f"\n🧹 Тестовий файл {test_file} видалено")


if __name__ == "__main__":
    quick_test() 