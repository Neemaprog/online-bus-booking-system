# core/apps.py
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        # Hapa tuna-import signals — Django ina-handle timing vizuri
        import core.signals