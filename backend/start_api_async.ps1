Set-Location $PSScriptRoot
$env:CELERY_TASK_ALWAYS_EAGER = "false"
& "D:\anaconda\python.exe" run.py
