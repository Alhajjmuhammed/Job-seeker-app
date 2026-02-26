from django.apps import AppConfig


class WorkerConnectConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'worker_connect'
    verbose_name = 'Worker Connect Core'