from app import create_app
from app.workers.celery_app import celery_app

app = create_app()
app.app_context().push()
