# EcoRegen App

Веб-приложение на FastAPI для работы с экологическими задачами и фото:
- регистрация и авторизация пользователей;
- создание и просмотр задач;
- загрузка фотографий в задачу;
- вычисление NDVI;
- HSV-анализ (доля пикселей, попадающих в заданный диапазон);
- сегментация изображений (YOLO / fallback Mask R-CNN).

## Технологии

- Python 3.10+
- FastAPI, Jinja2
- SQLAlchemy (SQLite)
- Pillow, NumPy, OpenCV, Matplotlib
- PyTorch / torchvision
- Ultralytics YOLO

## Структура проекта

- `app/main.py` - точка входа FastAPI, middleware, подключение роутов
- `app/features/auth/` - регистрация, вход, выход, JWT cookie
- `app/features/tasks/` - задачи, загрузка фото, NDVI/HSV/segmentation
- `app/image/` - модули обработки изображений
- `app/models.py` - SQLAlchemy-модели (`User`, `Task`, `Photo`, результаты обработки)
- `app/static/uploads/` - загруженные и сгенерированные изображения
- `app/templates/` - HTML-шаблоны

## Быстрый старт

1. Создайте и активируйте виртуальное окружение.
2. Установите зависимости:

```bash
pip install -r requirements.txt
```

3. Запустите приложение:

```bash
uvicorn app.main:app --reload
```

4. Откройте в браузере:

```text
http://127.0.0.1:8000
```

При первом запуске таблицы создаются автоматически (`Base.metadata.create_all(...)`).
Файл базы данных SQLite: `app.db` в корне проекта.

## Основной пользовательский сценарий

1. Зарегистрироваться на `/register`.
2. Войти на `/login`.
3. Создать задачу (`/tasks/create` или через UI).
4. Открыть страницу задачи `/tasks/{task_id}`.
5. Загрузить одну или несколько фотографий.
6. Запустить NDVI / HSV-анализ / сегментацию для выбранного фото.

## Основные маршруты

### Auth

- `GET /register` - форма регистрации
- `POST /register/form` - регистрация пользователя
- `GET /login` - форма входа
- `POST /login/form` - вход
- `GET /logout` - выход

### Tasks

- `GET /` - главная (последние задачи, фильтр по датам)
- `GET /tasks` - список задач
- `POST /tasks/create` - создание задачи
- `GET /tasks/{task_id}` - детали задачи
- `POST /tasks/{task_id}/upload` - загрузка фото
- `POST /tasks/{task_id}/ndvi` - построение NDVI
- `POST /tasks/{task_id}/analyze_hsv` - HSV-анализ
- `POST /tasks/{task_id}/segment` - сегментация
- `POST /tasks/{task_id}/photos/{photo_id}/rename` - переименование фото
- `POST /tasks/{task_id}/delete` - удаление задачи (и связанных файлов)

Часть обработчиков поддерживает AJAX/JSON-ответы при `X-Requested-With: XMLHttpRequest` или `Accept: application/json`.

## Обработка изображений

### NDVI

Модуль: `app/image/ndvi.py`

- Ожидает многоканальное изображение.
- Каналы задаются индексами `red_index` и `nir_index` (0-based).
- Результат сохраняется в `app/static/uploads/ndvi_photo_{photo_id}.png`.

### HSV-анализ

Модуль: `app/image/analysis.py`

- Вычисляет долю пикселей, попавших в диапазон hue и пороги `sat_min`/`val_min`.
- Сохраняет круговую диаграмму в `app/static/uploads/analysis_hsv_photo_{photo_id}.png`.

### Сегментация

Модуль: `app/image/segmentation.py`

- `method=yolo`: используется `YOLO("yolov8n-seg")`.
- Альтернативно доступен fallback на Mask R-CNN.
- Результат сохраняется в `app/static/uploads/segm_photo_{photo_id}.png`.

## Конфигурация и безопасность

Сейчас в коде используются дев-настройки:
- `SECRET_KEY = "dev-secret-change-me"` в `app/features/auth/utils.py`
- CORS открыт для всех источников (`allow_origins=["*"]`)

Для production рекомендуется:
- вынести секреты в переменные окружения;
- ограничить CORS доверенными доменами;
- настроить защищенные cookie (`Secure`, `SameSite`, срок жизни);
- добавить миграции (например, Alembic) вместо auto-create таблиц.

## Полезные замечания

- В репозитории присутствуют веса `yolov8n.pt` и `yolov8n-seg.pt`, а также директория `dataset/` и результаты обучения в `runs/`.
- При удалении задачи удаляются связанные изображения и артефакты обработки из `app/static/uploads/`.

