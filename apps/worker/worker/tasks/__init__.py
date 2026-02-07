from worker.celery_app import celery

@celery.task(name="worker.tasks.example_task")
async def ping() -> str:
    return "pong"