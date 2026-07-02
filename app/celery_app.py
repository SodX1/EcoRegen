from celery import Celery
from kombu import Exchange, Queue
import os

# Создаём Celery приложение
app = Celery(
    "ecoreggen",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1"),
)

# Конфигурация
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 минут жёсткий лимит
    task_soft_time_limit=25 * 60,  # 25 минут софт лимит
    result_expires=3600,  # результаты хранятся 1 час
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
)

# Очереди
app.conf.task_queues = (
    Queue("segmentation", Exchange("segmentation"), routing_key="segmentation.#", queue_type="direct"),
    Queue("default", Exchange("default"), routing_key="default", queue_type="direct"),
)

# Маршруты задач
app.conf.task_routes = {
    "app.tasks.segment_image": {"queue": "segmentation"},
}

if __name__ == "__main__":
    app.start()
