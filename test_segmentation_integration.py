#!/usr/bin/env python3
"""
Скрипт для тестирования интеграции обученной модели в приложение.
Проверяет работу сегментации на реальных изображениях из датасета.
"""

import os
import sys
from pathlib import Path

# Добавляем путь к приложению
sys.path.insert(0, os.path.dirname(__file__))

from app.image.segmentation import run_segmentation

def test_segmentation_integration():
    """Тестирует интеграцию сегментации с обученной моделью."""
    
    print("\n" + "="*70)
    print("🧪 ТЕСТИРОВАНИЕ ИНТЕГРАЦИИ СЕГМЕНТАЦИИ В ПРИЛОЖЕНИЕ")
    print("="*70)
    
    # Проверяем наличие модели в приложении
    model_path = "app/models/yolov8n-seg-trained.pt"
    if not os.path.exists(model_path):
        print(f"\n❌ Обученная модель не найдена: {model_path}")
        print("💡 Совет: запустите deploy_model.py для развёртывания модели")
        return False
    
    print(f"\n✅ Обученная модель найдена: {model_path}")
    
    # Ищем тестовые изображения
    test_dirs = [
        "dataset/test/images",
        "dataset/valid/images",
        "dataset/train/images",
    ]
    
    test_images = []
    for test_dir in test_dirs:
        if os.path.exists(test_dir):
            images = list(Path(test_dir).glob("*.jpg")) + list(Path(test_dir).glob("*.png"))
            test_images.extend(images[:2])  # Берём по 2 из каждой директории
            if test_images:
                break
    
    if not test_images:
        print("\n❌ Тестовые изображения не найдены")
        return False
    
    print(f"\n🖼️  Найдено {len(test_images)} тестовых изображений")
    
    # Создаём директорию для результатов
    output_dir = "segmentation_test_results"
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"📁 Результаты сохраняются в: {output_dir}/")
    print("\n" + "-"*70)
    
    success_count = 0
    error_count = 0
    
    # Тестируем на каждом изображении
    for idx, img_path in enumerate(test_images[:3], 1):  # Первые 3 изображения
        print(f"\n[{idx}/{min(3, len(test_images))}] Тестирую: {img_path.name}")
        
        output_path = os.path.join(output_dir, f"segmented_{img_path.stem}_result.jpg")
        
        try:
            success, message = run_segmentation(
                input_path=str(img_path),
                output_path=output_path,
                method="yolo",
                conf=0.3
            )
            
            if success:
                print(f"    ✅ Успешно! Результат сохранён: {output_path}")
                success_count += 1
            else:
                print(f"    ❌ Ошибка: {message}")
                error_count += 1
        except Exception as e:
            print(f"    ❌ Исключение: {e}")
            error_count += 1
    
    print("\n" + "-"*70)
    print(f"\n✅ РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    print(f"   Успешно обработано: {success_count}")
    print(f"   Ошибок: {error_count}")
    print(f"   Результаты в: {output_dir}/")
    
    if success_count > 0:
        print("\n✅ Интеграция работает корректно!")
        print("✅ Вы можете использовать функцию сегментации в приложении")
        return True
    else:
        print("\n⚠️  Интеграция имеет проблемы")
        return False

def show_deployment_info():
    """Показывает информацию о развёртывании."""
    
    print("\n" + "="*70)
    print("📊 ИНФОРМАЦИЯ О РАЗВЁРТЫВАНИИ")
    print("="*70)
    
    if os.path.exists("app/models/yolov8n-seg-trained.pt"):
        size = os.path.getsize("app/models/yolov8n-seg-trained.pt") / 1024 / 1024
        print(f"\n✅ Обученная модель развёрнута")
        print(f"   Путь: app/models/yolov8n-seg-trained.pt")
        print(f"   Размер: {size:.1f} MB")
        print(f"   Статус: Готова к использованию")
    else:
        print(f"\n⚠️  Обученная модель не развёрнута")
        print(f"   Запустите: .venv\\Scripts\\python.exe deploy_model.py")

if __name__ == "__main__":
    show_deployment_info()
    
    print("\n")
    success = test_segmentation_integration()
    
    print("\n" + "="*70)
    if success:
        print("🚀 ГОТОВО К ИСПОЛЬЗОВАНИЮ!")
        print("\nНапустите приложение:")
        print("  .venv\\Scripts\\uvicorn.exe app.main:app --reload")
        print("\nЗатем откройте http://localhost:8000 в браузере")
    print("="*70 + "\n")
    
    exit(0 if success else 1)
