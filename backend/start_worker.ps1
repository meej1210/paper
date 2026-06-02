Set-Location $PSScriptRoot
$env:CELERY_TASK_ALWAYS_EAGER = "false"
& "D:\anaconda\python.exe" -m celery -A app.workers.celery_app.celery_app worker --loglevel=info --pool=solo
