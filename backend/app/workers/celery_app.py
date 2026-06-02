from celery import Celery

from ..config import get_config


def make_celery():
    config = get_config()
    celery = Celery(
        __name__,
        broker=config.REDIS_URL,
        backend=config.REDIS_URL,
        include=["app.workers.sast_tasks", "app.workers.dast_tasks", "app.workers.sca_tasks"],
    )
    celery.conf.update(
        task_track_started=True,
        result_expires=3600,
        task_always_eager=config.CELERY_TASK_ALWAYS_EAGER,
        broker_connection_retry_on_startup=True,
        worker_pool="solo",
    )
    return celery


celery_app = make_celery()
