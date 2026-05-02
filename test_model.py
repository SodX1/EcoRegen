
"""
Скрипт для тестирования обученной YOLOv8 сегментационной модели.
Выполняет инференс на контрольном наборе и выводит метрики.
"""

import os
from pathlib import Path
from ultralytics import YOLO
from PIL import Image
import numpy as np

# Пути
MODEL_PATH = "runs/segment/train_gpu/weights/best.pt"
TEST_IMAGES_DIR = "dataset/test/images"
OUTPUT_DIR = "test_results"

def test_model():
    """Загружает модель и тестирует на контрольном наборе."""
    
    # Проверяем наличие модели
    if not os.path.exists(MODEL_PATH):
        print(f"❌ Модель не найдена: {MODEL_PATH}")
        return False
    
    print(f"📦 Загружаю модель из {MODEL_PATH}...")
    model = YOLO(MODEL_PATH)
    print(f"✅ Модель загружена успешно!")
    print(f"   Архитектура: YOLOv8 Segmentation")
    print(f"   Входной размер: 640x640")
    
    # Создаём директорию для результатов
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Проверяем наличие тестовых изображений
    test_images = list(Path(TEST_IMAGES_DIR).glob("*.jpg")) + \
                  list(Path(TEST_IMAGES_DIR).glob("*.png"))
    
    if not test_images:
        print(f"⚠️  Тестовые изображения не найдены в {TEST_IMAGES_DIR}")
        
        # Используем пример из train если test пуст
        train_images = list(Path("dataset/train/images").glob("*.jpg")) + \
                      list(Path("dataset/train/images").glob("*.png"))
        if train_images:
            print(f"💡 Использую {len(train_images[:5])} изображений из обучающего набора...")
            test_images = train_images[:5]
        else:
            print("❌ Нет доступных изображений для тестирования")
            return False
    else:
        test_images = test_images[:5]  # Тестируем на первых 5 изображениях
    
    print(f"\n🖼️  Тестирую на {len(test_images)} изображениях...")
    print("=" * 70)
    
    total_detections = 0
    
    for idx, img_path in enumerate(test_images, 1):
        print(f"\n[{idx}/{len(test_images)}] Обрабатываю: {img_path.name}")
        
        # Выполняем инференс
        results = model.predict(str(img_path), conf=0.3)
        result = results[0]
        
        # Считаем детекции
        num_detections = len(result.boxes)
        num_masks = len(result.masks) if result.masks is not None else 0
        total_detections += num_detections
        
        print(f"   ✓ Обнаружено объектов: {num_detections}")
        if num_masks > 0:
            print(f"   ✓ Сегментов: {num_masks}")
        
        # Сохраняем результат с визуализацией
        output_path = os.path.join(OUTPUT_DIR, f"result_{idx}_{img_path.stem}.jpg")
        im_array = result.plot()
        Image.fromarray(im_array).save(output_path)
        print(f"   ✓ Сохранено: {output_path}")
    
    print("\n" + "=" * 70)
    print(f"✅ Тестирование завершено!")
    print(f"   Всего обнаружено объектов: {total_detections}")
    print(f"   Среднее на изображение: {total_detections / len(test_images):.1f}")
    print(f"   Результаты сохранены в: {OUTPUT_DIR}/")
    
    return True

def benchmark_speed():
    """Проверяет скорость инференса на GPU."""
    
    if not os.path.exists(MODEL_PATH):
        print(f"Модель не найдена: {MODEL_PATH}")
        return
    
    print(f"\nБенчмарк скорости инференса...")
    print("=" * 70)
    
    model = YOLO(MODEL_PATH)
    
    # Создаём тестовое изображение 640x640
    dummy_image = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
    
    # Тестируем несколько раз
    print("Выполняю 5 проходов инференса...")
    import time
    
    times = []
    for i in range(5):
        start = time.time()
        results = model.predict(dummy_image, verbose=False)
        elapsed = time.time() - start
        times.append(elapsed)
        print(f"   Проход {i+1}: {elapsed*1000:.1f}ms")
    
    avg_time = np.mean(times[1:])  # Исключаем первый (инициализация)
    fps = 1.0 / avg_time
    
    print(f"\nРезультаты бенчмарка:")
    print(f"   Среднее время инференса: {avg_time*1000:.1f}ms")
    print(f"   FPS (кадры в секунду): {fps:.1f}")
    print(f"   Размер модели: {os.path.getsize(MODEL_PATH) / 1024 / 1024:.1f} MB")

if __name__ == "__main__":
    print("\n" + "="*70)
    print("ТЕСТИРОВАНИЕ YOLOV8 СЕГМЕНТАЦИОННОЙ МОДЕЛИ")
    print("="*70)
    
    # Тестируем модель
    success = test_model()
    
    if success:
        # Бенчмарк скорости
        benchmark_speed()
    
    print("\n" + "="*70)
