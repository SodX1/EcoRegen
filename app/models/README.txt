Обученная YOLOv8 Segmentation модель

Источник: runs/segment/train_gpu/weights/best.pt
Дата копирования: 2026-03-29

Архитектура: YOLOv8-nano Segmentation
Входной размер: 640x640
Выходной формат: Instance segmentation (polygons)

Использование:
  from ultralytics import YOLO
  model = YOLO("app/models/yolov8n-seg-trained.pt")
  results = model.predict("image.jpg")

Примечание:
  Сегментация использует эту модель автоматически в приложении.
  Обновите эту копию, если переобучили модель.
